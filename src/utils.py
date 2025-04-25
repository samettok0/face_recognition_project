import logging
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, List, Any, Optional, Dict, Union
from .config import BOUNDING_BOX_COLOR, TEXT_COLOR, LOG_FILE, LOG_FORMAT
import time

# Configure logging once at module level
# Note: For multi-process applications, this should be guarded with 
# if __name__ == "__main__": to avoid duplicate handlers
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=LOG_FORMAT
)

# Create a global logger instance
logger = logging.getLogger("face_recognition")

# Color conversion helpers
def color_name_to_bgr(color_name: str) -> Tuple[int, int, int]:
    """
    Convert color name to BGR tuple for OpenCV
    
    Args:
        color_name: String name of the color (e.g., "blue", "white")
        
    Returns:
        BGR tuple for OpenCV functions
    """
    color_map = {
        "blue": (255, 0, 0),     # BGR format
        "green": (0, 255, 0),
        "red": (0, 0, 255),
        "white": (255, 255, 255),
        "black": (0, 0, 0),
    }
    return color_map.get(color_name.lower(), (255, 255, 255))  # Default to white

def draw_bounding_box(draw: ImageDraw, 
                     bounding_box: Tuple[int, int, int, int],
                     name: str,
                     box_color: str = BOUNDING_BOX_COLOR,
                     text_color: str = TEXT_COLOR) -> None:
    """
    Draw a bounding box with a name on a PIL Image
    
    Args:
        draw: PIL ImageDraw object
        bounding_box: Tuple of (top, right, bottom, left) coordinates
        name: Name to display
        box_color: Color to use for the bounding box
        text_color: Color to use for the text
    """
    top, right, bottom, left = bounding_box
    
    # Draw the box
    draw.rectangle([(left, top), (right, bottom)], outline=box_color, width=2)
    
    # Get text size - works with all PIL versions
    try:
        # For newer PIL versions
        font = draw.getfont()
        text_width, text_height = font.getsize(name)
    except (AttributeError, TypeError):
        try:
            # For PIL 9.2.0+
            font = ImageFont.load_default()
            left, top, right, bottom = font.getbbox(name)
            text_width, text_height = right - left, bottom - top
        except:
            # Fallback for older PIL versions
            text_width, text_height = draw.textsize(name)
    
    text_left = left
    text_bottom = bottom + text_height
    
    # Draw a filled rectangle for the text background
    draw.rectangle([(text_left, bottom), (text_left + text_width, text_bottom)], 
                   fill=box_color)
    
    # Draw the text
    draw.text((text_left, bottom), name, fill=text_color)

def draw_recognition_feedback_on_frame(frame: np.ndarray, 
                                      results: List[Tuple[Any, ...]], 
                                      include_confidence: bool = True) -> np.ndarray:
    """
    Draws face recognition feedback directly on a CV2 frame
    
    Args:
        frame: OpenCV frame/image as numpy array
        results: Recognition results (face locations, names, and optionally confidence scores)
        include_confidence: Whether to include confidence score in the label
    
    Returns:
        Frame with annotations
    """
    # Create a copy to avoid modifying the original
    annotated_frame = frame.copy()
    
    for result in results:
        # Extract data based on result format
        if len(result) == 2:  # (bounding_box, name) format
            (top, right, bottom, left), name = result
            confidence = None
        else:  # (bounding_box, name, confidence) format 
            (top, right, bottom, left), name, confidence = result
            
        # Choose color based on recognition status
        if name == "Unknown":
            # Red color for unknown faces (BGR format)
            main_color = (50, 50, 220)  # Darker red
            text_bg_color = (80, 80, 255)  # Brighter red
        elif name == "Fake":
            # Purple color for fake/spoofed faces (BGR format)
            main_color = (220, 50, 220)  # Darker purple
            text_bg_color = (255, 80, 255)  # Brighter purple
        else:
            # Green color for known faces
            main_color = (50, 180, 50)  # Darker green
            text_bg_color = (20, 220, 20)  # Brighter green
            
        # Calculate box dimensions
        box_width = right - left
        box_height = bottom - top
        
        # Draw rectangle with thickness based on face size (more proportional)
        thickness = max(1, min(3, int(box_width / 100)))
        
        # Draw main rectangle (slightly rounded corners using multiple rectangles)
        cv2.rectangle(annotated_frame, (left, top), (right, bottom), main_color, thickness)
        
        # Add corner accents (small perpendicular lines at corners)
        corner_length = max(10, min(20, int(box_width / 15)))
        
        # Top left corner
        cv2.line(annotated_frame, (left, top), (left + corner_length, top), main_color, thickness + 1)
        cv2.line(annotated_frame, (left, top), (left, top + corner_length), main_color, thickness + 1)
        
        # Top right corner
        cv2.line(annotated_frame, (right, top), (right - corner_length, top), main_color, thickness + 1)
        cv2.line(annotated_frame, (right, top), (right, top + corner_length), main_color, thickness + 1)
        
        # Bottom left corner
        cv2.line(annotated_frame, (left, bottom), (left + corner_length, bottom), main_color, thickness + 1)
        cv2.line(annotated_frame, (left, bottom), (left, bottom - corner_length), main_color, thickness + 1)
        
        # Bottom right corner
        cv2.line(annotated_frame, (right, bottom), (right - corner_length, bottom), main_color, thickness + 1)
        cv2.line(annotated_frame, (right, bottom), (right, bottom - corner_length), main_color, thickness + 1)
        
        # Prepare label
        if include_confidence and confidence is not None:
            label = f"{name} ({confidence:.2f})"
        else:
            label = name
            
        # Calculate text size for better positioning
        (text_width, text_height), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1
        )
        
        # Draw background for text - bottom aligned, slightly bigger than text
        text_bg_padding = 5
        text_left = left
        text_bottom = bottom + text_height + 2 * text_bg_padding  # Position below face

        # Semi-transparent background for text (helps with readability)
        overlay = annotated_frame.copy()
        cv2.rectangle(
            overlay, 
            (text_left, bottom), 
            (text_left + text_width + 2 * text_bg_padding, text_bottom), 
            text_bg_color, 
            -1  # Filled rectangle
        )
        
        # Apply the overlay with transparency
        alpha = 0.7  # Transparency factor
        cv2.addWeighted(overlay, alpha, annotated_frame, 1 - alpha, 0, annotated_frame)
        
        # Show name with a nicer font
        cv2.putText(
            annotated_frame, 
            label, 
            (text_left + text_bg_padding, text_bottom - text_bg_padding), 
            cv2.FONT_HERSHEY_DUPLEX, 
            0.6, 
            (255, 255, 255), 
            1, 
            cv2.LINE_AA  # Anti-aliased text for smoother appearance
        )
    
    return annotated_frame

def ensure_dir_exists(directory: str) -> None:
    """
    Ensures a directory exists, creating it if necessary
    
    Args:
        directory: Path to the directory
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        
def get_logger(name: str = None) -> logging.Logger:
    """
    Gets a logger with the given name. If no name is provided, returns the global logger.
    
    Args:
        name: Optional name for the logger
        
    Returns:
        Configured logger instance
    """
    if name:
        # Create a child logger that inherits settings from the root logger
        return logging.getLogger(f"face_recognition.{name}")
    return logger

def create_flash_effect(frame: np.ndarray, flash_duration: float = 0.1) -> None:
    """
    Create a flash effect when taking a photo
    
    Args:
        frame: Current frame to display flash on
        flash_duration: Duration of flash effect in seconds
    """
    h, w, _ = frame.shape
    # Create a white overlay
    white_overlay = np.ones((h, w, 3), dtype=np.uint8) * 255
    
    # Create a gradually fading flash effect
    # Limit to approximately 10 frames total to maintain performance
    start_time = time.time()
    max_frames = 10
    frame_time = flash_duration / max_frames
    
    for i in range(max_frames):
        # Calculate elapsed percentage
        elapsed = i / max_frames
        
        # Alpha starts at 0.9 and decreases to 0
        alpha = max(0, 0.9 * (1 - elapsed))
        
        # Create blended frame
        blended = cv2.addWeighted(frame, 1 - alpha, white_overlay, alpha, 0)
        
        # Display the flash effect
        cv2.imshow("Registration", blended)
        cv2.waitKey(1)
        
        # Control frame rate by sleeping until next frame time
        frame_end_time = start_time + (i + 1) * frame_time
        sleep_time = max(0, frame_end_time - time.time())
        if sleep_time > 0:
            time.sleep(sleep_time)