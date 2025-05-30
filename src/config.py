from pathlib import Path

# Project directory structure
TRAINING_DIR = Path("data/training")
OUTPUT_DIR = Path("output")
ENCODINGS_FILE = OUTPUT_DIR / "encodings.pkl"

# Create required directories
TRAINING_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Face detection models
HOG_MODEL = "hog"  # Faster but less accurate
CNN_MODEL = "cnn"  # More accurate but slower, requires GPU for good performance

# Visualization settings
BOUNDING_BOX_COLOR = "blue"
TEXT_COLOR = "white"

# Camera settings
DEFAULT_CAMERA_INDEX = 0
FRAME_WIDTH = 320  # Lower resolution for better performance on Raspberry Pi
FRAME_HEIGHT = 240  # Lower resolution for better performance on Raspberry Pi

# GPIO Lock settings
GPIO_LOCK_PIN = 18  # BCM pin number for lock control (physical pin 12)
LOCK_UNLOCK_DURATION = 5.0  # How long to keep lock unlocked (seconds)
ENABLE_GPIO_LOCK = True  # Set to False to disable physical lock and use simulation only
GPIO_LOCK_ACTIVE_HIGH = False  # Set to True if relay is active HIGH, False if active LOW

# Head pose settings
# Multipliers for sensitivity scaling - higher values = more sensitive
YAW_MULTIPLIER = 30
PITCH_MULTIPLIER = 500
ROLL_MULTIPLIER = 0.5

# Width factor for calculation
WIDTH_FACTOR = 0.05

# Thresholds for pose classification (degrees)
YAW_THRESHOLD = 10
PITCH_THRESHOLD = 10
ROLL_THRESHOLD = 10

# Centering tolerance (percentage of width)
CENTERING_TOLERANCE = 0.1

# Time settings
STABILIZATION_TIME = 1.5  # Time in seconds for pose to be considered stable
COUNTDOWN_TIME = 3  # Countdown time in seconds before capturing
BURST_DELAY = 0.5  # Delay between burst captures in seconds

# Logging settings
LOG_FILE = "face_recognition.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s" 