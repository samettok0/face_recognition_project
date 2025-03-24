import pickle
from collections import Counter
from pathlib import Path
import logging

import face_recognition
from PIL import Image, ImageDraw

# Constants for visualization
BOUNDING_BOX_COLOR = "blue"
TEXT_COLOR = "white"

# Default path for storing face encodings
DEFAULT_ENCODINGS_PATH = Path("output/encodings.pkl")

# Initialize required directories for the project
Path("data/training").mkdir(parents=True, exist_ok=True)
Path("output").mkdir(exist_ok=True)
Path("data/validation").mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(filename='validation.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def encode_known_faces(
    model: str = "hog", encodings_location: Path = DEFAULT_ENCODINGS_PATH
) -> None:
    """
    Creates a database of known faces from training images.
    
    Args:
        model: Face detection model to use ('hog' or 'cnn')
        encodings_location: Path to save the face encodings database
    """
    names = []
    encodings = []
    for filepath in Path("data/training").glob("*/*"):
        name = filepath.parent.name
        image = face_recognition.load_image_file(filepath)

        # Detect faces and create their encodings
        face_locations = face_recognition.face_locations(image, model=model)
        face_encodings = face_recognition.face_encodings(image, face_locations)

        for encoding in face_encodings:
            names.append(name)
            encodings.append(encoding)

    # Save the database of face encodings
    name_encodings = {"names": names, "encodings": encodings}
    with encodings_location.open(mode="wb") as f:
        pickle.dump(name_encodings, f)

# encode_known_faces()

def recognize_faces(
    image_location: str,
    model: str = "hog",
    encodings_location: Path = DEFAULT_ENCODINGS_PATH,
) -> None:
    """
    Recognizes faces in an image and displays the results with bounding boxes.
    
    Args:
        image_location: Path to the image to analyze
        model: Face detection model to use ('hog' or 'cnn')
        encodings_location: Path to the face encodings database
    """
    # Load the database of known face encodings
    with encodings_location.open(mode="rb") as f:
        loaded_encodings = pickle.load(f)

    # Load and process the input image
    input_image = face_recognition.load_image_file(image_location)

    # Detect faces and create their encodings
    input_face_locations = face_recognition.face_locations(
        input_image, model=model
    )
    input_face_encodings = face_recognition.face_encodings(
        input_image, input_face_locations
    )

    # Prepare image for drawing
    pillow_image = Image.fromarray(input_image)
    draw = ImageDraw.Draw(pillow_image)

    # Process each detected face
    for bounding_box, unknown_encoding in zip(
        input_face_locations, input_face_encodings
    ):
        name = _recognize_face(unknown_encoding, loaded_encodings)
        if not name:
            name = "Unknown"
        _display_face(draw, bounding_box, name)

    del draw
    pillow_image.show()

def _display_face(draw, bounding_box, name):
    """
    Draws a bounding box and name label for a detected face.
    
    Args:
        draw: PIL ImageDraw object
        bounding_box: Face location coordinates (top, right, bottom, left)
        name: Name to display for the face
    """
    top, right, bottom, left = bounding_box
    draw.rectangle(((left, top), (right, bottom)), outline=BOUNDING_BOX_COLOR)
    text_left, text_top, text_right, text_bottom = draw.textbbox(
        (left, bottom), name
    )
    draw.rectangle(
        ((text_left, text_top), (text_right, text_bottom)),
        fill="blue",
        outline="blue",
    )
    draw.text(
        (text_left, text_top),
        name,
        fill="white",
    )

def _recognize_face(unknown_encoding, loaded_encodings):
    """
    Matches an unknown face encoding against known encodings.
    
    Args:
        unknown_encoding: Face encoding to identify
        loaded_encodings: Database of known face encodings
    
    Returns:
        The most likely name match or None if no match found
    """
    boolean_matches = face_recognition.compare_faces(
        loaded_encodings["encodings"], unknown_encoding
    )
    votes = Counter(
        name
        for match, name in zip(boolean_matches, loaded_encodings["names"])
        if match
    )
    if votes:
        return votes.most_common(1)[0][0]

def validate(model: str = "hog"):
    """
    Validates the face recognition model on validation data.
    
    Args:
        model: Face detection model to use ('hog' or 'cnn')
    """
    for filepath in Path("data/validation").rglob("*"):
        if filepath.is_file():
            try:
                logging.info(f"Processing file: {filepath}")
                recognize_faces(
                    image_location=str(filepath.absolute()), model=model
                )
            except Exception as e:
                logging.error(f"Error processing file {filepath}: {e}")

validate()



