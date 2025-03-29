# Face Recognition Biometric Authentication

A modern facial recognition system for biometric authentication using computer vision. This system is designed to provide secure access control through real-time face recognition.

## Overview

This project implements a video-based biometric authentication system that can:
- Register new users by capturing face images
- Authenticate users in real-time using face recognition
- Continuously monitor for authorized faces
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

Before authentication, you need to register at least one user:

```
python -m src.main register
```

Follow the on-screen instructions to:
- Enter your name
- Capture multiple face images (10 recommended)
- Train the recognition model

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
  - `main.py`: Command-line interface
  - `utils.py`: Utility functions

## Improving Recognition Accuracy

If you experience incorrect identifications:

1. **Choose the right model**: 
   - Use CNN model for higher accuracy (requires GPU)
   - Use HOG model for faster processing
2. **Increase training data**: Capture more images (15-20) during registration
3. **Vary conditions**: Register in different lighting and angles
4. **Adjust threshold**: Modify the recognition threshold in `BiometricAuth` class
5. **Consistent lighting**: Ensure good, consistent lighting during authentication

## Dependencies

- **face_recognition**: Core face recognition library
- **dlib**: Required by face_recognition
- **OpenCV**: For camera handling and image processing
- **numpy**: For numerical operations
- **Pillow**: For image manipulation

## Future Enhancements

- Hardware integration for physical lock control
- Multi-factor authentication
- Liveness detection to prevent spoofing
- Mobile app control

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.
