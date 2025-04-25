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
python -m src.main auth [--model {hog,cnn}]
```

Options:
- `--model hog`: Use HOG model (faster, works on CPU)
- `--model cnn`: Use CNN model (more accurate, requires GPU)

This will activate the camera and attempt to authenticate any face it detects against registered users.

### Continuous Monitoring

For ongoing authentication (e.g., to control access to a secure area):

```
python -m src.main monitor [--model {hog,cnn}]
```

Options:
- `--model hog`: Use HOG model (faster, works on CPU)
- `--model cnn`: Use CNN model (more accurate, requires GPU)

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

## Project Structure

- `src/`
  - `biometric_auth.py`: Core authentication functionality
  - `camera_handler.py`: Camera management and frame capture
  - `config.py`: Configuration settings
  - `face_encoder.py`: Face encoding and model training
  - `face_recognizer.py`: Face recognition algorithms
  - `guided_registration.py`: Guided user registration with head pose detection
  - `head_pose_detector.py`: Head pose estimation and analysis
  - `head_pose_demo.py`: Demo application for head pose detection
  - `main.py`: Command-line interface
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

## Dependencies

- **face_recognition**: Core face recognition library
- **dlib**: Required by face_recognition
- **OpenCV**: For camera handling and image processing
- **numpy**: For numerical operations
- **Pillow**: For image manipulation
- **mediapipe**: For face mesh and head pose detection

## Future Enhancements

- Hardware integration for physical lock control
- Multi-factor authentication
- Liveness detection to prevent spoofing
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

For maximum security, enable both anti-spoofing and use the CNN model.

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.
