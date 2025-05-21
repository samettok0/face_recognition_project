import pickle
import cv2
import time
from pathlib import Path
from typing import Dict, List, Union, Any, Tuple, Optional
import face_recognition
import logging
import numpy as np
import os
from datetime import datetime

from .config import TRAINING_DIR, ENCODINGS_FILE, HOG_MODEL
from .utils import logger
from .camera_handler import CameraHandler

class FaceEncoder:
    def __init__(self, model: str = HOG_MODEL, encodings_path: Path = ENCODINGS_FILE):
        """
        Initialize the face encoder
        
        Args:
            model: Face detection model to use ('hog' or 'cnn')
            encodings_path: Path to save/load the face encodings database
        """
        self.model = model
        self.encodings_path = encodings_path
        self.db_manager = None
        
        # Import here to avoid circular imports
        from .db_manager import DatabaseManager
        self.db_manager = DatabaseManager()
        
    def load_encodings(self) -> Dict[str, Union[List[str], List[Any]]]:
        """
        Load face encodings from database
        
        Returns:
            Dictionary with face encodings and corresponding names
        """
        try:
            # Try to load from database
            if self.db_manager:
                return self.db_manager.get_face_encodings()
                
            # Fallback to loading from pkl file
            if self.encodings_path.exists():
                with open(self.encodings_path, "rb") as f:
                    return pickle.load(f)
            else:
                logger.warning(f"Encodings file {self.encodings_path} not found")
                return {"names": [], "encodings": []}
        except Exception as e:
            logger.error(f"Error loading encodings: {e}")
            return {"names": [], "encodings": []}
    
    def _encode_face(self, image_path: Path) -> Optional[np.ndarray]:
        """
        Create a face encoding for a single image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Face encoding vector or None if no face detected
        """
        # Load image
        try:
            image = face_recognition.load_image_file(image_path)
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            return None
        
        # Find face locations
        face_locations = face_recognition.face_locations(
            image, model=self.model
        )
        
        # No faces found
        if not face_locations:
            logger.warning(f"No face found in {image_path}")
            return None
            
        # If multiple faces found, use the largest one
        if len(face_locations) > 1:
            logger.warning(f"Multiple faces found in {image_path}, using largest")
            # Calculate face area for each detection
            areas = [(r - t) * (r - l) for t, r, b, l in face_locations]
            # Get index of largest face
            largest_idx = areas.index(max(areas))
            face_locations = [face_locations[largest_idx]]
            
        # Create face encoding
        face_encoding = face_recognition.face_encodings(image, face_locations)[0]
        return face_encoding
    
    def encode_known_faces(self, force_rebuild: bool = False) -> bool:
        """
        Process the training directory and build face encodings database
        
        Args:
            force_rebuild: If True, rebuild encodings even if file exists
            
        Returns:
            True if successful, False otherwise
        """
        training_dir = TRAINING_DIR
        
        # Check if encodings already exist and force_rebuild is False
        if not force_rebuild and self.encodings_path.exists():
            logger.info(f"Using existing encodings file: {self.encodings_path}")
            
            # Migrate to database if needed
            if self.db_manager:
                migrations = self.db_manager.migrate_from_pkl(self.encodings_path)
                if migrations > 0:
                    logger.info(f"Migrated {migrations} face encodings to database")
                    
            return True
            
        logger.info("Building face encodings database...")
        
        # Dictionary to store the results
        data = {
            "names": [],
            "encodings": []
        }
        
        # Loop through each person's directory
        for person_dir in training_dir.iterdir():
            if not person_dir.is_dir():
                continue
                
            person_name = person_dir.name
            logger.info(f"Processing {person_name}'s images...")
            
            # Add user to database
            user_id = None
            if self.db_manager:
                user_id = self.db_manager.add_user(person_name)
            
            # Process each image for this person
            images_processed = 0
            for image_path in person_dir.glob("*.png"):
                # Encode face
                face_encoding = self._encode_face(image_path)
                if face_encoding is None:
                    continue
                    
                # Add encoding to database
                if self.db_manager and user_id is not None:
                    self.db_manager.add_face_encoding(user_id, face_encoding)
                    
                # Add to data dictionary
                data["names"].append(person_name)
                data["encodings"].append(face_encoding)
                
                images_processed += 1
                
            logger.info(f"Processed {images_processed} images for {person_name}")
            
        # If still using pkl files, save them
        if not self.db_manager:
            # Save the database of face encodings
            self.encodings_path.parent.mkdir(exist_ok=True)
            with open(self.encodings_path, "wb") as f:
                pickle.dump(data, f)
                
            logger.info(f"Saved {len(data['names'])} face encodings to {self.encodings_path}")
        else:
            logger.info(f"Added {len(data['names'])} face encodings to database")
            
        return len(data["names"]) > 0
    
    def register_person_from_camera(self, camera_handler: CameraHandler, name: str, 
                                   num_images: int = 5) -> bool:
        """
        Register a new person by taking photos from camera
        
        Args:
            camera_handler: Initialized camera handler
            name: Person's name
            num_images: Number of photos to take
            
        Returns:
            True if successful, False if failed or cancelled
        """
        # Create directory for training images
        person_dir = TRAINING_DIR / name
        person_dir.mkdir(parents=True, exist_ok=True)
        
        # Get timestamp for image names
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add user to database
        user_id = None
        if self.db_manager:
            user_id = self.db_manager.add_user(name)
        
        # Start camera if not already running
        camera_was_running = camera_handler.is_running
        if not camera_was_running:
            if not camera_handler.start():
                logger.error("Failed to start camera for registration")
                return False
        
        try:
            images_captured = 0
            print(f"Capturing {num_images} photos for {name}...")
            print("Press 'c' to capture, 'q' to cancel")
            
            last_capture_time = 0
            min_capture_interval = 1.0  # Minimum 1 second between captures
            
            while images_captured < num_images:
                frame = camera_handler.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Show instructions on frame
                progress = f"Progress: {images_captured}/{num_images} photos"
                cv2.putText(frame, progress, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "Press 'c' to capture, 'q' to cancel", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow("Registration", frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                # Cancel registration
                if key == ord('q'):
                    print("Registration cancelled.")
                    return False
                
                # Capture image
                current_time = time.time()
                if key == ord('c') and current_time - last_capture_time >= min_capture_interval:
                    # Save image
                    image_path = person_dir / f"{name}_{timestamp}_{images_captured+1}.png"
                    cv2.imwrite(str(image_path), frame)
                    
                    # Encode face
                    face_encoding = self._encode_face(image_path)
                    
                    if face_encoding is None:
                        print(f"No face detected in captured image. Please try again.")
                        # Delete the image
                        os.remove(image_path)
                    else:
                        # Add encoding to database
                        if self.db_manager and user_id is not None:
                            self.db_manager.add_face_encoding(user_id, face_encoding)
                            
                        images_captured += 1
                        print(f"Captured photo {images_captured}/{num_images}")
                        last_capture_time = current_time
            
            # Re-encode all faces to update the database
            logger.info(f"Registration complete. Re-encoding faces...")
            self.encode_known_faces(force_rebuild=True)
            
            return True
            
        finally:
            # Stop camera if it wasn't running before
            if not camera_was_running:
                camera_handler.stop()
            
            cv2.destroyAllWindows() 