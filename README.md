# Face Recognition System

This project implements a face recognition system using computer vision libraries to detect and recognize faces in real-time. It can be used for authentication purposes in IoT projects using a USB camera.

## Features

- **Face Detection & Recognition**: Detect and recognize faces in images and live camera feed
- **Training Interface**: Register new people by capturing their photos and training the model
- **Live Recognition**: Real-time face recognition using a webcam
- **Command-line Interface**: Easy to use commands for different functions

## Project Structure

```
face_recognition_project/
├── src/
│   ├── camera_handler.py    # Enhanced camera operations
│   ├── config.py            # Configuration settings
│   ├── face_encoder.py      # Face encoding and training
│   ├── face_recognizer.py   # Face recognition logic
│   ├── main.py              # Command-line interface
│   ├── utils.py             # Utility functions
│   └── __init__.py          # Package marker
├── data/
│   ├── training/            # Training images organized by person
│   └── validation/          # Validation images
├── output/                  # Output files (encodings, captured images)
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone https://github.com/your-username/face_recognition_project.git
   cd face_recognition_project
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Training the Model

Train the model with existing images in the training directory:

```
python -m src.main train [--model hog|cnn]
```

### Registering a New Person

Capture photos of a new person and add them to the training data:

```
python -m src.main register
```

This will open the camera and guide you through the process of capturing photos.

### Recognizing Faces in an Image

```
python -m src.main recognize path/to/image.jpg [--model hog|cnn]
```

### Live Face Recognition

```
python -m src.main live [--model hog|cnn]
```

## Models

The system supports two face detection models:

- **HOG** (default): Faster but less accurate, suitable for most applications
- **CNN**: More accurate but slower, requires GPU for good performance

## Dependencies

- **face_recognition**: Core face recognition library
- **dlib**: Required by face_recognition
- **OpenCV**: For camera handling and image processing
- **numpy**: For numerical operations
- **Pillow**: For image manipulation

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.