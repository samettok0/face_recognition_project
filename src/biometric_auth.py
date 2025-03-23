import cv2
import time
import numpy as np
from typing import Optional, Callable, List, Tuple

from .camera_handler import CameraHandler
from .face_recognizer import FaceRecognizer
from .utils import get_logger

logger = get_logger(__name__)

class BiometricAuth:
    def __init__(self, recognition_threshold: float = 0.6,
                 consecutive_matches_required: int = 3,
                 model: str = "hog"):
        """
        Initialize the biometric authentication system
        
        Args:
            recognition_threshold: Threshold for face recognition (0-1, higher = stricter)
            consecutive_matches_required: Number of consecutive matches required for auth
            model: Face detection model to use (hog or cnn)
        """
        self.camera = CameraHandler()
        self.recognizer = FaceRecognizer(model=model, 
                                         recognition_threshold=recognition_threshold)
        self.consecutive_matches_required = consecutive_matches_required
        self.authorized_users = set()
        
    def add_authorized_user(self, username: str) -> None:
        """Add a user to the authorized users list"""
        self.authorized_users.add(username)
        logger.info(f"Added {username} to authorized users")
        
    def remove_authorized_user(self, username: str) -> None:
        """Remove a user from the authorized users list"""
        if username in self.authorized_users:
            self.authorized_users.remove(username)
            logger.info(f"Removed {username} from authorized users")
    
    def authenticate(self, max_attempts: int = 10, 
                    timeout: int = 30) -> Tuple[bool, Optional[str]]:
        """
        Authenticate a user using face recognition
        
        Args:
            max_attempts: Maximum number of frames to check
            timeout: Maximum time to wait for authentication in seconds
            
        Returns:
            Tuple of (success, username)
        """
        if not self.camera.start():
            logger.error("Failed to start camera")
            return False, None
            
        try:
            logger.info("Starting authentication")
            start_time = time.time()
            consecutive_matches = {}  # username -> count
            
            attempt = 0
            while attempt < max_attempts and (time.time() - start_time) < timeout:
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                    
                # Process frame and get recognition results
                results = self.recognizer.recognize_face_in_frame(frame)
                
                # Show feedback on frame
                self._add_recognition_feedback(frame, results)
                cv2.imshow("Authentication", frame)
                
                # Check for 'q' key to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # Check for authorized users
                for _, name, confidence in results:
                    if name != "Unknown" and name in self.authorized_users:
                        # Reset consecutive matches for all other users
                        for other_name in consecutive_matches:
                            if other_name != name:
                                consecutive_matches[other_name] = 0
                                
                        # Increment match count for this user
                        consecutive_matches[name] = consecutive_matches.get(name, 0) + 1
                        
                        # Check if we have enough consecutive matches
                        if consecutive_matches[name] >= self.consecutive_matches_required:
                            logger.info(f"Authentication successful: {name} (confidence: {confidence:.2f})")
                            self.unlock_lock(name)
                            return True, name
                
                attempt += 1
                time.sleep(0.1)  # Small delay between frames
                
            logger.info("Authentication failed: No authorized user recognized")
            return False, None
                
        finally:
            self.camera.stop()
            cv2.destroyAllWindows()
    
    def unlock_lock(self, username: str) -> None:
        """
        Placeholder method to unlock physical lock
        
        Args:
            username: Name of the authenticated user
        """
        # This is a placeholder - not implemented yet
        logger.info(f"UNLOCK REQUEST: Access granted to {username}")
        print(f"🔓 Access granted to {username}")
        # Future implementation will connect to physical lock mechanism
    
    def _add_recognition_feedback(self, frame, results):
        """Add visual feedback about recognition to the frame"""
        for (top, right, bottom, left), name, confidence in results:
            # Color based on recognition status (red=unknown, green=known)
            if name == "Unknown":
                color = (0, 0, 255)  # Red for unknown
            else:
                color = (0, 255, 0)  # Green for known
                
            # Draw rectangle around the face
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Draw background for text
            cv2.rectangle(frame, (left, bottom - 35), 
                        (right, bottom), color, cv2.FILLED)
            
            # Show name and confidence
            label = f"{name} ({confidence:.2f})"
            cv2.putText(frame, label, (left + 6, bottom - 6),
                       cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
    
    def run_continuous_monitoring(self, 
                               on_success: Optional[Callable[[str], None]] = None):
        """
        Run continuous face monitoring and authentication
        
        Args:
            on_success: Callback function to run when authentication succeeds
        """
        if not self.camera.start():
            logger.error("Failed to start camera")
            return
            
        try:
            logger.info("Starting continuous monitoring")
            consecutive_matches = {}
            
            while True:
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Process every frame
                results = self.recognizer.recognize_face_in_frame(frame)
                
                # Update the frame with recognition results
                self._add_recognition_feedback(frame, results)
                cv2.imshow("Monitoring", frame)
                
                # Process authentication
                for _, name, confidence in results:
                    if name != "Unknown" and name in self.authorized_users:
                        consecutive_matches[name] = consecutive_matches.get(name, 0) + 1
                        
                        # If we've seen this person enough times, authenticate them
                        if consecutive_matches[name] >= self.consecutive_matches_required:
                            logger.info(f"Authentication successful: {name}")
                            self.unlock_lock(name)
                            
                            if on_success:
                                on_success(name)
                                
                            # Reset consecutive matches
                            consecutive_matches = {}
                            # Wait a bit before trying to authenticate again
                            time.sleep(3)
                    else:
                        # Reset counter if we don't see an authorized person
                        consecutive_matches = {}
                
                # Check for 'q' key to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
                time.sleep(0.03)  # Slight delay to reduce CPU usage
                
        finally:
            self.camera.stop()
            cv2.destroyAllWindows() 