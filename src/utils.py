import logging
import os
from PIL import Image, ImageDraw
from typing import Tuple, List
from .config import BOUNDING_BOX_COLOR, TEXT_COLOR, LOG_FILE, LOG_FORMAT

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=LOG_FORMAT
)

def draw_bounding_box(draw: ImageDraw, bounding_box: Tuple[int, int, int, int], name: str) -> None:
    """
    Draws a bounding box and name label for a detected face.
    
    Args:
        draw: PIL ImageDraw object
        bounding_box: Face location coordinates (top, right, bottom, left)
        name: Name to display for the face
    """
    top, right, bottom, left = bounding_box
    draw.rectangle(((left, top), (right, bottom)), outline=BOUNDING_BOX_COLOR, width=3)
    text_left, text_top, text_right, text_bottom = draw.textbbox(
        (left, bottom), name
    )
    draw.rectangle(
        ((text_left, text_top), (text_right, text_bottom)),
        fill=BOUNDING_BOX_COLOR,
        outline=BOUNDING_BOX_COLOR,
    )
    draw.text(
        (text_left, text_top),
        name,
        fill=TEXT_COLOR,
    )

def resize_image(image: Image.Image, width: int) -> Image.Image:
    """
    Resizes an image maintaining aspect ratio
    
    Args:
        image: PIL Image to resize
        width: Target width
        
    Returns:
        Resized PIL Image
    """
    aspect_ratio = image.height / image.width
    new_height = int(width * aspect_ratio)
    return image.resize((width, new_height))

def ensure_dir_exists(directory: str) -> None:
    """
    Ensures a directory exists, creating it if necessary
    
    Args:
        directory: Path to the directory
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        
def get_logger(name: str) -> logging.Logger:
    """
    Gets a logger with the given name
    
    Args:
        name: Name for the logger
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)