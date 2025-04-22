import pickle
import cv2
import time
from pathlib import Path
from typing import Dict, List, Union, Any, Tuple, Optional
import face_recognition
import logging

from .config import TRAINING_DIR, ENCODINGS_FILE, HOG_MODEL
from .utils import logger

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
        
    def encode_known_faces(self) -> None:
        """
        Creates a database of known faces from training images.
        """
        logger.info("Starting face encoding process")
        names = []
        encodings = []
        
        # Count total files for progress tracking
        total_files = sum(1 for _ in TRAINING_DIR.glob("*/*"))
        processed = 0
        
        for filepath in TRAINING_DIR.glob("*/*"):
            if not filepath.is_file():
                continue
                
            # Extract name from parent directory
            name = filepath.parent.name
            logger.info(f"Processing image: {filepath.name} for person: {name}")
            
            try:
                # Load the image
                image = face_recognition.load_image_file(filepath)

                # Detect faces and create their encodings
                face_locations = face_recognition.face_locations(image, model=self.model)
                face_encodings = face_recognition.face_encodings(image, face_locations)

                # Save each detected face encoding
                for encoding in face_encodings:
                    names.append(name)
                    encodings.append(encoding)
                
                processed += 1
                if processed % 10 == 0:
                    logger.info(f"Processed {processed}/{total_files} images")
                    
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
        
        # Save the database of face encodings
        self._save_encodings(names, encodings)
        logger.info(f"Face encoding complete. Encoded {len(encodings)} faces for {len(set(names))} individuals.")
        
    def _save_encodings(self, names: List[str], encodings: List[Any]) -> None:
        """
        Save face encodings to file
        
        Args:
            names: List of person names corresponding to encodings
            encodings: List of face encodings
        """
        name_encodings = {"names": names, "encodings": encodings}
        with self.encodings_path.open(mode="wb") as f:
            pickle.dump(name_encodings, f)
        logger.info(f"Saved encodings to {self.encodings_path}")
        
    def load_encodings(self) -> Dict[str, Union[List[str], List[Any]]]:
        """
        Load face encodings from file
        
        Returns:
            Dictionary with 'names' and 'encodings' keys
        """
        if not self.encodings_path.exists():
            logger.error(f"Encodings file not found: {self.encodings_path}")
            return {"names": [], "encodings": []}
            
        try:
            with self.encodings_path.open(mode="rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading encodings: {e}")
            return {"names": [], "encodings": []}
            
    def add_face(self, image_path: str, name: str) -> bool:
        """
        Add a new face to the training data and update encodings
        
        Args:
            image_path: Path to the image containing the face
            name: Name of the person
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the directory created in config.py
            person_dir = TRAINING_DIR / name
            
            # Get the next available filename
            existing_files = list(person_dir.glob("*.jpg"))
            new_filename = f"{len(existing_files) + 1}.jpg"
            new_file_path = person_dir / new_filename
            
            # Copy the image file
            import shutil
            shutil.copy(image_path, new_file_path)
            
            logger.info(f"Added new face for {name}: {new_file_path}")
            
            # Re-encode all faces to update the database
            self.encode_known_faces()
            
            return True
        except Exception as e:
            logger.error(f"Error adding face: {e}")
            return False
            
    def register_person_from_camera(self, camera, name: str, num_images: int = 10) -> bool:
        """
        Register a new person by capturing their face from camera
        
        Args:
            camera: Camera handler instance
            name: Name of the person
            num_images: Number of images to capture
            
        Returns:
            True if successful, False otherwise
        """
        # Normalize the name (lowercase, replace spaces with underscores)
        normalized_name = name.lower().replace(" ", "_")
        
        logger.info(f"Starting registration for {normalized_name}")
        
        if not camera.start():
            logger.error("Failed to start camera for registration")
            return False
        
        try:
            saved_paths = []
            count = 0
            
            print(f"Capturing {num_images} photos for {name}...")
            print("Position your face in the camera and press SPACE to capture each photo.")
            print("Press ESC to cancel.")
            
            while count < num_images:
                # Get frame
                frame = camera.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Display with instruction
                cv2.putText(frame, f"Press SPACE to capture ({count+1}/{num_images})", 
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("Register New Face", frame)
                
                # Wait for key press
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC key
                    logger.info("Registration cancelled by user")
                    return False
                elif key == 32:  # SPACE key
                    # Use the directory created in config.py
                    person_dir = TRAINING_DIR / normalized_name
                    
                    # Generate filename
                    image_path = str(person_dir / f"{count+1}.jpg")
                    
                    # Save image
                    cv2.imwrite(image_path, frame)
                    saved_paths.append(image_path)
                    logger.info(f"Captured image {count+1}/{num_images} for {normalized_name}")
                    print(f"Captured image {count+1}/{num_images}")
                    count += 1
        
        finally:
            camera.stop()
            cv2.destroyAllWindows()
        
        if saved_paths:
            logger.info(f"Successfully captured {len(saved_paths)} images for {normalized_name}")
            # Re-encode all faces to update the database
            self.encode_known_faces()
            return True
        
        return False 