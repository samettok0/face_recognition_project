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
        
        # UI settings
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.8
        self.thickness = 2
        self.text_color = (255, 255, 255)
        self.primary_color = (0, 255, 0)  # Green
        self.secondary_color = (0, 165, 255)  # Orange
        
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
        Draw guidance overlay on frame
        
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
        frame_with_overlay = frame.copy()
        
        # Draw translucent background for UI elements
        overlay = frame.copy()
        
        # Top instruction bar
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
        
        # Side status panel
        panel_width = 250
        cv2.rectangle(overlay, (w - panel_width, 80), (w, h), (0, 0, 0), -1)
        
        # Blend the overlay with the original frame
        alpha = 0.7
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame_with_overlay)
        
        # Draw top instruction
        instruction = f"Please look {current_pose}"
        if burst_mode:
            instruction = f"HOLD STILL - Capturing {total_images - images_captured} more photos"
        
        cv2.putText(frame_with_overlay, instruction, (20, 50), 
                   self.font, 1.2, self.text_color, self.thickness)
        
        # Draw progress
        cv2.putText(frame_with_overlay, f"Progress: {images_captured}/{total_images}", 
                   (w - panel_width + 20, 120), self.font, self.font_scale, 
                   self.text_color, self.thickness)
        
        # Draw all poses and their status
        y_offset = 170
        for i, pose in enumerate(self.pose_sequence):
            if pose == current_pose:
                # Current pose - highlight
                cv2.rectangle(frame_with_overlay, 
                            (w - panel_width + 10, y_offset - 25), 
                            (w - 10, y_offset + 10), 
                            self.primary_color, 2)
            
            status = "Current" if pose == current_pose else "Done" if i < self.pose_sequence.index(current_pose) else "Waiting"
            status_color = self.primary_color if status == "Done" else self.secondary_color if status == "Current" else (100, 100, 100)
            
            cv2.putText(frame_with_overlay, f"{pose}", 
                       (w - panel_width + 20, y_offset), 
                       self.font, self.font_scale, self.text_color, self.thickness)
            
            cv2.putText(frame_with_overlay, f"{status}", 
                       (w - panel_width + 150, y_offset), 
                       self.font, self.font_scale - 0.2, status_color, 1)
            
            y_offset += 50
        
        # Draw detected pose information
        if pose_result["face_detected"]:
            detected_pose = pose_result["pose_label"]
            is_correct_pose = detected_pose == current_pose
            
            # Draw stability indicator if pose is correct
            if is_correct_pose and pose_stable_time is not None and not burst_mode:
                # Draw stability progress bar
                bar_width = 200
                bar_height = 15
                bar_left = (w - panel_width + 20)
                bar_top = h - 100
                
                # Full outline
                cv2.rectangle(
                    frame_with_overlay,
                    (bar_left, bar_top),
                    (bar_left + bar_width, bar_top + bar_height),
                    (150, 150, 150),
                    1
                )
                
                # Fill based on stable time (0 to stabilization_time)
                fill_ratio = min(1.0, pose_stable_time / self.stabilization_time)
                fill_width = int(bar_width * fill_ratio)
                
                # Progress fill
                if fill_width > 0:
                    cv2.rectangle(
                        frame_with_overlay,
                        (bar_left, bar_top),
                        (bar_left + fill_width, bar_top + bar_height),
                        (0, 255, 0),
                        -1
                    )
                
                # Draw stability text
                cv2.putText(
                    frame_with_overlay,
                    f"Hold pose steady: {int(pose_stable_time)}/{int(self.stabilization_time)}s",
                    (bar_left, bar_top - 10),
                    self.font,
                    0.6,
                    self.text_color,
                    1
                )
            
            if not burst_mode:
                cv2.putText(frame_with_overlay, f"Detected: {detected_pose}", 
                          (w - panel_width + 20, h - 70), 
                          self.font, self.font_scale, 
                          self.primary_color if is_correct_pose else (0, 0, 255), 
                          self.thickness)
                
                # Draw checkmark or X based on pose match
                status_text = "✓" if is_correct_pose else "✗"
                cv2.putText(frame_with_overlay, status_text, 
                          (w - panel_width + 20, h - 30), 
                          self.font, 1.5, 
                          self.primary_color if is_correct_pose else (0, 0, 255), 
                          self.thickness * 2)
        
        # Draw countdown if active
        if countdown is not None:
            # Draw large countdown number in the center of the screen
            count_text = str(countdown)
            text_size = cv2.getTextSize(count_text, self.font, 6, 6)[0]
            text_x = (w - text_size[0]) // 2
            text_y = (h + text_size[1]) // 2
            
            # Draw semi-transparent background circle
            circle_radius = max(text_size[0], text_size[1]) // 2 + 30
            circle_center = (w // 2, h // 2)
            
            # Draw background circle
            overlay_circle = frame_with_overlay.copy()
            cv2.circle(overlay_circle, circle_center, circle_radius, (0, 0, 0), -1)
            cv2.addWeighted(overlay_circle, 0.7, frame_with_overlay, 0.3, 0, frame_with_overlay)
            
            # Draw countdown number
            cv2.putText(
                frame_with_overlay,
                count_text,
                (text_x, text_y),
                self.font,
                6,
                (0, 255, 255) if countdown > 1 else (0, 255, 0),
                6
            )
            
            # Draw "Get Ready" text
            ready_text = "Get Ready!"
            ready_size = cv2.getTextSize(ready_text, self.font, 1, 2)[0]
            cv2.putText(
                frame_with_overlay,
                ready_text,
                ((w - ready_size[0]) // 2, text_y + 80),
                self.font,
                1,
                (0, 255, 255),
                2
            )
        
        # Draw burst mode indicator if active
        if burst_mode:
            # Draw a special message for burst mode
            burst_text = "BURST MODE ACTIVE - HOLD STILL"
            
            # Draw background for burst text
            burst_size = cv2.getTextSize(burst_text, self.font, 1, 2)[0]
            overlay_burst = frame_with_overlay.copy()
            cv2.rectangle(
                overlay_burst,
                (w // 2 - burst_size[0] // 2 - 20, h - 80),
                (w // 2 + burst_size[0] // 2 + 20, h - 80 + burst_size[1] + 20),
                (0, 0, 200),
                -1
            )
            cv2.addWeighted(overlay_burst, 0.7, frame_with_overlay, 0.3, 0, frame_with_overlay)
            
            # Draw burst text
            cv2.putText(
                frame_with_overlay,
                burst_text,
                (w // 2 - burst_size[0] // 2, h - 80 + burst_size[1] + 5),
                self.font,
                1,
                (255, 255, 255),
                2
            )
        
        return frame_with_overlay
    
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
    
    # Number of images per pose
    try:
        num_images = int(input("How many photos per pose to capture (default: 2): ") or "2")
    except ValueError:
        num_images = 2
    
    # Create camera and registration handler
    camera = CameraHandler()
    registration = GuidedRegistration(camera)
    
    print("\nStarting guided registration process...")
    print("Please follow the on-screen instructions.")
    print("The system will automatically capture photos when your face is in the correct position.")
    print("Hold each pose steady for 2 seconds, then wait for the countdown.")
    print("The first photo will use countdown, then additional photos will be taken in quick succession.")
    print("Press 'q' at any time to cancel.")
    
    # Run the guided registration
    success = registration.run_guided_registration(name, num_images)
    
    if success:
        print(f"Successfully registered {name}.")
        
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