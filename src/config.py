from pathlib import Path

# Project directory structure
TRAINING_DIR = Path("data/training")
VALIDATION_DIR = Path("data/validation")
OUTPUT_DIR = Path("output")
ENCODINGS_FILE = OUTPUT_DIR / "encodings.pkl"

# Create required directories
TRAINING_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

# Face detection models
HOG_MODEL = "hog"  # Faster but less accurate
CNN_MODEL = "cnn"  # More accurate but slower, requires GPU for good performance

# Visualization settings
BOUNDING_BOX_COLOR = "blue"
TEXT_COLOR = "white"

# Camera settings
DEFAULT_CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Logging settings
LOG_FILE = "face_recognition.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s" 