# Face Recognition Biometric Authentication with GPIO Lock Control

A modern facial recognition system for biometric authentication using computer vision, with integrated GPIO lock control for Raspberry Pi access control systems. This system provides secure access control through real-time face recognition with physical lock integration.

Demo Video: https://www.youtube.com/watch?v=Fvyx59dDuRs

## Overview

This project implements a video-based biometric authentication system that can:
- Register new users by capturing face images
- Authenticate users in real-time using face recognition
- **Control physical locks via GPIO pins on Raspberry Pi**
- **Automatically lock/unlock based on face recognition results**
- **Provide auto-lock functionality with configurable delays**
- Continuously monitor for authorized faces
- Detect and analyze head pose for improved user experience
- Provide guided registration with automatic pose detection
- Prevent false positives with temporal voting mechanism
- Support both HOG and CNN face detection models
- **Include comprehensive lock testing and manual control**

The system focuses on accuracy and performance for secure biometric access control with real-world physical integration.

## Hardware Requirements

- Python 3.8+
- Webcam
- **Raspberry Pi (for GPIO lock control)**
- **Electronic lock mechanism (relay, solenoid, etc.)**
- **Proper wiring to GPIO pin 18 (configurable)**
- GPU (recommended for CNN model)

## GPIO Lock Integration

### Hardware Setup

1. **Connect your lock mechanism to GPIO pin 18** (or configure a different pin)
2. **Use appropriate relay/driver circuits** for high-power locks
3. **Ensure proper power supply** for your lock mechanism
4. **Test connections safely** before integrating with face recognition

⚠️ **Safety Note**: Always test your lock mechanism thoroughly before deploying. Ensure you have backup access methods in case of system failure.

### Lock Control Features

- **Automatic unlock** when authorized face is detected
- **Configurable auto-lock delay** (default: 10 seconds)
- **Manual lock/unlock control** for testing and emergencies
- **Lock status monitoring** and logging
- **Graceful shutdown** with automatic lock securing
- **Emergency interrupt handling** (Ctrl+C always locks the system)
- **Simulation mode** for testing without actual GPIO hardware

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

   Note: The `gpiozero` library is included for Raspberry Pi GPIO control. On non-Raspberry Pi systems, the lock controller will run in simulation mode.

## Usage

### Lock System Commands

#### Test Lock Functionality
```bash
# Test the GPIO lock system
python -m src.main test_lock

# Manual lock control interface
python -m src.main manual_lock

# Comprehensive integration test
python test_lock_integration.py [test_mode]
```

Test modes for `test_lock_integration.py`:
- `lock_only`: Test just GPIO lock functionality
- `simulation`: Test face recognition with simulated lock
- `full`: Test complete integration (requires camera and registered users)
- `manual`: Manual lock control interface

### Authentication with Lock Control

#### One-time Authentication with Lock
```bash
# Basic authentication with 10-second auto-lock
python -m src.main auth

# Authentication with custom auto-lock delay
python -m src.main auth --auto-lock-delay 5.0

# Secure authentication with anti-spoofing and fast auto-lock
python -m src.main auth --anti-spoofing --auto-lock-delay 3.0
```

#### Continuous Monitoring with Lock
```bash
# Continuous monitoring with lock control
python -m src.main monitor

# Monitoring with custom auto-lock delay
python -m src.main monitor --auto-lock-delay 15.0

# Secure monitoring with anti-spoofing
python -m src.main monitor --anti-spoofing --auto-lock-delay 8.0
```

### Lock Control Options

All authentication commands now support:
- `--auto-lock-delay SECONDS`: Time to wait before auto-locking after successful authentication (default: 10.0)

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
  - `guided_registration.py`: Guided user registration with head pose detection
  - `head_pose_detector.py`: Head pose estimation and analysis
  - `head_pose_demo.py`: Demo application for head pose detection
  - `main.py`: Command-line interface
  - `anti_spoofing.py`: Liveness detection to prevent spoofing
  - `utils.py`: Utility functions

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

- Hardware integration for physical lock control
- Multi-factor authentication
- Advanced liveness detection methods
- Mobile app control

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
