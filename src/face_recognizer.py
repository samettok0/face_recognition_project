from collections import Counter
from typing import Dict, List, Union, Any, Tuple, Optional
import numpy as np
import face_recognition
import cv2
from PIL import Image, ImageDraw

from .config import HOG_MODEL, ENCODINGS_FILE
from .face_encoder import FaceEncoder
from .utils import draw_bounding_box, logger, draw_recognition_feedback_on_frame

class FaceRecognizer:
    def __init__(self, model: str = HOG_MODEL, recognition_threshold: float = 0.5):
        """
        Initialize the face recognizer
        
        Args:
            model: Face detection model to use ('hog' or 'cnn')
            recognition_threshold: Threshold for face recognition (lower = stricter)
        """
        self.model = model
        self.recognition_threshold = recognition_threshold
        self.face_encoder = FaceEncoder(model=model)
        # Load encodings immediately
        self.loaded_encodings = self.face_encoder.load_encodings()
        
    def reload_encodings(self):
        """Reload face encodings from disk"""
        self.loaded_encodings = self.face_encoder.load_encodings()
        return len(self.loaded_encodings.get("encodings", []))

    def _detect_and_encode_faces(self, image: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], List[np.ndarray]]:
        """
        Detect faces and create face encodings for an image
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Tuple of (face_locations, face_encodings)
        """
        # Ensure image is in RGB format - convert if necessary
        try:
            # First check if image is valid
            if image is None or image.size == 0:
                logger.error("Empty or invalid image received")
                return [], []
            
            # Check if grayscale (2D array)
            if len(image.shape) == 2:
                # Convert grayscale to RGB
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            # Handle color images (3D array)
            elif len(image.shape) == 3:
                if image.shape[2] == 4:  # RGBA format
                    image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
                elif image.shape[2] == 3:  # Could be BGR from OpenCV
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                elif image.shape[2] == 1:  # Single channel color format
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                # Unknown format - try to normalize
                logger.warning(f"Unusual image format with shape: {image.shape}")
                # Convert to 8-bit if needed
                if image.dtype != np.uint8:
                    image = (image * 255).astype(np.uint8)
                
                # Force conversion to RGB as a last resort
                if len(image.shape) == 3 and image.shape[2] >= 3:
                    image = image[:, :, :3]  # Take first 3 channels
                else:
                    # Create a 3-channel image
                    h, w = image.shape[:2]
                    rgb_image = np.zeros((h, w, 3), dtype=np.uint8)
                    # Copy the first channel to all RGB channels
                    rgb_image[:, :, 0] = image[:, :, 0] if len(image.shape) == 3 else image
                    rgb_image[:, :, 1] = image[:, :, 0] if len(image.shape) == 3 else image
                    rgb_image[:, :, 2] = image[:, :, 0] if len(image.shape) == 3 else image
                    image = rgb_image
            
            # Make sure we have 8-bit per channel
            if image.dtype != np.uint8:
                image = image.astype(np.uint8)
            
            # Detect faces
            face_locations = face_recognition.face_locations(
                image, model=self.model
            )
            
            # Create encodings for detected faces
            face_encodings = face_recognition.face_encodings(
                image, face_locations
            )
            
            return face_locations, face_encodings
            
        except Exception as e:
            logger.error(f"Error processing image for face detection: {e}")
            return [], []
        
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
        
        # Load the input image
        input_image = face_recognition.load_image_file(image_location)
        
        # Detect faces and create their encodings
        input_face_locations, input_face_encodings = self._detect_and_encode_faces(input_image)
        
        # Process each detected face
        results = []
        for bounding_box, unknown_encoding in zip(input_face_locations, input_face_encodings):
            name, confidence = self._recognize_face_with_confidence(unknown_encoding)
            results.append((bounding_box, name))
            
        logger.info(f"Found {len(results)} faces in image")
        
        # Display result if requested
        if display_result:
            self._display_results(input_image, results)
            
        return results
        
    def recognize_face_in_frame(self, frame: np.ndarray) -> List[Tuple[Tuple[int, int, int, int], str, float]]:
        """
        Recognizes faces in a video frame
        
        Args:
            frame: Video frame as numpy array
            
        Returns:
            List of tuples containing face locations, names, and confidence scores
        """
        try:
            # Check if frame is valid
            if frame is None or frame.size == 0:
                logger.warning("Invalid frame received in recognize_face_in_frame")
                return []
                
            # Detect faces and create their encodings
            face_locations, face_encodings = self._detect_and_encode_faces(frame)
            
            # Process each detected face
            results = []
            for bounding_box, unknown_encoding in zip(face_locations, face_encodings):
                name, confidence = self._recognize_face_with_confidence(unknown_encoding)
                results.append((bounding_box, name, confidence))
                
            return results
        except Exception as e:
            logger.error(f"Error in face recognition: {e}")
            return []
    
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
        
    def _recognize_face_with_confidence(self, unknown_encoding: np.ndarray) -> Tuple[str, float]:
        """
        Matches an unknown face encoding against known encodings with confidence score.
        
        Args:
            unknown_encoding: Face encoding to identify
            
        Returns:
            Tuple of (name, confidence_score)
        """
        if not self.loaded_encodings.get("encodings", []):
            return "Unknown", 0.0
            
        # Get face distances (lower = more similar)
        face_distances = face_recognition.face_distance(
            self.loaded_encodings["encodings"], unknown_encoding
        )
        
        if len(face_distances) == 0:
            return "Unknown", 0.0
            
        # Find best match
        best_match_index = np.argmin(face_distances)
        min_distance = face_distances[best_match_index]
        
        # Convert distance to confidence (0-1)
        confidence = 1.0 - min_distance
        
        # If confidence is high enough, return the name
        if confidence >= self.recognition_threshold:
            return self.loaded_encodings["names"][best_match_index], confidence
        
        return "Unknown", confidence
        
    def _display_results(self, image: np.ndarray, 
                         results: List[Tuple[Tuple[int, int, int, int], str]]) -> None:
        """
        Display recognition results with bounding boxes
        
        Args:
            image: Input image as numpy array
            results: List of face locations and names
        """
        # Use the OpenCV-based approach by default - more consistent with video processing
        annotated_image = draw_recognition_feedback_on_frame(image, results, include_confidence=False)
        cv2.imshow("Recognition Results", annotated_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        # Alternative PIL-based approach (kept for reference)
        # pillow_image = Image.fromarray(image)
        # draw = ImageDraw.Draw(pillow_image)
        # for bounding_box, name in results:
        #     draw_bounding_box(draw, bounding_box, name)
        # pillow_image.show() 