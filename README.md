# Face Detection Project

This project implements a face detection system using a camera feed. It utilizes various libraries to detect and recognize faces in real-time.

## Project Structure

```
face_detection_project
├── src
│   ├── detector.py       # Main logic for detecting faces using the camera feed
│   ├── camera.py         # Handles camera operations and video frame capture
│   ├── utils.py          # Utility functions for drawing and displaying
│   └── __init__.py       # Marks the directory as a Python package
├── requirements.txt       # Lists the dependencies required for the project
└── README.md              # Documentation for the project
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd face_detection_project
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the face detection program:
   ```
   python src/detector.py
   ```

2. The program will open a window displaying the camera feed with detected faces highlighted.

## Dependencies

- `face_recognition`
- `opencv-python`
- `Pillow`

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.