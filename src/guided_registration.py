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
        self.primary_color = (0, 197, 105)  # Green
        self.secondary_color = (30, 144, 255)  # Dodger Blue
        self.accent_color = (255, 195, 0)  # Amber
        self.error_color = (87, 86, 255)  # Red (BGR)
        self.background_color = (33, 33, 33)  # Dark gray
        
        # Icon/emoji codes for visualization
        self.icons = {
            "check": "OK",
            "cross": "X",
            "forward": "FWD",
            "left": "LEFT",
            "right": "RIGHT",
            "up": "UP",
            "down": "DOWN",
            "camera": "CAM",
            "burst": "BURST"
        }
        
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
    
    def _draw_rounded_rect(self, img, rect_start, rect_end, color, thickness=-1, radius=10, alpha=1.0):
        """
        Draw a rounded rectangle on the image
        
        Args:
            img: Image to draw on
            rect_start: Top-left corner (x, y)
            rect_end: Bottom-right corner (x, y)
            color: Rectangle color (BGR)
            thickness: Line thickness (-1 for filled)
            radius: Corner radius
            alpha: Transparency (0-1)
        """
        x1, y1 = rect_start
        x2, y2 = rect_end
        
        if alpha < 1.0:
            overlay = img.copy()
            
            # Draw main rectangle
            cv2.rectangle(overlay, (x1 + radius, y1), (x2 - radius, y1), color, thickness)
            cv2.rectangle(overlay, (x1, y1 + radius), (x2, y2 - radius), color, thickness)
            cv2.rectangle(overlay, (x1 + radius, y2), (x2 - radius, y2), color, thickness)
            
            # Draw the four corner circles
            cv2.circle(overlay, (x1 + radius, y1 + radius), radius, color, thickness)
            cv2.circle(overlay, (x2 - radius, y1 + radius), radius, color, thickness)
            cv2.circle(overlay, (x1 + radius, y2 - radius), radius, color, thickness)
            cv2.circle(overlay, (x2 - radius, y2 - radius), radius, color, thickness)
            
            # Blend with original image
            cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        else:
            # Draw main rectangle
            cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y1), color, thickness)
            cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, thickness)
            cv2.rectangle(img, (x1 + radius, y2), (x2 - radius, y2), color, thickness)
            
            # Draw the four corner circles
            cv2.circle(img, (x1 + radius, y1 + radius), radius, color, thickness)
            cv2.circle(img, (x2 - radius, y1 + radius), radius, color, thickness)
            cv2.circle(img, (x1 + radius, y2 - radius), radius, color, thickness)
            cv2.circle(img, (x2 - radius, y2 - radius), radius, color, thickness)
    
    def _draw_progress_bar(self, img, x, y, w, h, value, max_value, bg_color, fill_color, radius=5, alpha=0.7):
        """
        Draw a stylish progress bar
        
        Args:
            img: Image to draw on
            x, y: Top-left position
            w, h: Width and height
            value: Current value
            max_value: Maximum value
            bg_color: Background color
            fill_color: Fill color
            radius: Corner radius
            alpha: Transparency
        """
        # Calculate fill width
        fill_ratio = min(1.0, value / max_value)
        fill_width = int(w * fill_ratio)
        
        # Draw background
        self._draw_rounded_rect(img, (x, y), (x + w, y + h), bg_color, -1, radius, alpha)
        
        # Draw fill
        if fill_width > 0:
            fill_radius = min(radius, h // 2)
            self._draw_rounded_rect(img, (x, y), (x + fill_width, y + h), fill_color, -1, fill_radius, alpha)
    
    def _get_pose_icon(self, pose: str) -> str:
        """Get icon for pose name"""
        pose_lower = pose.lower()
        return self.icons.get(pose_lower, "FWD")
    
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
        
        # ======= Create main UI elements =======
        
        # Top bar - dark translucent background
        self._draw_rounded_rect(
            frame_with_overlay, 
            (10, 10), 
            (w - 10, 90), 
            self.background_color, 
            -1, 
            15, 
            0.85
        )
        
        # Side panel
        panel_width = 280
        self._draw_rounded_rect(
            frame_with_overlay, 
            (w - panel_width - 10, 100), 
            (w - 10, h - 10), 
            self.background_color, 
            -1, 
            15, 
            0.85
        )
        
        # ======= Top instruction bar content =======
        
        # Set instruction text based on mode
        if burst_mode:
            instruction = f"{self.icons['burst']} CAPTURING SEQUENCE - HOLD STILL"
            instruction_color = self.accent_color
        else:
            instruction = f"{self._get_pose_icon(current_pose)} Please look {current_pose}"
            instruction_color = self.text_color
        
        # Draw instruction text
        cv2.putText(
            frame_with_overlay, 
            instruction, 
            (30, 55), 
            self.font, 
            1.2, 
            instruction_color, 
            self.thickness
        )
        
        # Add photo progress on top bar
        total_photos = len(self.pose_sequence) * total_images
        current_photo = (self.pose_sequence.index(current_pose) * total_images) + images_captured
        progress_text = f"Photos: {current_photo}/{total_photos}"
        
        text_size = cv2.getTextSize(progress_text, self.font, 0.8, 2)[0]
        cv2.putText(
            frame_with_overlay, 
            progress_text, 
            (w - text_size[0] - 30, 55), 
            self.font, 
            0.8, 
            self.text_color, 
            1
        )
        
        # ======= Side panel content =======
        
        # Panel title
        panel_title = "REGISTRATION PROGRESS"
        cv2.putText(
            frame_with_overlay, 
            panel_title, 
            (w - panel_width - 10 + 20, 130), 
            self.font, 
            0.9, 
            self.text_color, 
            2
        )
        
        # Draw divider line
        cv2.line(
            frame_with_overlay,
            (w - panel_width - 10 + 20, 140),
            (w - 30, 140),
            self.text_color,
            1
        )
        
        # Draw all poses and their status
        y_offset = 180
        for i, pose in enumerate(self.pose_sequence):
            # Current pose indicator
            is_current = pose == current_pose
            is_completed = i < self.pose_sequence.index(current_pose)
            is_pending = not (is_current or is_completed)
            
            # Define style based on status
            if is_completed:
                box_color = self.primary_color
                status_text = "COMPLETED"
                status_color = self.primary_color
            elif is_current:
                box_color = self.secondary_color
                status_text = "CURRENT"
                status_color = self.secondary_color
            else:
                box_color = (80, 80, 80)  # Gray
                status_text = "PENDING"
                status_color = (150, 150, 150)  # Light gray
            
            # Draw rounded box for pose name with icon
            box_width = 240
            box_height = 40
            box_x = w - panel_width - 10 + 20
            box_y = y_offset - 25
            
            self._draw_rounded_rect(
                frame_with_overlay,
                (box_x, box_y),
                (box_x + box_width, box_y + box_height),
                box_color if is_current else (60, 60, 60),
                -1,
                10,
                0.7 if is_current else 0.4
            )
            
            # Draw pose name and icon
            pose_icon = self._get_pose_icon(pose)
            cv2.putText(
                frame_with_overlay, 
                f"{pose_icon} {pose}", 
                (box_x + 10, box_y + 28), 
                self.font, 
                0.8, 
                self.text_color if is_current else (200, 200, 200), 
                2 if is_current else 1
            )
            
            # Draw progress for current pose
            if is_current:
                progress_width = 200
                progress_height = 6
                progress_x = box_x + 20
                progress_y = box_y + box_height + 10
                
                progress_value = images_captured
                
                self._draw_progress_bar(
                    frame_with_overlay,
                    progress_x,
                    progress_y,
                    progress_width,
                    progress_height,
                    progress_value,
                    total_images,
                    (60, 60, 60),
                    self.secondary_color,
                    3,
                    0.8
                )
                
                # Progress text
                cv2.putText(
                    frame_with_overlay,
                    f"{images_captured}/{total_images}",
                    (progress_x + progress_width + 10, progress_y + 5),
                    self.font,
                    0.6,
                    self.text_color,
                    1
                )
                
                # Add more vertical space for current pose
                y_offset += 50
            
            y_offset += 50
        
        # ======= Status information =======
        
        status_area_y = h - 120
        
        # Draw detected pose information
        if pose_result["face_detected"]:
            detected_pose = pose_result["pose_label"]
            is_correct_pose = detected_pose == current_pose
            
            # Draw stability indicator if pose is correct and not in burst mode
            if is_correct_pose and pose_stable_time is not None and not burst_mode:
                # Draw stability heading
                cv2.putText(
                    frame_with_overlay,
                    "HOLD STEADY",
                    (30, status_area_y),
                    self.font,
                    0.8,
                    self.accent_color,
                    2
                )
                
                # Draw progress bar for stability
                bar_width = 200
                bar_height = 8
                bar_x = 30
                bar_y = status_area_y + 15
                
                self._draw_progress_bar(
                    frame_with_overlay,
                    bar_x,
                    bar_y,
                    bar_width,
                    bar_height,
                    pose_stable_time,
                    self.stabilization_time,
                    (60, 60, 60),
                    self.primary_color,
                    4,
                    0.8
                )
                
                # Draw stability text
                cv2.putText(
                    frame_with_overlay,
                    f"{int(pose_stable_time)}/{int(self.stabilization_time)}s",
                    (bar_x + bar_width + 10, bar_y + 8),
                    self.font,
                    0.7,
                    self.text_color,
                    1
                )
                
            # Show detected pose information (only when not in burst mode)
            if not burst_mode:
                # Detection status box
                status_box_x = 30
                status_box_y = status_area_y + 40
                status_box_width = 200
                status_box_height = 40
                
                self._draw_rounded_rect(
                    frame_with_overlay,
                    (status_box_x, status_box_y),
                    (status_box_x + status_box_width, status_box_y + status_box_height),
                    self.primary_color if is_correct_pose else self.error_color,
                    -1,
                    10,
                    0.7
                )
                
                # Draw detected pose text
                status_icon = self.icons["check"] if is_correct_pose else self.icons["cross"]
                cv2.putText(
                    frame_with_overlay, 
                    f"{status_icon} {detected_pose} POSE", 
                    (status_box_x + 15, status_box_y + 28), 
                    self.font, 
                    0.8, 
                    self.text_color, 
                    2
                )
        
        # ======= Draw countdown if active =======
        
        if countdown is not None:
            # Draw large countdown circle in the center
            circle_center = (w // 2, h // 2)
            circle_radius = 80
            
            # Draw a semi-transparent dark background circle
            overlay_circle = frame_with_overlay.copy()
            cv2.circle(overlay_circle, circle_center, circle_radius + 20, (0, 0, 0), -1)
            cv2.addWeighted(overlay_circle, 0.7, frame_with_overlay, 0.3, 0, frame_with_overlay)
            
            # Draw countdown border
            cv2.circle(
                frame_with_overlay, 
                circle_center, 
                circle_radius, 
                self.accent_color if countdown > 1 else self.primary_color, 
                8
            )
            
            # Draw countdown number
            count_text = str(countdown)
            text_size = cv2.getTextSize(count_text, self.font, 5, 5)[0]
            text_x = circle_center[0] - text_size[0] // 2
            text_y = circle_center[1] + text_size[1] // 2
            
            cv2.putText(
                frame_with_overlay,
                count_text,
                (text_x, text_y),
                self.font,
                5,
                self.accent_color if countdown > 1 else self.primary_color,
                8
            )
            
            # "GET READY" text
            ready_text = "GET READY!"
            ready_size = cv2.getTextSize(ready_text, self.font, 1, 2)[0]
            ready_x = circle_center[0] - ready_size[0] // 2
            ready_y = circle_center[1] + circle_radius + 40
            
            cv2.putText(
                frame_with_overlay,
                ready_text,
                (ready_x, ready_y),
                self.font,
                1,
                self.text_color,
                2
            )
        
        # ======= Draw burst mode indicator if active =======
        
        elif burst_mode:
            # Draw "BURST MODE" indicator at the bottom
            burst_text = f"{self.icons['camera']} BURST MODE ACTIVE • HOLD STILL"
            
            # Get text size for centering
            text_size = cv2.getTextSize(burst_text, self.font, 1, 2)[0]
            text_x = (w - text_size[0]) // 2
            text_y = h - 40
            
            # Draw background pill
            self._draw_rounded_rect(
                frame_with_overlay,
                (text_x - 20, text_y - 30),
                (text_x + text_size[0] + 20, text_y + 10),
                (0, 0, 200),  # Red background
                -1,
                20,
                0.8
            )
            
            # Draw text
            cv2.putText(
                frame_with_overlay,
                burst_text,
                (text_x, text_y),
                self.font,
                1,
                self.text_color,
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
    
    # Number of images per pose with improved validation
    num_images = 2  # Default value
    while True:
        try:
            image_input = input("How many photos per pose to capture (default: 2): ")
            if not image_input:
                break  # Use default value
                
            num_images = int(image_input)
            if num_images <= 0:
                print("Please enter a positive number.")
                continue
            break  # Valid input, exit the loop
        except ValueError:
            print("Please enter a valid number, not letters or special characters.")
    
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