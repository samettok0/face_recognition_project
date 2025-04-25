import os
import time
import cv2
import numpy as np
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Callable

from .config import DEFAULT_CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, OUTPUT_DIR
from .utils import logger

class CameraHandler:
    def __init__(self, 
                 camera_index: int = DEFAULT_CAMERA_INDEX,
                 width: int = FRAME_WIDTH,
                 height: int = FRAME_HEIGHT,
                 fps: int = 30,
                 **kwargs):
        """
        Initialize the camera handler
        
        Args:
            camera_index: Index of the camera to use
            width: Camera resolution width
            height: Camera resolution height
            fps: Target frames per second
            **kwargs: Additional camera parameters
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.kwargs = kwargs
        self.cap = None
        self._is_capturing = False
        self._consecutive_failures = 0
        self._max_failures = kwargs.get('max_failures', 5)
        
    def _get_backend(self) -> int:
        """
        Select appropriate backend based on platform
        
        Returns:
            OpenCV backend API identifier
        """
        system = platform.system().lower()
        
        if system == "linux":
            return cv2.CAP_V4L2
        elif system == "darwin":
            return cv2.CAP_AVFOUNDATION
        elif system == "windows":
            return cv2.CAP_DSHOW
        else:
            # Default to auto-detect
            return cv2.CAP_ANY
            
    def start(self) -> bool:
        """
        Start the camera
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try with specified backend first
            backend = self._get_backend()
            
            try:
                self.cap = cv2.VideoCapture(self.camera_index, backend)
                if not self.cap.isOpened():
                    # Fallback to default backend if specified one fails
                    logger.warning(f"Failed to open camera with specific backend, trying default")
                    self.cap = cv2.VideoCapture(self.camera_index)
            except Exception as e:
                logger.warning(f"Backend-specific initialization failed: {e}, trying default")
                self.cap = cv2.VideoCapture(self.camera_index)
            
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # Set higher framerate
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Apply any additional parameters from kwargs
            for key, value in self.kwargs.items():
                if key.startswith('cv_'):
                    prop_name = key[3:]  # Remove 'cv_' prefix
                    if hasattr(cv2, prop_name):
                        prop_id = getattr(cv2, prop_name)
                        self.cap.set(prop_id, value)
            
            if not self.cap.isOpened():
                logger.error("Failed to open camera")
                return False
                
            # Reset failure counter on successful start
            self._consecutive_failures = 0
            self._is_capturing = True
            logger.info(f"Camera started with index {self.camera_index}, resolution {self.width}x{self.height}")
            
            # Get actual resolution (might be different from requested)
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            logger.info(f"Actual camera settings: {actual_width}x{actual_height} @ {actual_fps} FPS")
            
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
    
    def _try_recover_camera(self) -> bool:
        """
        Try to recover camera after failures
        
        Returns:
            True if recovery was successful, False otherwise
        """
        logger.warning(f"Attempting to recover camera after {self._consecutive_failures} failures")
        self.stop()
        time.sleep(1)  # Give the camera some time to reset
        return self.start()
        
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
            self._consecutive_failures += 1
            logger.warning(f"Failed to get frame ({self._consecutive_failures}/{self._max_failures})")
            
            # Try to recover camera if too many consecutive failures
            if self._consecutive_failures >= self._max_failures:
                if not self._try_recover_camera():
                    logger.error("Camera recovery failed")
                    return None
            return None
            
        # Reset failure counter on successful frame read
        self._consecutive_failures = 0
        return frame
    
    def set_exposure(self, value: int) -> bool:
        """
        Set camera exposure. Negative values enable auto-exposure.
        
        Args:
            value: Exposure value (-1 for auto, or specific value)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_capturing():
            return False
            
        # First disable auto-exposure if setting manual value
        if value >= 0:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)  # 0 = manual mode
        else:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 1 = auto mode
            return True
            
        # Then set the exposure value
        return self.cap.set(cv2.CAP_PROP_EXPOSURE, value)
    
    def set_gain(self, value: float) -> bool:
        """
        Set camera gain (brightness amplification)
        
        Args:
            value: Gain value (higher values = brighter image)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_capturing():
            return False
            
        return self.cap.set(cv2.CAP_PROP_GAIN, value)
    
    def set_auto_focus(self, enable: bool) -> bool:
        """
        Enable or disable camera auto-focus
        
        Args:
            enable: True to enable auto-focus, False to disable
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_capturing():
            return False
            
        return self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1 if enable else 0)
    
    def set_focus(self, value: int) -> bool:
        """
        Set manual focus value (requires auto-focus to be disabled first)
        
        Args:
            value: Focus value
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_capturing():
            return False
            
        # Disable auto-focus first
        self.set_auto_focus(False)
        return self.cap.set(cv2.CAP_PROP_FOCUS, value)
        
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
                     process_frame: Optional[Callable[[np.ndarray], np.ndarray]] = None, 
                     show_fps: bool = True) -> None:
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
                    # Slight delay to prevent tight loop if camera is failing
                    time.sleep(0.1)
                    continue
                    
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