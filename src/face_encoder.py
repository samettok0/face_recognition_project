import pickle
from pathlib import Path
from typing import Dict, List, Union, Any, Tuple
import face_recognition
import logging

from .config import TRAINING_DIR, ENCODINGS_FILE, HOG_MODEL
from .utils import get_logger

logger = get_logger(__name__)

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
            # Create directory for this person if it doesn't exist
            person_dir = TRAINING_DIR / name
            person_dir.mkdir(exist_ok=True)
            
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