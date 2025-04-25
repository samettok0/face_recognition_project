import cv2
import time
import os
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional

from .camera_handler import CameraHandler
from .head_pose_detector import HeadPoseDetector
from .utils import logger, create_flash_effect
from .config import TRAINING_DIR


class GuidedRegistration:
    """
    Guided registration with head pose detection for creating comprehensive training data
    """
    
    def __init__(self, camera: CameraHandler = None):
        """
        Initialize the guided registration
        
        Args:
            camera: Optional camera handler (will create one if not provided)
        """
        self.camera = camera if camera else CameraHandler()
        self.head_pose_detector = HeadPoseDetector()
        
        # Sequence of poses to capture
        self.pose_sequence = ["Forward", "Left", "Right", "Up", "Down"]
        
        # Timing settings
        self.stabilization_time = 2.0  # Seconds to wait for stable pose
        self.countdown_time = 3  # Seconds for countdown
        self.burst_delay = 0.5  # Seconds between consecutive photos in burst mode
        
        # Simple UI settings
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.8
        self.text_color = (255, 255, 255)
        self.success_color = (0, 255, 0)  # Green (BGR)
        self.error_color = (0, 0, 255)    # Red (BGR)
        self.accent_color = (0, 255, 255) # Yellow (BGR)

    def _create_user_dir(self, name: str) -> Path:
        """
        Create a directory for the user's training images
        
        Args:
            name: User's name
            
        Returns:
            Path to the created directory
        """
        # Create main training directory if it doesn't exist
        if not TRAINING_DIR.exists():
            TRAINING_DIR.mkdir(parents=True)
            
        # Create user directory
        user_dir = TRAINING_DIR / name
        if not user_dir.exists():
            user_dir.mkdir()
            
        return user_dir
    
    def _capture_image(self, frame: np.ndarray, 
                       user_dir: Path, pose: str, index: int) -> Optional[str]:
        """
        Capture and save an image
        
        Args:
            frame: Frame to save
            user_dir: Directory to save to
            pose: Current pose
            index: Image index
            
        Returns:
            Path to saved image or None if failed
        """
        # Create filename with timestamp
        timestamp = int(time.time())
        filename = f"{index:02d}_{pose}_{timestamp}.jpg"
        file_path = str(user_dir / filename)
        
        try:
            # Create a flash effect
            create_flash_effect(frame)
            
            # Save the image
            cv2.imwrite(file_path, frame)
            logger.info(f"Saved image to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return None
    
    def _draw_guidance(self, frame: np.ndarray, 
                       current_pose: str, pose_result: dict, 
                       images_captured: int, total_images: int,
                       countdown: int = None, pose_stable_time: float = None,
                       burst_mode: bool = False) -> np.ndarray:
        """
        Draw simplified guidance overlay on frame
        
        Args:
            frame: Frame to draw on
            current_pose: Current pose to capture
            pose_result: Result from head pose detection
            images_captured: Number of images captured for current pose
            total_images: Total images to capture per pose
            countdown: Optional countdown number to display
            pose_stable_time: How long the pose has been stable in seconds
            burst_mode: Whether burst mode is active
            
        Returns:
            Frame with guidance overlay
        """
        h, w, _ = frame.shape
        
        # Copy the frame for overlay
        guidance_frame = frame.copy()
        
        # 1. Draw instruction text at the top
        instruction = f"Please look {current_pose}"
        if burst_mode:
            instruction = "CAPTURING SEQUENCE - HOLD STILL"
        
        cv2.putText(
            guidance_frame,
            instruction,
            (20, 40),
            self.font,
            1.0,
            self.text_color,
            2
        )
        
        # 2. Draw progress information
        total_photos = len(self.pose_sequence) * total_images
        current_photo = (self.pose_sequence.index(current_pose) * total_images) + images_captured
        progress_text = f"Progress: {current_photo}/{total_photos} photos"
        
        cv2.putText(
            guidance_frame,
            progress_text,
            (20, 80),
            self.font,
            0.8,
            self.text_color,
            1
        )
        
        # 3. Draw pose detection status
        if pose_result["face_detected"]:
            detected_pose = pose_result["pose_label"]
            is_correct_pose = detected_pose == current_pose
            
            status_text = f"Detected: {detected_pose}"
            status_color = self.success_color if is_correct_pose else self.error_color
            
            cv2.putText(
                guidance_frame,
                status_text,
                (20, h - 60),
                self.font,
                0.8,
                status_color,
                2
            )
            
            # Draw stability info if correct pose
            if is_correct_pose and pose_stable_time is not None and not burst_mode:
                stability_text = f"Hold steady: {int(pose_stable_time)}/{int(self.stabilization_time)}s"
                
                cv2.putText(
                    guidance_frame,
                    stability_text,
                    (20, h - 30),
                    self.font,
                    0.8,
                    self.accent_color,
                    2
                )
        
        # 4. Draw countdown if active
        if countdown is not None:
            count_text = str(countdown)
            text_size = cv2.getTextSize(count_text, self.font, 5, 5)[0]
            text_x = (w - text_size[0]) // 2
            text_y = (h + text_size[1]) // 2
            
            cv2.putText(
                guidance_frame,
                count_text,
                (text_x, text_y),
                self.font,
                5,
                self.accent_color,
                5
            )
        
        # 5. Draw burst mode indicator if active
        elif burst_mode:
            burst_text = "BURST MODE - CAPTURING PHOTOS"
            cv2.putText(
                guidance_frame,
                burst_text,
                (w // 2 - 200, h - 30),
                self.font,
                1.0,
                self.error_color,
                2
            )
        
        return guidance_frame
    
    def run_guided_registration(self, name: str, images_per_pose: int = 2) -> bool:
        """
        Run the guided registration process
        
        Args:
            name: Name of the person to register
            images_per_pose: Number of images to capture per pose
            
        Returns:
            True if registration completed successfully, False otherwise
        """
        if not self.camera.start():
            logger.error("Failed to start camera")
            return False
        
        try:
            # Create directory for user
            user_dir = self._create_user_dir(name)
            
            total_captured = 0
            
            # Process each pose in sequence
            for pose_index, pose in enumerate(self.pose_sequence):
                # Reset counters for this pose
                pose_captured = 0
                pose_stable_start = None
                pose_stable_time = 0
                countdown_start = None
                countdown_value = None
                burst_mode = False
                burst_start_time = None
                burst_photo_count = 0
                
                print(f"\nPlease look {pose}. Capturing {images_per_pose} images...")
                
                # Capture loop for current pose
                while pose_captured < images_per_pose:
                    frame = self.camera.get_frame()
                    if frame is None:
                        time.sleep(0.1)
                        continue
                    
                    # Get head pose
                    pose_result = self.head_pose_detector.get_head_pose_simple(frame)
                    
                    # Current time for various timing operations
                    current_time = time.time()
                    
                    # Check if we're in burst mode (taking multiple photos quickly)
                    if burst_mode:
                        # Check if it's time to take the next photo in burst mode
                        if current_time - burst_start_time >= self.burst_delay and burst_photo_count < images_per_pose - 1:
                            # Capture another photo in burst mode
                            if self._capture_image(frame, user_dir, pose, total_captured):
                                pose_captured += 1
                                total_captured += 1
                                burst_photo_count += 1
                                burst_start_time = current_time
                                
                                # If we've captured all needed photos, exit burst mode
                                if pose_captured >= images_per_pose or burst_photo_count >= images_per_pose - 1:
                                    burst_mode = False
                                    # Give a little breathing room after completing burst mode
                                    time.sleep(1.0)
                        
                        # Continue displaying frames during burst mode
                        guidance_frame = self._draw_guidance(
                            frame, pose, pose_result,
                            pose_captured, images_per_pose,
                            None, None, burst_mode
                        )
                        
                        cv2.imshow("Registration", guidance_frame)
                        
                        # Check for key press
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            logger.info("Registration cancelled by user")
                            return False
                            
                        # Continue to next iteration during burst mode
                        continue
                    
                    # Check if current pose matches required pose (only when not in burst mode)
                    is_correct_pose = pose_result["face_detected"] and pose_result["pose_label"] == pose
                    
                    # Handle pose stability timing
                    if is_correct_pose:
                        if pose_stable_start is None:
                            # Just started the correct pose
                            pose_stable_start = current_time
                            pose_stable_time = 0
                        else:
                            # Continue timing the stable pose
                            pose_stable_time = current_time - pose_stable_start
                    else:
                        # Reset stability timer if pose is lost
                        pose_stable_start = None
                        pose_stable_time = 0
                        countdown_start = None
                        countdown_value = None
                    
                    # Check if pose has been stable for the required time
                    if pose_stable_time >= self.stabilization_time and countdown_start is None:
                        # Start countdown for photo capture
                        countdown_start = current_time
                        countdown_value = self.countdown_time
                    
                    # Update countdown if active
                    if countdown_start is not None:
                        elapsed = current_time - countdown_start
                        countdown_value = max(0, self.countdown_time - int(elapsed))
                        
                        # Take first photo when countdown reaches 0
                        if countdown_value == 0:
                            # Capture the first image
                            if self._capture_image(frame, user_dir, pose, total_captured):
                                pose_captured += 1
                                total_captured += 1
                                
                                # If we need more than 1 photo for this pose, enter burst mode
                                if images_per_pose > 1:
                                    burst_mode = True
                                    burst_start_time = current_time
                                    burst_photo_count = 0
                                else:
                                    # Reset timers if we only need one photo
                                    pose_stable_start = None
                                    pose_stable_time = 0
                                    
                                countdown_start = None
                                countdown_value = None
                    
                    # Draw guidance overlay with stability and countdown info
                    guidance_frame = self._draw_guidance(
                        frame, pose, pose_result,
                        pose_captured, images_per_pose,
                        countdown_value, pose_stable_time,
                        burst_mode
                    )
                    
                    # Show the frame
                    cv2.imshow("Registration", guidance_frame)
                    
                    # Check for key press
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("Registration cancelled by user")
                        return False
            
            print(f"\nRegistration complete! Captured {total_captured} images.")
            print("Please wait for a few seconds while we close the camera...")
            time.sleep(2)
            
            return True
            
        finally:
            self.camera.stop()
            cv2.destroyAllWindows()
            
        return False


def register_user_guided():
    """Command-line interface for guided registration"""
    print("=== Guided User Registration ===")
    
    # Get user name
    name = input("Enter the person's name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return False
    
    # Number of images per pose with improved validation
    num_images = 2  # Default value
    max_images = 5  # Maximum allowed images per pose
    while True:
        try:
            image_input = input(f"How many photos per pose to capture (1-{max_images}, default: 2): ")
            if not image_input:
                break  # Use default value
                
            num_images = int(image_input)
            if num_images <= 0:
                print("Please enter a positive number.")
                continue
            if num_images > max_images:
                print(f"Maximum {max_images} photos per pose allowed.")
                continue
            break  # Valid input, exit the loop
        except ValueError:
            print("Please enter a valid number, not letters or special characters.")
    
    # Create camera and registration handler
    camera = CameraHandler()
    registration = GuidedRegistration(camera)
    
    print("\nStarting registration...")
    print("Instructions:")
    print("- Look in the direction shown on screen")
    print("- Hold each pose steady until photos are captured")
    print("- Press 'q' at any time to cancel")
    
    # Run the guided registration
    success = registration.run_guided_registration(name, num_images)
    
    if success:
        print(f"Registration complete for {name}.")
        
        # Reload encodings if needed
        from .face_encoder import FaceEncoder
        encoder = FaceEncoder()
        encoder.encode_known_faces()
        print("Face recognition model updated with new images.")
        
        return True
    else:
        print("Registration failed or was cancelled.")
        return False


if __name__ == "__main__":
    register_user_guided()