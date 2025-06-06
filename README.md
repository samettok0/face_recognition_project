# Face Recognition Biometric Authentication

A modern facial recognition system for biometric authentication using computer vision. This system is designed to provide secure access control through real-time face recognition.

Demo Video: https://www.youtube.com/watch?v=Fvyx59dDuRs

## Overview

This project implements a video-based biometric authentication system that can:
- Register new users by capturing face images
- Authenticate users in real-time using face recognition
- Continuously monitor for authorized faces
- Detect and analyze head pose for improved user experience
- Provide guided registration with automatic pose detection
- Prevent false positives with temporal voting mechanism
- Provide a foundation for integration with physical lock mechanisms
- Support both HOG and CNN face detection models

The system focuses on accuracy and performance for secure biometric access control.

## Requirements

- Python 3.8+
- Webcam
- GPU (recommended for CNN model)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/samettok0/face-recognition-auth.git
   cd face-recognition-auth
   ```

2. Create a virtual environment (recommended):
   ```
   python -m venv facerecogenv
   source facerecogenv/bin/activate  # On Windows: facerecogenv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

   Note: Installation of `dlib` may require additional steps on some systems.

## Usage

### Register a New User

Before authentication, you need to register at least one user. You have two options:

#### Standard Registration:

```
python -m src.main register
```

Follow the on-screen instructions to:
- Enter your name
- Capture multiple face images (10 recommended)
- Train the recognition model

#### Guided Registration (Recommended):

```
python -m src.main guided-register
```

This advanced registration method features:
- Automatic head pose detection (Forward, Left, Right, Up, Down)
- Guided UI with real-time feedback
- Automatic photo capture when your pose is correct
- Flash effect for better user experience
- Automatic burst mode for multiple photos per pose

Follow the on-screen instructions to:
- Enter your name
- Choose how many photos to capture per pose
- Follow the guided process to capture images from all angles
- Hold each pose steady when prompted
- Watch for the countdown and burst capture

The guided registration creates a more comprehensive dataset with images from multiple angles, which significantly improves recognition accuracy.

### One-time Authentication

To run a single authentication attempt:

```
python -m src.main auth [--model {hog,cnn}] [--anti-spoofing] [--window WINDOW] [--min-live MIN_LIVE] [--min-match MIN_MATCH] [--live-threshold LIVE_THRESHOLD]
```

Options:
- `--model hog`: Use HOG model (faster, works on CPU)
- `--model cnn`: Use CNN model (more accurate, requires GPU)
- `--anti-spoofing`: Enable anti-spoofing detection
- `--window`: Number of recent frames to keep for decision gate (default: 15)
- `--min-live`: Minimum number of frames that must pass liveness check (default: 12)
- `--min-match`: Minimum number of frames that must match an authorized user (default: 12)
- `--live-threshold`: Threshold for liveness detection (0.0-1.0, default: 0.9)

This will activate the camera and attempt to authenticate any face it detects against registered users.

Common usage examples:
```
# Standard authentication with anti-spoofing
python -m src.main auth --anti-spoofing

# Faster authentication (~1 second response)
python -m src.main auth --anti-spoofing --window 10 --min-live 8 --min-match 8

# More secure authentication (requires more consistent matching)
python -m src.main auth --anti-spoofing --window 20 --min-live 18 --min-match 18
```

### Continuous Monitoring

For ongoing authentication (e.g., to control access to a secure area):

```
python -m src.main monitor [--model {hog,cnn}] [--anti-spoofing]
```

Options:
- `--model hog`: Use HOG model (faster, works on CPU)
- `--model cnn`: Use CNN model (more accurate, requires GPU)
- `--anti-spoofing`: Enable anti-spoofing detection

This mode continuously checks for authorized faces and triggers the authentication process when a face is detected.

### Head Pose Detection Demo

To run the head pose detection demo:

```
python -m src.main head_pose
```

This will start a real-time demo showing:
- Head pose detection (Left, Right, Up, Down, Forward)
- Face centering detection
- Numerical yaw, pitch, and roll estimates

This feature is useful for improving authentication by ensuring users are properly positioned.

### GPIO Lock Control (Raspberry Pi)

The system includes GPIO lock control functionality for physical door locks on Raspberry Pi. When authentication succeeds, the system can automatically unlock a physical lock mechanism.

#### Hardware Setup

1. **Connect your lock mechanism to GPIO pin 18** (BCM numbering, physical pin 12)
2. **Use a relay module** to control high-voltage lock mechanisms safely
3. **Ensure proper power supply** for your lock mechanism

**Wiring Example:**
```
Raspberry Pi GPIO 18 → Relay Module Signal Pin
Relay Module VCC → 5V or 3.3V (depending on relay)
Relay Module GND → Ground
Lock Mechanism → Relay NO/NC contacts
```

#### Software Setup

1. **Install GPIO library** (if not already installed):
   ```bash
   pip install lgpio
   ```

2. **Add user to gpio group** (to run without sudo):
   ```bash
   sudo usermod -a -G gpio $USER
   sudo reboot
   ```

#### Testing the Lock

Before using with authentication, test the lock functionality:

**Using the built-in test command:**
```bash
python -m src.main lock_test [--cycles 3]
```

**Using the standalone test script:**
```bash
# Basic test
python test_lock.py

# Manual control mode
python test_lock.py --manual

# Custom test cycles
python test_lock.py --cycles 5

# Override GPIO pin
python test_lock.py --pin 20 --duration 3.0
```

The manual control mode provides interactive commands:
- `unlock` or `u` - Unlock the door
- `lock` or `l` - Lock the door  
- `status` or `s` - Check lock status
- `test` or `t` - Run test cycle
- `auth` or `a` - Simulate authentication unlock
- `quit` or `q` - Exit

#### Configuration

Lock settings can be configured in `src/config.py`:

```python
# GPIO Lock settings
GPIO_LOCK_PIN = 18  # BCM pin number for lock control
LOCK_UNLOCK_DURATION = 5.0  # How long to keep lock unlocked (seconds)
ENABLE_GPIO_LOCK = True  # Set to False to disable physical lock
GPIO_LOCK_ACTIVE_HIGH = False  # Set to True if relay is active HIGH, False if active LOW
```

**Important: Relay Configuration**
- **Active HIGH relay**: Set `GPIO_LOCK_ACTIVE_HIGH = True` - GPIO HIGH unlocks, GPIO LOW locks
- **Active LOW relay**: Set `GPIO_LOCK_ACTIVE_HIGH = False` - GPIO LOW unlocks, GPIO HIGH locks

Most common relay modules are **active LOW**, so the default setting should work. If your lock behavior is inverted (lock command unlocks, unlock command locks), change this setting to `True`.

#### Using with Authentication

The lock automatically activates when authentication succeeds:

```bash
# Authentication with lock control
python -m src.main auth --anti-spoofing

# Continuous monitoring with lock control
python -m src.main monitor --anti-spoofing
```

When an authorized user is authenticated:
1. The system logs the successful authentication
2. GPIO pin 18 is activated (HIGH) to unlock the door
3. The lock remains unlocked for the configured duration (default: 5 seconds)
4. GPIO pin 18 is deactivated (LOW) to lock the door again
5. The system continues monitoring (in monitor mode)

#### Lock Behavior

- **Default State**: Locked (GPIO pin LOW)
- **Unlock Duration**: 5 seconds (configurable)
- **Automatic Re-lock**: Yes, after unlock duration expires
- **Fail-Safe**: Lock defaults to locked state on errors or system shutdown
- **Simulation Mode**: If GPIO is unavailable, lock operations are simulated with console output

#### Troubleshooting

**Permission Errors:**
```bash
# Add user to gpio group and reboot
sudo usermod -a -G gpio $USER
sudo reboot
```

**GPIO Library Issues:**
```bash
# Install lgpio for Raspberry Pi 5
pip install lgpio

# For older Pi models, you might need RPi.GPIO
pip install RPi.GPIO
```

**Inverted Lock Behavior:**
If your lock operates in reverse (lock command unlocks, unlock command locks):
1. Edit `src/config.py`
2. Change `GPIO_LOCK_ACTIVE_HIGH = False` to `GPIO_LOCK_ACTIVE_HIGH = True`
3. Test with: `python test_lock.py --cycles 1`

**Testing Without Hardware:**
- Set `ENABLE_GPIO_LOCK = False` in config.py
- The system will simulate lock operations with console output
- Useful for development and testing

### Retraining the Model

If you need to update the face recognition model after adding new users:

```
python -m src.main train [--model {hog,cnn}]
```

Options:
- `--model hog`: Use HOG model (faster, works on CPU)
- `--model cnn`: Use CNN model (more accurate, requires GPU)

## Model Selection Guide

The system supports two face detection models:

1. **HOG Model** (default)
   - Faster processing speed
   - Works well on CPU
   - Typical confidence scores: 0.60-0.70
   - Good for real-time applications
   - Recommended for most use cases

2. **CNN Model**
   - Higher accuracy
   - Requires GPU for good performance
   - Typical confidence scores: 0.80-0.90
   - Slower processing speed
   - Recommended for high-security applications

## Temporal Voting Mechanism

The system implements a temporal voting gate to prevent false positives from momentary misidentifications or spoofing attacks. This ensures that authentication only succeeds when there's consistent evidence over time.

### How It Works

1. The system maintains sliding windows of recent results for:
   - Liveness detection (is the face real)
   - Face matching (is it an authorized person)

2. Authentication succeeds only when both criteria pass consistently:
   - At least X frames out of the last Y frames must pass liveness check
   - At least Z frames out of the last Y frames must pass face matching

3. This prevents single-frame errors from triggering false authentication, such as:
   - Momentary incorrect face matches
   - Brief spoofing attempts
   - Camera glitches or processing errors

### Configuration Parameters

- `window`: Total number of recent frames to consider (default: 15)
- `min-live`: Minimum frames that must pass liveness check (default: 12)
- `min-match`: Minimum frames that must match an authorized user (default: 12)

### Timing Estimates

- Default settings (~15 frames at 7-8 FPS): ≈ 2 seconds
- Faster settings (10 frames, 8 required): ≈ 1.25 seconds 
- More secure (20 frames, 18 required): ≈ 2.5 seconds

Adjust these parameters based on your security requirements and desired response speed.

## Project Structure

- `src/`
  - `biometric_auth.py`: Core authentication functionality
  - `camera_handler.py`: Camera management and frame capture
  - `config.py`: Configuration settings
  - `decision_gate.py`: Temporal voting mechanism
  - `face_encoder.py`: Face encoding and model training
  - `face_recognizer.py`: Face recognition algorithms
  - `gpio_lock.py`: GPIO lock control for Raspberry Pi
  - `guided_registration.py`: Guided user registration with head pose detection
  - `head_pose_detector.py`: Head pose estimation and analysis
  - `head_pose_demo.py`: Demo application for head pose detection
  - `main.py`: Command-line interface
  - `anti_spoofing.py`: Liveness detection to prevent spoofing
  - `utils.py`: Utility functions
- `test_lock.py`: Standalone GPIO lock testing script

## Improving Recognition Accuracy

If you experience incorrect identifications:

1. **Choose the right model**: 
   - Use CNN model for higher accuracy (requires GPU)
   - Use HOG model for faster processing
2. **Use guided registration**: Register with the guided system to capture poses from multiple angles
3. **Increase training data**: Capture more images per pose (3-5 recommended)
4. **Vary conditions**: Register in different lighting and angles
5. **Adjust threshold**: Modify the recognition threshold in `BiometricAuth` class
6. **Consistent lighting**: Ensure good, consistent lighting during authentication
7. **Enable head pose verification**: Use `--head-pose` option to require proper face positioning
8. **Adjust temporal voting**: Increase window size and threshold for higher security

## Dependencies

- **face_recognition**: Core face recognition library
- **dlib**: Required by face_recognition
- **OpenCV**: For camera handling and image processing
- **numpy**: For numerical operations
- **Pillow**: For image manipulation
- **mediapipe**: For face mesh and head pose detection
- **deepface**: For anti-spoofing detection

## Future Enhancements

- ✅ Hardware integration for physical lock control (implemented)
- Multi-factor authentication
- Advanced liveness detection methods
- Mobile app control
- Web-based administration interface
- Multiple lock support
- Access logging and audit trails

## Anti-Spoofing Detection

The system includes anti-spoofing detection to prevent unauthorized access using photos, videos, or masks. This feature uses DeepFace's anti-spoofing capabilities to distinguish between real faces and fake presentations.

### Anti-Spoofing Demo

To run the anti-spoofing detection demo:

```
python -m src.main anti_spoof [--camera CAMERA_INDEX]
```

Options:
- `--camera`: Camera index to use (default: 0)

This demo will show real-time detection of real vs. fake faces, helping you understand how the anti-spoofing system works.

### Using Anti-Spoofing with Authentication

To enable anti-spoofing during authentication:

```
python -m src.main auth --anti-spoofing [--model {hog,cnn}]
```

For continuous monitoring with anti-spoofing:

```
python -m src.main monitor --anti-spoofing [--model {hog,cnn}]
```

When anti-spoofing is enabled, the system will:
1. Detect faces as usual
2. Perform recognition to identify the person
3. Run additional checks to ensure the face is real, not a photo or video
4. Mark fake faces with a purple label and refuse authentication

This provides an additional layer of security against presentation attacks.

### How Anti-Spoofing Works

The anti-spoofing system uses computer vision techniques to analyze:
- Texture patterns that distinguish real skin from printed photos
- Micro-movements that would be present in real faces but not in static images
- Depth information that helps identify flat surfaces vs. 3D faces

This provides robust protection against common spoofing attempts using:
- Printed photos
- Digital images on screens
- Video replays
- Some types of masks

For maximum security, enable both anti-spoofing and use the CNN model with stricter temporal voting parameters.

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.
