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
    try:
        # Ensure frame is valid
        if frame is None or frame.size == 0:
            logger.error("Cannot draw on empty frame")
            return np.zeros((100, 100, 3), dtype=np.uint8)  # Return a blank frame
        
        # Create a copy to avoid modifying the original
        try:
            annotated_frame = frame.copy()
        except Exception as e:
            logger.error(f"Could not copy frame: {e}")
            # Try to create a compatible copy
            if len(frame.shape) == 2:  # Grayscale
                annotated_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            else:
                # Last resort, create a new array with same dimensions
                annotated_frame = np.zeros_like(frame)
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    # Try to copy content
                    np.copyto(annotated_frame, frame, casting='unsafe')
                else:
                    logger.error(f"Incompatible frame format: {frame.shape}")
                    return frame  # Return original as fallback
        
        # If we have no results, return early
        if not results:
            # Add text showing no faces detected
            cv2.putText(annotated_frame, "No faces detected", (10, 30),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return annotated_frame
        
        for result in results:
            # Extract data based on result format
            if len(result) == 2:  # (bounding_box, name) format
                (top, right, bottom, left), name = result
                confidence = None
            else:  # (bounding_box, name, confidence) format 
                (top, right, bottom, left), name, confidence = result
                
            # Ensure coordinates are valid integers
            try:
                top = max(0, int(top))
                right = max(0, int(right))
                bottom = max(0, int(bottom))
                left = max(0, int(left))
                
                # Ensure coordinates are within image bounds
                height, width = annotated_frame.shape[:2]
                right = min(right, width-1)
                bottom = min(bottom, height-1)
                
                # Skip if invalid box dimensions
                if right <= left or bottom <= top:
                    continue
            except Exception as e:
                logger.error(f"Invalid bounding box coordinates: {e}")
                continue
                
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

            # Make sure text stays within image bounds
            text_bottom = min(text_bottom, annotated_frame.shape[0] - 1)

            # Semi-transparent background for text (helps with readability)
            overlay = annotated_frame.copy()
            cv2.rectangle(
                overlay, 
                (text_left, bottom), 
                (min(text_left + text_width + 2 * text_bg_padding, annotated_frame.shape[1] - 1), text_bottom), 
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
    except Exception as e:
        logger.error(f"Error drawing recognition feedback: {e}")
        # Return original frame if there was an error
        return frame

def draw_enhanced_anti_spoofing_feedback(frame: np.ndarray, 
                                        results: List[Tuple[Any, ...]], 
                                        is_live: bool = True,
                                        include_confidence: bool = True) -> np.ndarray:
    """
    Draws enhanced anti-spoofing feedback with improved visual indicators
    
    Args:
        frame: OpenCV frame/image as numpy array
        results: Recognition results (face locations, names, and optionally confidence scores)
        is_live: Whether the detected face is live (not spoofed)
        include_confidence: Whether to include confidence score in the label
    
    Returns:
        Frame with enhanced annotations
    """
    try:
        # Ensure frame is valid
        if frame is None or frame.size == 0:
            logger.error("Cannot draw on empty frame")
            return np.zeros((100, 100, 3), dtype=np.uint8)  # Return a blank frame
        
        # Create a copy to avoid modifying the original
        try:
            annotated_frame = frame.copy()
        except Exception as e:
            logger.error(f"Could not copy frame: {e}")
            # Try to create a compatible copy
            if len(frame.shape) == 2:  # Grayscale
                annotated_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            else:
                # Last resort, create a new array with same dimensions
                annotated_frame = np.zeros_like(frame)
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    # Try to copy content
                    np.copyto(annotated_frame, frame, casting='unsafe')
                else:
                    logger.error(f"Incompatible frame format: {frame.shape}")
                    return frame  # Return original as fallback
        
        # If we have no results, show "NO FACES DETECTED"
        if not results:
            # Add text showing no faces detected in red
            cv2.putText(annotated_frame, "NO FACES DETECTED", (10, 30),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            return annotated_frame
        
        # Show "FACE DETECTED" when faces are found
        cv2.putText(annotated_frame, "FACE DETECTED", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        for result in results:
            # Extract data based on result format
            if len(result) == 2:  # (bounding_box, name) format
                (top, right, bottom, left), name = result
                confidence = None
            else:  # (bounding_box, name, confidence) format 
                (top, right, bottom, left), name, confidence = result
                
            # Ensure coordinates are valid integers
            try:
                top = max(0, int(top))
                right = max(0, int(right))
                bottom = max(0, int(bottom))
                left = max(0, int(left))
                
                # Ensure coordinates are within image bounds
                height, width = annotated_frame.shape[:2]
                right = min(right, width-1)
                bottom = min(bottom, height-1)
                
                # Skip if invalid box dimensions
                if right <= left or bottom <= top:
                    continue
            except Exception as e:
                logger.error(f"Invalid bounding box coordinates: {e}")
                continue
                
            # Determine if this is a known person (not "Unknown")
            is_known_person = name != "Unknown"
            
            # Choose color based on recognition status and liveness
            if is_known_person:
                if is_live:
                    # Known person, live - green colors
                    main_color = (50, 180, 50)  # Darker green
                    text_bg_color = (20, 220, 20)  # Brighter green
                else:
                    # Known person, spoofed - green for name, red for SPOOFED
                    main_color = (50, 180, 50)  # Darker green
                    text_bg_color = (20, 220, 20)  # Brighter green
            else:
                # Unknown person - red colors regardless of liveness
                main_color = (50, 50, 220)  # Darker red
                text_bg_color = (80, 80, 255)  # Brighter red
                
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
            
            # Prepare the enhanced label based on the requirements
            if is_known_person:
                if is_live:
                    # Known person, live
                    label = f"Match: {name}, LIVE"
                else:
                    # Known person, spoofed
                    label = f"Match: {name}, SPOOFED"
            else:
                if is_live:
                    # Unknown person, live
                    label = f"Match: Unknown Face, LIVE"
                else:
                    # Unknown person, spoofed
                    label = f"Match: Unknown Face, SPOOFED"
                
            # Calculate text size for better positioning
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1
            )
            
            # Draw background for text - bottom aligned, slightly bigger than text
            text_bg_padding = 5
            text_left = left
            text_bottom = bottom + text_height + 2 * text_bg_padding  # Position below face

            # Make sure text stays within image bounds
            text_bottom = min(text_bottom, annotated_frame.shape[0] - 1)

            # Semi-transparent background for text (helps with readability)
            overlay = annotated_frame.copy()
            cv2.rectangle(
                overlay, 
                (text_left, bottom), 
                (min(text_left + text_width + 2 * text_bg_padding, annotated_frame.shape[1] - 1), text_bottom), 
                text_bg_color, 
                -1  # Filled rectangle
            )
            
            # Apply the overlay with transparency
            alpha = 0.7  # Transparency factor
            cv2.addWeighted(overlay, alpha, annotated_frame, 1 - alpha, 0, annotated_frame)
            
            # Draw the text with different colors for different parts
            # Split the label into parts for different coloring
            if is_known_person:
                if is_live:
                    # "Match: {name}, LIVE" - all green
                    cv2.putText(
                        annotated_frame, 
                        label, 
                        (text_left + text_bg_padding, text_bottom - text_bg_padding), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.6, 
                        (255, 255, 255),  # White text on green background
                        1, 
                        cv2.LINE_AA
                    )
                else:
                    # "Match: {name}, SPOOFED" - name in green, SPOOFED in red
                    # Draw "Match: {name}," part in white (on green background)
                    match_part = f"Match: {name}, "
                    cv2.putText(
                        annotated_frame, 
                        match_part, 
                        (text_left + text_bg_padding, text_bottom - text_bg_padding), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.6, 
                        (255, 255, 255),  # White text
                        1, 
                        cv2.LINE_AA
                    )
                    
                    # Calculate position for "SPOOFED" part
                    (match_width, _), _ = cv2.getTextSize(
                        match_part, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1
                    )
                    spoofed_x = text_left + text_bg_padding + match_width
                    
                    # Draw "SPOOFED" in black for better contrast
                    cv2.putText(
                        annotated_frame, 
                        "SPOOFED", 
                        (spoofed_x, text_bottom - text_bg_padding), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.6, 
                        (0, 0, 0),  # Black text for better contrast
                        1, 
                        cv2.LINE_AA
                    )
            else:
                if is_live:
                    # "Match: Unknown Face, LIVE" - Unknown Face in black, LIVE in green
                    # Draw "Match: " part in white
                    match_part = "Match: "
                    cv2.putText(
                        annotated_frame, 
                        match_part, 
                        (text_left + text_bg_padding, text_bottom - text_bg_padding), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.6, 
                        (255, 255, 255),  # White text
                        1, 
                        cv2.LINE_AA
                    )
                    
                    # Calculate position for "Unknown Face" part
                    (match_width, _), _ = cv2.getTextSize(
                        match_part, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1
                    )
                    unknown_x = text_left + text_bg_padding + match_width
                    
                    # Draw "Unknown Face" in black for better contrast
                    cv2.putText(
                        annotated_frame, 
                        "Unknown Face", 
                        (unknown_x, text_bottom - text_bg_padding), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.6, 
                        (0, 0, 0),  # Black text for better contrast
                        1, 
                        cv2.LINE_AA
                    )
                    
                    # Calculate position for ", LIVE" part
                    (unknown_width, _), _ = cv2.getTextSize(
                        "Unknown Face", cv2.FONT_HERSHEY_DUPLEX, 0.6, 1
                    )
                    live_x = unknown_x + unknown_width
                    
                    # Draw ", LIVE" in green
                    cv2.putText(
                        annotated_frame, 
                        ", LIVE", 
                        (live_x, text_bottom - text_bg_padding), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.6, 
                        (0, 255, 0),  # Green text
                        1, 
                        cv2.LINE_AA
                    )
                else:
                    # "Match: Unknown Face, SPOOFED" - Unknown Face in black, SPOOFED in black
                    # Draw "Match: " part in white
                    match_part = "Match: "
                    cv2.putText(
                        annotated_frame, 
                        match_part, 
                        (text_left + text_bg_padding, text_bottom - text_bg_padding), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.6, 
                        (255, 255, 255),  # White text
                        1, 
                        cv2.LINE_AA
                    )
                    
                    # Calculate position for "Unknown Face" part
                    (match_width, _), _ = cv2.getTextSize(
                        match_part, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1
                    )
                    unknown_x = text_left + text_bg_padding + match_width
                    
                    # Draw "Unknown Face" in black for better contrast
                    cv2.putText(
                        annotated_frame, 
                        "Unknown Face", 
                        (unknown_x, text_bottom - text_bg_padding), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.6, 
                        (0, 0, 0),  # Black text for better contrast
                        1, 
                        cv2.LINE_AA
                    )
                    
                    # Calculate position for ", SPOOFED" part
                    (unknown_width, _), _ = cv2.getTextSize(
                        "Unknown Face", cv2.FONT_HERSHEY_DUPLEX, 0.6, 1
                    )
                    spoofed_x = unknown_x + unknown_width
                    
                    # Draw ", SPOOFED" in black for better contrast
                    cv2.putText(
                        annotated_frame, 
                        ", SPOOFED", 
                        (spoofed_x, text_bottom - text_bg_padding), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.6, 
                        (0, 0, 0),  # Black text for better contrast
                        1, 
                        cv2.LINE_AA
                    )
        
        return annotated_frame
    except Exception as e:
        logger.error(f"Error drawing enhanced anti-spoofing feedback: {e}")
        # Return original frame if there was an error
        return frame

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

def resize_for_deepface(frame: np.ndarray, width: int = 320, height: int = 240) -> np.ndarray:
    """Resize frame to smaller resolution for faster DeepFace processing on Raspberry Pi."""
    return cv2.resize(frame, (width, height))

def draw_authentication_status(frame: np.ndarray, 
                              status: str, 
                              message: str = "",
                              is_success: bool = False,
                              duration: float = 3.0) -> np.ndarray:
    """
    Draw authentication status messages on the frame
    
    Args:
        frame: OpenCV frame/image as numpy array
        status: Status text (e.g., "AUTHENTICATION SUCCESSFUL", "AUTHENTICATION FAILED")
        message: Additional message text
        is_success: Whether this is a success or failure message
        duration: How long to show the message (for future use)
    
    Returns:
        Frame with status message overlay
    """
    try:
        # Ensure frame is valid
        if frame is None or frame.size == 0:
            logger.error("Cannot draw status on empty frame")
            return np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Create a copy to avoid modifying the original
        annotated_frame = frame.copy()
        
        # Get frame dimensions
        height, width = annotated_frame.shape[:2]
        
        # Choose colors based on success/failure
        if is_success:
            # Success colors - green theme
            status_color = (0, 255, 0)  # Bright green
            bg_color = (0, 100, 0)      # Dark green
            text_color = (255, 255, 255)  # White text
        else:
            # Failure colors - red theme
            status_color = (0, 0, 255)  # Bright red
            bg_color = (0, 0, 100)      # Dark red
            text_color = (255, 255, 255)  # White text
        
        # Create a semi-transparent overlay for the entire frame
        overlay = annotated_frame.copy()
        
        # Add a dark overlay to make text more readable
        cv2.rectangle(overlay, (0, 0), (width, height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.3, annotated_frame, 0.7, 0, annotated_frame)
        
        # Calculate text positions
        status_font = cv2.FONT_HERSHEY_DUPLEX
        message_font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Get text sizes
        (status_width, status_height), _ = cv2.getTextSize(status, status_font, 1.2, 3)
        message_width, message_height = 0, 0
        if message:
            (message_width, message_height), _ = cv2.getTextSize(message, message_font, 0.8, 2)
        
        # Calculate total height needed
        total_height = status_height + 20  # 20px spacing
        if message:
            total_height += message_height + 10
        
        # Calculate background rectangle
        bg_padding = 30
        bg_width = max(status_width, message_width) + 2 * bg_padding
        bg_height = total_height + 2 * bg_padding
        
        # Center the background
        bg_x = (width - bg_width) // 2
        bg_y = (height - bg_height) // 2
        
        # Draw background rectangle with rounded corners effect
        cv2.rectangle(annotated_frame, 
                     (bg_x, bg_y), 
                     (bg_x + bg_width, bg_y + bg_height), 
                     bg_color, -1)
        
        # Add border
        cv2.rectangle(annotated_frame, 
                     (bg_x, bg_y), 
                     (bg_x + bg_width, bg_y + bg_height), 
                     status_color, 3)
        
        # Draw status text
        status_x = (width - status_width) // 2
        status_y = bg_y + bg_padding + status_height
        
        # Draw text with outline for better visibility
        cv2.putText(annotated_frame, status, (status_x, status_y), 
                   status_font, 1.2, (0, 0, 0), 4, cv2.LINE_AA)  # Black outline
        cv2.putText(annotated_frame, status, (status_x, status_y), 
                   status_font, 1.2, status_color, 2, cv2.LINE_AA)  # Colored text
        
        # Draw message text if provided
        if message:
            message_x = (width - message_width) // 2
            message_y = status_y + 20 + message_height  # 20px below status
            
            # Draw text with outline for better visibility
            cv2.putText(annotated_frame, message, (message_x, message_y), 
                       message_font, 0.8, (0, 0, 0), 3, cv2.LINE_AA)  # Black outline
            cv2.putText(annotated_frame, message, (message_x, message_y), 
                       message_font, 0.8, text_color, 1, cv2.LINE_AA)  # White text
        
        return annotated_frame
        
    except Exception as e:
        logger.error(f"Error drawing authentication status: {e}")
        return frame

def validate_face_size_and_distance(frame: np.ndarray, bbox: Tuple[int, int, int, int], 
                                   min_face_size: int = 100, max_face_size: int = 400) -> bool:
    """
    Validate that the face is at an appropriate distance from the camera
    
    Args:
        frame: OpenCV frame/image as numpy array
        bbox: Face bounding box (top, right, bottom, left)
        min_face_size: Minimum face size in pixels (too far = spoofing attempt)
        max_face_size: Maximum face size in pixels (too close = potential bypass)
    
    Returns:
        True if face size is within acceptable range, False otherwise
    """
    try:
        top, right, bottom, left = bbox
        face_width = right - left
        face_height = bottom - top
        
        # Use the larger dimension as the face size
        face_size = max(face_width, face_height)
        
        # Check if face is too small (too far away - potential spoofing bypass)
        if face_size < min_face_size:
            logger.warning(f"Face too small ({face_size}px) - potential spoofing bypass attempt")
            return False
        
        # Check if face is too large (too close - might be bypass attempt)
        if face_size > max_face_size:
            logger.warning(f"Face too large ({face_size}px) - potential bypass attempt")
            return False
        
        # Additional check: face should be reasonably centered and not too close to edges
        frame_height, frame_width = frame.shape[:2]
        face_center_x = (left + right) // 2
        face_center_y = (top + bottom) // 2
        
        # Face should be in the center 70% of the frame
        margin_x = frame_width * 0.15  # 15% margin from edges
        margin_y = frame_height * 0.15
        
        if (face_center_x < margin_x or face_center_x > frame_width - margin_x or
            face_center_y < margin_y or face_center_y > frame_height - margin_y):
            logger.warning(f"Face too close to frame edges - potential bypass attempt")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating face size and distance: {e}")
        return False

def calculate_face_quality_score(frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> float:
    """
    Calculate a quality score for the face based on size, position, and clarity
    
    Args:
        frame: OpenCV frame/image as numpy array
        bbox: Face bounding box (top, right, bottom, left)
    
    Returns:
        Quality score between 0.0 and 1.0
    """
    try:
        top, right, bottom, left = bbox
        face_width = right - left
        face_height = bottom - top
        
        # Base score from face size (optimal size around 200px)
        optimal_size = 200
        size_diff = abs(max(face_width, face_height) - optimal_size)
        size_score = max(0.0, 1.0 - (size_diff / optimal_size))
        
        # Position score (center is better)
        frame_height, frame_width = frame.shape[:2]
        face_center_x = (left + right) / 2
        face_center_y = (top + bottom) / 2
        
        # Distance from center (0 = perfect center, 1 = at edge)
        center_distance_x = abs(face_center_x - frame_width / 2) / (frame_width / 2)
        center_distance_y = abs(face_center_y - frame_height / 2) / (frame_height / 2)
        center_distance = (center_distance_x + center_distance_y) / 2
        position_score = 1.0 - center_distance
        
        # Combined score
        quality_score = (size_score * 0.6) + (position_score * 0.4)
        
        return max(0.0, min(1.0, quality_score))
        
    except Exception as e:
        logger.error(f"Error calculating face quality score: {e}")
        return 0.0