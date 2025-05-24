import cv2
import time
import numpy as np
import threading
import queue
from typing import Optional, Callable, List, Tuple
from deepface import DeepFace
import platform
import sys

from .camera_handler import CameraHandler
from .face_recognizer import FaceRecognizer
from .utils import logger, draw_recognition_feedback_on_frame
from .config import LOCK_GPIO_PIN, LOCK_OPEN_DURATION, LOCK_ACTIVE_HIGH

# Check if we're running on a Raspberry Pi and import GPIO if available
is_raspberry_pi = platform.machine().startswith('arm')
if is_raspberry_pi:
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    except ImportError:
        GPIO_AVAILABLE = False
        logger.warning("RPi.GPIO module not available. Lock control will be simulated.")
else:
    GPIO_AVAILABLE = False
    logger.info("Not running on Raspberry Pi. Lock control will be simulated.")

class BiometricAuth:
    def __init__(self, recognition_threshold: float = 0.6,
                 consecutive_matches_required: int = 3,
                 model: str = "hog",
                 use_threading: bool = True,
                 use_anti_spoofing: bool = True):
        """
        Initialize the biometric authentication system
        
        Args:
            recognition_threshold: Threshold for face recognition (0-1, higher = stricter)
            consecutive_matches_required: Number of consecutive matches required for auth
            model: Face detection model to use (hog or cnn)
            use_threading: Whether to use a separate thread for face recognition
            use_anti_spoofing: Whether to enable anti-spoofing checks
        """
        self.camera = CameraHandler()
        self.recognizer = FaceRecognizer(model=model, 
                                         recognition_threshold=recognition_threshold)
        self.consecutive_matches_required = consecutive_matches_required
        self.authorized_users = set()
        self.use_anti_spoofing = use_anti_spoofing
        
        # Threading-related attributes
        self.use_threading = use_threading
        self.recognition_thread = None
        self.processing_queue = queue.Queue(maxsize=1)  # Only process most recent frame
        self.results_queue = queue.Queue()
        self.should_stop = threading.Event()
        
    def add_authorized_user(self, username: str) -> None:
        """Add a user to the authorized users list"""
        self.authorized_users.add(username)
        logger.info(f"Added {username} to authorized users")
        
    def remove_authorized_user(self, username: str) -> None:
        """Remove a user from the authorized users list"""
        if username in self.authorized_users:
            self.authorized_users.remove(username)
            logger.info(f"Removed {username} from authorized users")
    
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
        Control the physical lock connected to GPIO pin
        
        Args:
            username: Name of the authenticated user
        """
        logger.info(f"UNLOCK REQUEST: Access granted to {username}")
        print(f"🔓 Access granted to {username}")
        
        if GPIO_AVAILABLE:
            try:
                # Setup GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(LOCK_GPIO_PIN, GPIO.OUT)
                
                # Set the pin to active state based on configuration
                active_state = GPIO.HIGH if LOCK_ACTIVE_HIGH else GPIO.LOW
                inactive_state = GPIO.LOW if LOCK_ACTIVE_HIGH else GPIO.HIGH
                
                # Activate the lock
                GPIO.output(LOCK_GPIO_PIN, active_state)
                logger.info(f"Lock activated via GPIO {LOCK_GPIO_PIN}")
                
                # Keep the lock open for the specified duration
                time.sleep(LOCK_OPEN_DURATION)
                
                # Deactivate the lock
                GPIO.output(LOCK_GPIO_PIN, inactive_state)
                logger.info(f"Lock deactivated after {LOCK_OPEN_DURATION} seconds")
                
                # Cleanup GPIO
                GPIO.cleanup(LOCK_GPIO_PIN)
                
            except Exception as e:
                logger.error(f"Error controlling lock via GPIO: {e}")
                print(f"⚠️ Error controlling lock: {e}")
        else:
            # Simulate the lock behavior when GPIO is not available
            print(f"🔓 Simulating lock open for {LOCK_OPEN_DURATION} seconds")
            time.sleep(LOCK_OPEN_DURATION)
            print(f"🔒 Simulating lock close")
            logger.info(f"Simulated lock control (GPIO not available)")
    
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