import cv2
import time
import logging
import threading
import queue
from typing import Optional, Callable, List, Tuple
from deepface import DeepFace

from .camera_handler import CameraHandler
from .face_recognizer import FaceRecognizer
from .utils import draw_recognition_feedback_on_frame
from .gpio_lock import GPIOLock
from .config import GPIO_LOCK_PIN, LOCK_UNLOCK_DURATION, ENABLE_GPIO_LOCK, GPIO_LOCK_ACTIVE_HIGH

# Set up logging
logger = logging.getLogger(__name__)

class BiometricAuth:
    """
    Biometric authentication system using face recognition
    
    This class handles the complete authentication pipeline including:
    - Face detection and recognition
    - Anti-spoofing verification
    - Physical lock control via GPIO
    - Continuous monitoring capabilities
    """
    
    def __init__(self, recognition_threshold: float = 0.6,
                 consecutive_matches_required: int = 3,
                 model: str = "hog",
                 use_threading: bool = True,
                 use_anti_spoofing: bool = True):
        """
        Initialize the biometric authentication system
        
        Args:
            recognition_threshold: Minimum confidence for face recognition
            consecutive_matches_required: Number of consecutive matches needed for authentication
            model: Face detection model ("hog" or "cnn")
            use_threading: Whether to use threading for face recognition
            use_anti_spoofing: Whether to enable anti-spoofing detection
        """
        self.recognition_threshold = recognition_threshold
        self.consecutive_matches_required = consecutive_matches_required
        self.use_threading = use_threading
        self.use_anti_spoofing = use_anti_spoofing
        
        # Initialize components
        self.recognizer = FaceRecognizer(recognition_threshold=recognition_threshold, model=model)
        self.camera = CameraHandler()
        self.authorized_users = set()
        
        # Initialize GPIO lock
        if ENABLE_GPIO_LOCK:
            self.gpio_lock = GPIOLock(gpio_pin=GPIO_LOCK_PIN, unlock_duration=LOCK_UNLOCK_DURATION, active_high=GPIO_LOCK_ACTIVE_HIGH)
        else:
            self.gpio_lock = None
            logger.info("GPIO lock disabled in configuration")
        
        # Threading components
        if use_threading:
            self.processing_queue = queue.Queue(maxsize=2)
            self.results_queue = queue.Queue()
            self.should_stop = threading.Event()
            self.recognition_thread = None

    def add_authorized_user(self, username: str) -> None:
        """Add a user to the authorized users list"""
        self.authorized_users.add(username)
        logger.info(f"Added authorized user: {username}")

    def remove_authorized_user(self, username: str) -> None:
        """Remove a user from the authorized users list"""
        if username in self.authorized_users:
            self.authorized_users.remove(username)
            logger.info(f"Removed authorized user: {username}")

    def _recognition_worker(self):
        """Worker function for face recognition thread"""
        logger.info("Face recognition thread started")
        while not self.should_stop.is_set():
            try:
                # Get the newest frame from the queue with timeout
                frame = self.processing_queue.get(timeout=0.1)
                
                # Process frame and get recognition results
                results = self.recognizer.recognize_face_in_frame(frame)
                
                # Check for anti-spoofing if enabled
                if self.use_anti_spoofing and results:
                    # Create a copy for anti-spoofing (we need the original frame for display)
                    frame_copy = frame.copy()
                    verified_results = []
                    
                    for bbox, name, confidence in results:
                        # Extract face region for anti-spoofing check
                        top, right, bottom, left = bbox
                        face_img = frame_copy[top:bottom, left:right]
                        
                        # Only perform anti-spoofing on faces that were recognized
                        if name != "Unknown" and name in self.authorized_users:
                            try:
                                # Perform anti-spoofing check using DeepFace
                                face_objs = DeepFace.extract_faces(img_path=face_img, 
                                                                 anti_spoofing=True,
                                                                 enforce_detection=False)
                                
                                # Check if face is real
                                is_real = all(face_obj.get("is_real", False) for face_obj in face_objs)
                                
                                if is_real:
                                    verified_results.append((bbox, name, confidence))
                                else:
                                    verified_results.append((bbox, "Fake", confidence))
                                    logger.warning(f"Fake face detected during authentication attempt for {name}")
                            except Exception as e:
                                logger.error(f"Anti-spoofing check failed: {e}")
                                # Still include the face but mark as potentially unsafe
                                verified_results.append((bbox, name, confidence))
                        else:
                            # For unknown faces, just pass through
                            verified_results.append((bbox, name, confidence))
                    
                    # Update results with anti-spoofing check
                    results = verified_results
                
                # Put results in results queue
                self.results_queue.put(results)
                
                # Mark task as done
                self.processing_queue.task_done()
            except queue.Empty:
                # No frame available, just continue
                continue
            except Exception as e:
                logger.error(f"Error in recognition thread: {e}")
                # Mark task as done if we had a frame
                if not self.processing_queue.empty():
                    self.processing_queue.task_done()
        
        logger.info("Face recognition thread stopped")
    
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
            
            # Start recognition thread if using threading
            if self.use_threading:
                self.should_stop.clear()
                self.recognition_thread = threading.Thread(target=self._recognition_worker)
                self.recognition_thread.daemon = True
                self.recognition_thread.start()
            
            last_results = []
            attempt = 0
            while (single_authentication and attempt < max_attempts and (time.time() - start_time) < timeout) or not single_authentication:
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Process frame and get recognition results
                if self.use_threading:
                    # Put frame in queue for processing
                    # If queue is full, replace the old frame (we only care about the latest frame)
                    if self.processing_queue.full():
                        try:
                            self.processing_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.processing_queue.put(frame)
                    
                    # Get results if available, otherwise use last results
                    try:
                        results = self.results_queue.get_nowait()
                        last_results = results
                        self.results_queue.task_done()
                    except queue.Empty:
                        results = last_results
                else:
                    # Process frame directly if not using threading
                    results = self.recognizer.recognize_face_in_frame(frame)
                    
                    # Perform anti-spoofing check without threading
                    if self.use_anti_spoofing and results:
                        # Create a copy for anti-spoofing
                        frame_copy = frame.copy()
                        verified_results = []
                        
                        for bbox, name, confidence in results:
                            # Extract face region for anti-spoofing check
                            top, right, bottom, left = bbox
                            face_img = frame_copy[top:bottom, left:right]
                            
                            # Only perform anti-spoofing on faces that were recognized
                            if name != "Unknown" and name in self.authorized_users:
                                try:
                                    # Perform anti-spoofing check using DeepFace
                                    face_objs = DeepFace.extract_faces(img_path=face_img, 
                                                                     anti_spoofing=True,
                                                                     enforce_detection=False)
                                    
                                    # Check if face is real
                                    is_real = all(face_obj.get("is_real", False) for face_obj in face_objs)
                                    
                                    if is_real:
                                        verified_results.append((bbox, name, confidence))
                                    else:
                                        verified_results.append((bbox, "Fake", confidence))
                                        logger.warning(f"Fake face detected during authentication attempt for {name}")
                                except Exception as e:
                                    logger.error(f"Anti-spoofing check failed: {e}")
                                    # Still include the face but mark as potentially unsafe
                                    verified_results.append((bbox, name, confidence))
                            else:
                                # For unknown faces, just pass through
                                verified_results.append((bbox, name, confidence))
                        
                        # Update results with anti-spoofing check
                        results = verified_results
                
                # Show feedback on frame
                annotated_frame = draw_recognition_feedback_on_frame(frame, results)
                cv2.imshow(window_name, annotated_frame)
                
                # Check for 'q' key to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # Check for authorized users
                for bbox, name, confidence in results:
                    # Skip unauthorized or fake faces
                    if name == "Unknown" or name == "Fake" or name not in self.authorized_users:
                        continue
                        
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
                
                attempt += 1
                time.sleep(0.03 if not single_authentication else 0.1)  # Small delay between frames
                
            if single_authentication:
                logger.info("Authentication failed: No authorized user recognized")
                return False, None
            return False, None  # Should not reach here in continuous mode
                
        finally:
            # Stop recognition thread if using threading
            if self.use_threading and self.recognition_thread:
                self.should_stop.set()
                self.recognition_thread.join(timeout=1.0)
            
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
        Unlock the physical lock for an authenticated user
        
        Args:
            username: Name of the authenticated user
        """
        try:
            if self.gpio_lock:
                # Use physical GPIO lock
                success = self.gpio_lock.unlock(username)
                if success:
                    logger.info(f"🔓 LOCK UNLOCKED: Access granted to {username}")
                else:
                    logger.error(f"Failed to unlock lock for {username}")
            else:
                # Fallback to simulation if GPIO lock is disabled
                logger.info(f"🔓 SIMULATED UNLOCK: Access granted to {username} (GPIO disabled)")
                print(f"🔓 SIMULATED UNLOCK: Access granted to {username}")
                print("   (GPIO lock is disabled in configuration)")
                
        except Exception as e:
            logger.error(f"Error during unlock operation for {username}: {e}")
            print(f"❌ Error during unlock operation: {e}")
    
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
    
    def cleanup(self):
        """
        Clean up resources including GPIO lock
        """
        try:
            # Stop any running threads
            if self.use_threading and self.recognition_thread:
                self.should_stop.set()
                self.recognition_thread.join(timeout=1.0)
            
            # Stop camera
            if hasattr(self, 'camera'):
                self.camera.stop()
            
            # Clean up GPIO lock
            if self.gpio_lock:
                self.gpio_lock.cleanup()
                
            logger.info("BiometricAuth cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during BiometricAuth cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup() 