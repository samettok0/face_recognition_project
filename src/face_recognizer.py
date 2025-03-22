from collections import Counter
from typing import Dict, List, Union, Any, Tuple, Optional
import numpy as np
import face_recognition
from PIL import Image, ImageDraw

from .config import HOG_MODEL, ENCODINGS_FILE
from .face_encoder import FaceEncoder
from .utils import draw_bounding_box, get_logger

logger = get_logger(__name__)

class FaceRecognizer:
    def __init__(self, model: str = HOG_MODEL):
        """
        Initialize the face recognizer
        
        Args:
            model: Face detection model to use ('hog' or 'cnn')
        """
        self.model = model
        self.face_encoder = FaceEncoder(model=model)
        
    def recognize_faces(self, image_location: str, display_result: bool = True) -> List[Tuple[Tuple[int, int, int, int], str]]:
        """
        Recognizes faces in an image
        
        Args:
            image_location: Path to the image to analyze
            display_result: Whether to display the result with bounding boxes
            
        Returns:
            List of tuples containing face locations and names
        """
        logger.info(f"Recognizing faces in {image_location}")
        
        # Load encodings
        loaded_encodings = self.face_encoder.load_encodings()
        
        # Load and process the input image
        input_image = face_recognition.load_image_file(image_location)
        
        # Detect faces and create their encodings
        input_face_locations = face_recognition.face_locations(
            input_image, model=self.model
        )
        input_face_encodings = face_recognition.face_encodings(
            input_image, input_face_locations
        )
        
        # Process each detected face
        results = []
        for bounding_box, unknown_encoding in zip(
            input_face_locations, input_face_encodings
        ):
            name = self._recognize_face(unknown_encoding, loaded_encodings)
            if not name:
                name = "Unknown"
            results.append((bounding_box, name))
            
        logger.info(f"Found {len(results)} faces in image")
        
        # Display result if requested
        if display_result:
            self._display_results(input_image, results)
            
        return results
        
    def recognize_face_in_frame(self, frame: np.ndarray) -> List[Tuple[Tuple[int, int, int, int], str]]:
        """
        Recognizes faces in a video frame
        
        Args:
            frame: Video frame as numpy array
            
        Returns:
            List of tuples containing face locations and names
        """
        # Load encodings
        loaded_encodings = self.face_encoder.load_encodings()
        
        # Detect faces and create their encodings
        face_locations = face_recognition.face_locations(
            frame, model=self.model
        )
        face_encodings = face_recognition.face_encodings(
            frame, face_locations
        )
        
        # Process each detected face
        results = []
        for bounding_box, unknown_encoding in zip(
            face_locations, face_encodings
        ):
            name = self._recognize_face(unknown_encoding, loaded_encodings)
            if not name:
                name = "Unknown"
            results.append((bounding_box, name))
            
        return results
    
    def _recognize_face(self, unknown_encoding: np.ndarray, 
                        loaded_encodings: Dict[str, Union[List[str], List[Any]]]) -> Optional[str]:
        """
        Matches an unknown face encoding against known encodings.
        
        Args:
            unknown_encoding: Face encoding to identify
            loaded_encodings: Database of known face encodings
            
        Returns:
            The most likely name match or None if no match found
        """
        if not loaded_encodings["encodings"]:
            return None
            
        # Compare the face with known faces
        boolean_matches = face_recognition.compare_faces(
            loaded_encodings["encodings"], unknown_encoding
        )
        
        # Count votes for each name that matched
        votes = Counter(
            name
            for match, name in zip(boolean_matches, loaded_encodings["names"])
            if match
        )
        
        # Return the name with the most votes
        if votes:
            return votes.most_common(1)[0][0]
        return None
        
    def _display_results(self, image: np.ndarray, 
                         results: List[Tuple[Tuple[int, int, int, int], str]]) -> None:
        """
        Display recognition results with bounding boxes
        
        Args:
            image: Input image as numpy array
            results: List of face locations and names
        """
        # Convert to PIL image for drawing
        pillow_image = Image.fromarray(image)
        draw = ImageDraw.Draw(pillow_image)
        
        # Draw each face
        for bounding_box, name in results:
            draw_bounding_box(draw, bounding_box, name)
            
        # Display the image
        pillow_image.show() 