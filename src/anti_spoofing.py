"""
Anti-spoofing module for face recognition using DeepFace

This module provides anti-spoofing functionality to detect fake/spoofed faces
during authentication attempts.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Union, Optional, Any
from deepface import DeepFace
from .utils import logger, draw_recognition_feedback_on_frame, draw_enhanced_anti_spoofing_feedback, resize_for_deepface

# Default threshold for live detection
LIVE_THRESHOLD = 0.5

class AntiSpoofing:
    def __init__(self, min_confidence: float = 0.9):
        """
        Initialize anti-spoofing detector
        
        Args:
            min_confidence: Minimum confidence threshold for anti-spoofing (0-1)
        """
        self.min_confidence = min_confidence
        logger.info(f"Anti-spoofing initialized with confidence threshold: {min_confidence}")
    
    def set_threshold(self, t: float):
        """Set the threshold for live detection"""
        global LIVE_THRESHOLD
        LIVE_THRESHOLD = t
        logger.info(f"Anti-spoofing threshold set to: {t}")
    
    def is_live(self, frame) -> bool:
        """Determine if a frame contains a live face"""
        try:
            # Resize frame for better performance on Raspberry Pi
            resized_frame = resize_for_deepface(frame)
            logger.info(f"Resized frame from {frame.shape[1]}x{frame.shape[0]} to 320x240 for DeepFace")
            
            # Use OpenCV detector for faster processing on Raspberry Pi
            face_objs = DeepFace.extract_faces(
                img_path=resized_frame, 
                anti_spoofing=True,
                enforce_detection=False,
                detector_backend="opencv"  # Use lighter OpenCV detector for Pi
            )
            
            if not face_objs:
                logger.warning("No faces detected in anti-spoofing check")
                return False
            
            # Check if any face is real - DeepFace's anti_spoofing adds 'is_real' property
            for face_obj in face_objs:
                if "is_real" in face_obj and face_obj["is_real"]:
                    logger.info("Live face detected")
                    return True
            
            # If no face determined to be real, return False
            logger.warning("No live face detected - possible spoofing attempt")
            return False
            
        except Exception as e:
            logger.error(f"Error in live detection: {e}")
            # For security, return False on errors (fail-closed approach)
            # This prevents authentication when anti-spoofing fails
            return False
    
    def check_image(self, img_path: str) -> bool:
        """
        Check if faces in an image are real
        
        Args:
            img_path: Path to image file
            
        Returns:
            True if all faces are real, False if any are fake or none detected
        """
        try:
            # If img_path is a string (file path), read and resize the image
            if isinstance(img_path, str):
                # Load the image
                img = cv2.imread(img_path)
                if img is not None:
                    # Resize for better performance
                    img = resize_for_deepface(img)
                    # Use the resized image instead of the file path
                    face_objs = DeepFace.extract_faces(
                        img_path=img, 
                        anti_spoofing=True,
                        detector_backend="opencv"  # Faster for Pi
                    )
                else:
                    # If image couldn't be read, try with original path
                    face_objs = DeepFace.extract_faces(
                        img_path=img_path, 
                        anti_spoofing=True,
                        detector_backend="opencv"  # Faster for Pi
                    )
            else:
                # If not a string path, use as is
                face_objs = DeepFace.extract_faces(
                    img_path=img_path, 
                    anti_spoofing=True,
                    detector_backend="opencv"  # Faster for Pi
                )
                
            if not face_objs:
                logger.warning("No faces detected in image during anti-spoofing check")
                return False
                
            # Check if all faces are real using the direct is_real property
            all_real = all(face_obj.get("is_real", False) for face_obj in face_objs)
            if not all_real:
                logger.warning(f"Fake face detected in image: {img_path}")
            
            return all_real
        except Exception as e:
            logger.error(f"Error in anti-spoofing check for image {img_path}: {e}")
            return False
    
    def check_face_region(self, frame: np.ndarray, 
                         face_location: Tuple[int, int, int, int]) -> bool:
        """
        Check if a face region in a frame is real
        
        Args:
            frame: Video frame/image as numpy array
            face_location: Face location as (top, right, bottom, left)
            
        Returns:
            True if face is real, False if fake or error occurred
        """
        try:
            top, right, bottom, left = face_location
            face_img = frame[top:bottom, left:right]
            
            # Resize face for better performance - smaller size for face regions
            resized_face = resize_for_deepface(face_img, width=160, height=160)
            
            # Use OpenCV detector for faster processing on Raspberry Pi
            face_objs = DeepFace.extract_faces(
                img_path=resized_face, 
                anti_spoofing=True,
                enforce_detection=False,
                detector_backend="opencv"  # Faster for Pi
            )
            
            if not face_objs:
                logger.warning("No faces detected in region during anti-spoofing check")
                return False
            
            # Check if the face is real using the 'is_real' property
            for face_obj in face_objs:
                if "is_real" in face_obj and face_obj["is_real"]:
                    return True
            
            logger.warning("Fake face detected in frame region")
            return False
            
        except Exception as e:
            logger.error(f"Error in anti-spoofing check for face region: {e}")
            return False
    
    def process_frame(self, frame: np.ndarray, 
                     face_results: List[Tuple[Tuple[int, int, int, int], str, float]]) -> List[Tuple[Tuple[int, int, int, int], str, float]]:
        """
        Process a frame and filter out fake faces from recognition results
        
        Args:
            frame: Video frame/image as numpy array
            face_results: List of face recognition results (bounding_box, name, confidence)
            
        Returns:
            Filtered list of face recognition results with fake faces marked
        """
        if not face_results:
            return []
            
        frame_copy = frame.copy()
        verified_results = []
        
        for bbox, name, confidence in face_results:
            # Extract face region for anti-spoofing check
            top, right, bottom, left = bbox
            face_img = frame_copy[top:bottom, left:right]
            
            # Only perform detailed anti-spoofing on recognized faces
            if name != "Unknown":
                try:
                    # Resize face for better performance
                    resized_face = resize_for_deepface(face_img, width=160, height=160)
                    
                    # Use OpenCV detector for faster processing on Raspberry Pi
                    face_objs = DeepFace.extract_faces(
                        img_path=resized_face, 
                        anti_spoofing=True,
                        enforce_detection=False,
                        detector_backend="opencv"  # Faster for Pi
                    )
                    
                    # Check if the face is real directly with is_real property
                    is_real = any(face_obj.get("is_real", False) for face_obj in face_objs)
                    
                    if is_real:
                        verified_results.append((bbox, name, confidence))
                    else:
                        verified_results.append((bbox, "Fake", confidence))
                        logger.warning(f"Fake face detected for {name}")
                except Exception as e:
                    logger.error(f"Anti-spoofing check failed: {e}")
                    # Mark as fake on errors for better security (fail-closed approach)
                    verified_results.append((bbox, "Fake", confidence))
                    logger.warning(f"Anti-spoofing error for {name} - marking as fake for security")
            else:
                # For unknown faces, just pass through
                verified_results.append((bbox, name, confidence))
        
        return verified_results
    
    def run_demo(self, camera_index: int = 0) -> None:
        """
        Run a demonstration of the anti-spoofing detection
        
        Args:
            camera_index: Camera device index to use
        """
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.error(f"Failed to open camera {camera_index}")
            return
            
        logger.info("Starting anti-spoofing demo")
        print("Press 'q' to quit")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Detect and analyze faces with anti-spoofing
                try:
                    # Resize frame for better performance on Raspberry Pi
                    resized_frame = resize_for_deepface(frame)
                    
                    # Use OpenCV detector for faster processing on Raspberry Pi
                    face_objs = DeepFace.extract_faces(
                        img_path=resized_frame, 
                        anti_spoofing=True,
                        enforce_detection=False,
                        detector_backend="opencv"  # Faster for Pi
                    )
                    
                    results = []
                    for face_obj in face_objs:
                        facial_area = face_obj.get("facial_area", {})
                        y = facial_area.get("y", 0)
                        x = facial_area.get("x", 0)
                        h = facial_area.get("h", 0)
                        w = facial_area.get("w", 0)
                        
                        # Convert to top, right, bottom, left format
                        bbox = (y, x + w, y + h, x)
                        
                        # Check if face is real directly from is_real property
                        is_real = face_obj.get("is_real", False)
                        name = "Real" if is_real else "Fake"
                        confidence = 1.0  # Placeholder
                        
                        results.append((bbox, name, confidence))
                    
                    # Add FPS counter for performance monitoring
                    if results:
                        # Determine liveness status for display
                        is_live = all(name == "Real" for bbox, name, confidence in results)
                        annotated_frame = draw_enhanced_anti_spoofing_feedback(frame, results, is_live)
                        cv2.putText(annotated_frame, f"Found {len(results)} faces", (10, 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    else:
                        annotated_frame = frame.copy()
                        cv2.putText(annotated_frame, "No faces detected", (10, 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    cv2.imshow("Anti-Spoofing Demo", annotated_frame)
                    
                except Exception as e:
                    logger.error(f"Error in anti-spoofing demo: {e}")
                    # Show error on frame for better user feedback
                    error_frame = frame.copy()
                    cv2.putText(error_frame, "Anti-spoofing Error!", (20, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(error_frame, str(e)[:50], (20, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
                    cv2.imshow("Anti-Spoofing Demo", error_frame)
                
                # Check for quit key
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            cap.release()
            cv2.destroyAllWindows()
            logger.info("Anti-spoofing demo ended")

# Simple command-line test if run directly
if __name__ == "__main__":
    spoof_detector = AntiSpoofing()
    spoof_detector.run_demo() 