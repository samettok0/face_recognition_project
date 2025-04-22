import cv2
import time
import numpy as np
from typing import Optional, Callable, List, Tuple

from .camera_handler import CameraHandler
from .face_recognizer import FaceRecognizer
from .utils import logger, draw_recognition_feedback_on_frame

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
    
    def _initialize_camera_and_process_frames(self, 
                                            window_name: str,
                                            single_authentication: bool = True,
                                            max_attempts: int = 10,
                                            timeout: int = 30,
                                            on_success: Optional[Callable[[str], None]] = None) -> Tuple[bool, Optional[str]]:
        """
        Common method for camera initialization and face recognition processing
        
        Args:
            window_name: Name for the display window
            single_authentication: If True, returns after first successful authentication
            max_attempts: Maximum number of frames to check (for single auth mode)
            timeout: Maximum time to wait for authentication in seconds (for single auth mode)
            on_success: Callback function when authentication succeeds (for continuous mode)
            
        Returns:
            Tuple of (success, username) in single auth mode, or (False, None) in continuous mode
        """
        if not self.camera.start():
            logger.error("Failed to start camera")
            return False, None
            
        try:
            logger.info(f"Starting {'authentication' if single_authentication else 'continuous monitoring'}")
            start_time = time.time()
            consecutive_matches = {}  # username -> count
            
            attempt = 0
            while (single_authentication and attempt < max_attempts and (time.time() - start_time) < timeout) or not single_authentication:
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                    
                # Process frame and get recognition results
                results = self.recognizer.recognize_face_in_frame(frame)
                
                # Show feedback on frame
                annotated_frame = draw_recognition_feedback_on_frame(frame, results)
                cv2.imshow(window_name, annotated_frame)
                
                # Check for 'q' key to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # Check for authorized users
                for _, name, confidence in results:
                    if name != "Unknown" and name in self.authorized_users:
                        # Reset consecutive matches for all other users in single auth mode
                        if single_authentication:
                            for other_name in consecutive_matches:
                                if other_name != name:
                                    consecutive_matches[other_name] = 0
                                
                        # Increment match count for this user
                        consecutive_matches[name] = consecutive_matches.get(name, 0) + 1
                        
                        # Check if we have enough consecutive matches
                        if consecutive_matches[name] >= self.consecutive_matches_required:
                            logger.info(f"Authentication successful: {name}" +
                                       (f" (confidence: {confidence:.2f})" if single_authentication else ""))
                            self.unlock_lock(name)
                            
                            if single_authentication:
                                return True, name
                            elif on_success:
                                on_success(name)
                                
                            # In continuous mode, reset and continue after success
                            if not single_authentication:
                                consecutive_matches = {}
                                time.sleep(3)  # Wait before next authentication attempt
                    elif not single_authentication:
                        # Reset counter if we don't see an authorized person (continuous mode only)
                        consecutive_matches = {}
                
                attempt += 1
                time.sleep(0.03 if not single_authentication else 0.1)  # Small delay between frames
                
            if single_authentication:
                logger.info("Authentication failed: No authorized user recognized")
                return False, None
            return False, None  # Should not reach here in continuous mode
                
        finally:
            self.camera.stop()
            cv2.destroyAllWindows()
    
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
        return self._initialize_camera_and_process_frames(
            window_name="Authentication",
            single_authentication=True,
            max_attempts=max_attempts,
            timeout=timeout
        )
    
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
    
    def run_continuous_monitoring(self, 
                                on_success: Optional[Callable[[str], None]] = None):
        """
        Run continuous face monitoring and authentication
        
        Args:
            on_success: Callback function to run when authentication succeeds
        """
        self._initialize_camera_and_process_frames(
            window_name="Monitoring",
            single_authentication=False,
            on_success=on_success
        ) 