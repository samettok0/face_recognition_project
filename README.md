# Face Recognition Biometric Authentication

A modern facial recognition system for biometric authentication using computer vision with enhanced security features, GUI feedback, and anti-spoofing protection. This system is designed to provide secure access control through real-time face recognition with comprehensive security measures.

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
- **Enhanced Security**: Prevent anti-spoofing bypass attempts
- **GUI Feedback**: Real-time visual feedback for authentication status
- **Face Quality Validation**: Ensure proper face positioning and distance
- **Comprehensive Logging**: Track security events and potential attacks

The system focuses on accuracy, security, and performance for secure biometric access control.

## Enhanced Security Features

### Anti-Spoofing Bypass Prevention

The system includes comprehensive security measures to prevent sophisticated spoofing attacks:

#### 1. Face Size and Distance Validation
- **Minimum Face Size**: Prevents faces that are too far away (potential spoofing bypass)
- **Maximum Face Size**: Prevents faces that are too close (potential bypass attempt)
- **Optimal Range**: 100-400px face size for proper anti-spoofing detection

#### 2. Face Position Validation
- **Edge Detection**: Faces too close to frame edges are rejected
- **Center Requirement**: Face must be in center 70% of frame
- **Margin Check**: 15% margin from all edges

#### 3. Face Quality Scoring
- **Size Score**: Based on proximity to optimal face size (200px)
- **Position Score**: Based on distance from frame center
- **Combined Score**: Weighted quality assessment (60% size + 40% position)
- **Quality Threshold**: 0.6 (60%) minimum required for authentication

#### 4. Enhanced Decision Gate
- **Three-Factor Authentication**: Liveness + Recognition + Quality
- **Quality Queue**: Tracks quality across multiple frames
- **Consistency Requirements**: All factors must pass consistently

### GUI Feedback System

The system provides real-time visual feedback during authentication:

#### Authentication Success
- **Green overlay** with "AUTHENTICATION SUCCESSFUL" message
- **Personalized welcome** message (e.g., "Welcome, John!")
- **3-second display** before continuing to unlock process
- **Professional styling** with semi-transparent background

#### Authentication Failure
- **Red overlay** with "AUTHENTICATION FAILED" message
- **Specific failure reasons**:
  - "Exceeded 120 frames limit"
  - "Timeout reached (60 seconds)"
  - "No authorized user detected"
  - "Face quality too low"
- **3-second display** with helpful tips

#### Real-Time Status
- **Frame counter** showing progress
- **Quality status** (GOOD/POOR) with color coding
- **Enhanced anti-spoofing feedback** with live/spoofed indicators

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

To run a single authentication attempt with enhanced security:

```
python -m src.main auth [--model {hog,cnn}] [--anti-spoofing] [--window WINDOW] [--min-live MIN_LIVE] [--min-match MIN_MATCH] [--live-threshold LIVE_THRESHOLD]
```

Options:
- `--model hog`: Use HOG model (faster, works on CPU)
- `--model cnn`: Use CNN model (more accurate, requires GPU)
- `--anti-spoofing`: Enable enhanced anti-spoofing detection with bypass prevention
- `--window`: Number of recent frames to keep for decision gate (default: 15)
- `--min-live`: Minimum number of frames that must pass liveness check (default: 12)
- `--min-match`: Minimum number of frames that must match an authorized user (default: 12)
- `--live-threshold`: Threshold for liveness detection (0.0-1.0, default: 0.9)

This will activate the camera and attempt to authenticate any face it detects against registered users with comprehensive security checks.

Common usage examples:
```
# Standard enhanced authentication with anti-spoofing
python -m src.main auth --anti-spoofing

# Faster authentication (~1 second response)
python -m src.main auth --anti-spoofing --window 10 --min-live 8 --min-match 8

# Maximum security authentication (requires perfect positioning)
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
- `--anti-spoofing`: Enable enhanced anti-spoofing detection

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

### Anti-Spoofing Demo

To test the anti-spoofing detection:

```
python -m src.main anti_spoof [--camera CAMERA_INDEX]
```

This demonstrates the system's ability to detect fake vs real faces.

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

## Security Features

### Enhanced Anti-Spoofing Protection

The system implements multiple layers of security to prevent sophisticated spoofing attacks:

#### Distance-Based Bypass Prevention
- **Face Size Validation**: Prevents faces that are too far or too close
- **Position Validation**: Ensures face is properly centered
- **Quality Scoring**: Quantitative assessment of face quality
- **Multi-Frame Consistency**: Requires consistent quality across frames

#### Security Checks
1. **Liveness Detection**: Anti-spoofing algorithms detect fake faces
2. **Face Recognition**: Match against authorized users
3. **Face Quality**: Size, position, and clarity validation
4. **Temporal Voting**: Decision gate ensures consistent results

#### Configuration Options
```python
# Face size limits (pixels)
min_face_size = 100  # Minimum face size
max_face_size = 400  # Maximum face size

# Quality thresholds
quality_threshold = 0.6  # Minimum quality score (0.0-1.0)
quality_required = 3     # Minimum quality frames

# Decision gate parameters
window = 15        # Total frames to consider
min_live = 12      # Minimum live frames
min_match = 12     # Minimum match frames
min_quality = 10   # Minimum quality frames
```

### Security Testing Scenarios

#### 1. Normal Authentication (Should Pass)
- **Setup**: Face at normal distance, centered in frame
- **Expected**: Authentication successful
- **Quality Score**: 0.7-0.9

#### 2. Face Too Far (Should Fail)
- **Setup**: Move face/phone far from camera
- **Expected**: Authentication fails due to small face size
- **Detection**: `Face too small (XXpx) - potential spoofing bypass attempt`

#### 3. Face Too Close (Should Fail)
- **Setup**: Move face very close to camera
- **Expected**: Authentication fails due to large face size
- **Detection**: `Face too large (XXpx) - potential bypass attempt`

#### 4. Face at Edge (Should Fail)
- **Setup**: Position face at frame edge
- **Expected**: Authentication fails due to position validation
- **Detection**: `Face too close to frame edges - potential bypass attempt`

#### 5. Poor Quality (Should Fail)
- **Setup**: Face at suboptimal distance/position
- **Expected**: Authentication fails due to low quality score
- **Detection**: `Face quality too low (X.XX) - potential bypass attempt`

## GUI Feedback System

### Real-Time Visual Feedback

The system provides immediate visual feedback during authentication:

#### During Authentication
- **Frame counter**: Shows progress (e.g., "Frame: 5/120")
- **Quality status**: Color-coded quality indicator (GOOD/POOR)
- **Face detection**: "FACE DETECTED" when faces are found
- **Recognition results**: Real-time face recognition feedback

#### Success Feedback
- **Green overlay** with success message
- **Personalized welcome** text
- **3-second display** before continuing
- **Professional styling** with borders and transparency

#### Failure Feedback
- **Red overlay** with failure message
- **Specific failure reason** displayed
- **Helpful tips** for improvement
- **3-second display** before closing

### Enhanced Anti-Spoofing Display

The GUI shows detailed anti-spoofing information:
- **"Match: [Name], LIVE"** for authenticated live faces
- **"Match: [Name], SPOOFED"** for detected fake faces
- **"Match: Unknown Face, LIVE"** for unknown live faces
- **"Match: Unknown Face, SPOOFED"** for unknown fake faces
- **Color coding**: Green for live, red for spoofed, purple for fake

## Performance and Compatibility

### Performance Impact
- **Face Size Check**: ~0.1ms per frame
- **Quality Calculation**: ~0.2ms per frame
- **Total Overhead**: <1ms per frame
- **FPS Impact**: Negligible (<1% reduction)

### Memory Usage
- **Additional Queues**: ~100 bytes per queue
- **Quality Tracking**: ~50 bytes per user
- **Total Memory**: <1KB additional

### Compatibility
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Camera support**: Compatible with all camera types supported by OpenCV
- **Resolution independent**: Automatically scales to different screen resolutions

## Troubleshooting

### Common Issues

#### Authentication Failures

**"Face too small" Errors**
- **Cause**: Face is too far from camera
- **Solution**: Move closer to camera (optimal: 30-60cm)
- **Security Note**: This is working as intended

**"Face too large" Errors**
- **Cause**: Face is too close to camera
- **Solution**: Move further from camera
- **Security Note**: This is working as intended

**"Face quality too low" Errors**
- **Cause**: Face not optimally positioned
- **Solution**: Center face in frame at proper distance
- **Security Note**: This prevents bypass attempts

**"Face too close to frame edges" Errors**
- **Cause**: Face positioned at edge of camera view
- **Solution**: Center face in frame
- **Security Note**: This prevents bypass attempts

#### GUI Issues

**No GUI Feedback Appearing**
- Check if camera is working properly
- Verify OpenCV installation and display capabilities
- Ensure authentication is running in GUI mode (not headless)

**Poor Text Readability**
- Check camera lighting conditions
- Verify screen resolution and scaling settings
- Ensure proper contrast between text and background

#### Performance Issues
- Reduce camera resolution if needed
- Check system resources during authentication
- Consider disabling anti-spoofing for faster processing

### Debug Information
```bash
# Enable verbose logging
export PYTHONPATH=.
python -m src.main auth --anti-spoofing

# Check logs for quality scores
tail -f face_recognition.log | grep "quality"

# Check logs for security events
tail -f face_recognition.log | grep "bypass"
```

## Project Structure

- `src/`
  - `biometric_auth.py`: Core authentication functionality with enhanced security
  - `camera_handler.py`: Camera management and frame capture
  - `config.py`: Configuration settings
  - `decision_gate.py`: Enhanced temporal voting mechanism with quality checks
  - `face_encoder.py`: Face encoding and model training
  - `face_recognizer.py`: Face recognition algorithms
  - `gpio_lock.py`: GPIO lock control for Raspberry Pi
  - `guided_registration.py`: Guided user registration with head pose detection
  - `head_pose_detector.py`: Head pose estimation and analysis
  - `head_pose_demo.py`: Demo application for head pose detection
  - `main.py`: Command-line interface with enhanced security
  - `anti_spoofing.py`: Liveness detection to prevent spoofing
  - `utils.py`: Utility functions including GUI feedback and security validation
- `test_lock.py`: Standalone GPIO lock testing script

## Future Enhancements

### Planned Security Improvements
1. **Dynamic Quality Thresholds**: Adjust based on lighting conditions
2. **Multi-Camera Validation**: Use multiple cameras for 3D validation
3. **Behavioral Analysis**: Track face movement patterns
4. **Machine Learning**: Train models on bypass attempts
5. **Hardware Integration**: Use depth sensors when available

### Configuration Enhancements
1. **Environment-Specific Settings**: Different thresholds for different environments
2. **User-Specific Quality**: Personalized quality requirements
3. **Adaptive Thresholds**: Automatic adjustment based on success rates
4. **Security Levels**: Configurable security vs. convenience trade-offs

### GUI Enhancements
1. **Animated transitions** between normal view and status messages
2. **Sound feedback** integration with buzzer systems
3. **Customizable themes** for different deployment environments
4. **Multi-language support** for status messages
5. **Accessibility features** for users with visual impairments

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with OpenCV for computer vision
- Uses face_recognition library for face detection and recognition
- Implements DeepFace for anti-spoofing detection
- Enhanced security features prevent sophisticated bypass attempts
