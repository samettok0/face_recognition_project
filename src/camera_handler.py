import os
import time
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

from .config import DEFAULT_CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, OUTPUT_DIR
from .utils import logger

class CameraHandler:
    def __init__(self, camera_index: int = DEFAULT_CAMERA_INDEX):
        """
        Initialize the camera handler
        
        Args:
            camera_index: Index of the camera to use
        """
        self.camera_index = camera_index
        self.cap = None
        self._is_capturing = False
        
    def start(self) -> bool:
        """
        Start the camera
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # Set higher framerate
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            if not self.cap.isOpened():
                logger.error("Failed to open camera")
                return False
                
            self._is_capturing = True
            logger.info(f"Camera started with index {self.camera_index}")
            return True
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False
            
    def stop(self) -> None:
        """
        Stop the camera
        """
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self._is_capturing = False
            logger.info("Camera stopped")
            
    def is_capturing(self) -> bool:
        """
        Check if camera is currently capturing
        
        Returns:
            True if camera is capturing, False otherwise
        """
        return self._is_capturing and self.cap and self.cap.isOpened()
        
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get a single frame from the camera
        
        Returns:
            Frame as numpy array or None if failed
        """
        if not self.is_capturing():
            logger.error("Cannot get frame: Camera not capturing")
            return None
            
        ret, frame = self.cap.read()
        if not ret:
            logger.error("Failed to get frame from camera")
            return None
            
        return frame
        
    def take_picture(self, save_path: Optional[str] = None) -> Optional[Tuple[np.ndarray, str]]:
        """
        Take a picture and optionally save it
        
        Args:
            save_path: Path to save the image, if None generates a filename
            
        Returns:
            Tuple of (frame, saved_path) or None if failed
        """
        frame = self.get_frame()
        if frame is None:
            return None
            
        # Generate filename if not provided
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = str(OUTPUT_DIR / f"capture_{timestamp}.jpg")
            
        # Save the image
        try:
            cv2.imwrite(save_path, frame)
            logger.info(f"Picture saved to {save_path}")
            return frame, save_path
        except Exception as e:
            logger.error(f"Failed to save picture: {e}")
            return frame, ""
            
    def show_preview(self, window_name: str = "Camera Preview", 
                     process_frame=None, show_fps: bool = True) -> None:
        """
        Show camera preview until user presses 'q'
        
        Args:
            window_name: Name of the preview window
            process_frame: Optional function to process frames before display
            show_fps: Whether to show FPS counter
        """
        if not self.start():
            return
            
        try:
            prev_time = time.time()
            fps = 0
            
            while True:
                frame = self.get_frame()
                if frame is None:
                    break
                    
                # Calculate FPS
                current_time = time.time()
                elapsed = current_time - prev_time
                if elapsed > 0:
                    fps = 1.0 / elapsed
                prev_time = current_time
                
                # Process frame if function provided
                if process_frame:
                    frame = process_frame(frame)
                    
                # Show FPS
                if show_fps:
                    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                
                # Display the frame
                cv2.imshow(window_name, frame)
                
                # Exit on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            self.stop()
            cv2.destroyAllWindows() 