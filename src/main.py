#!/usr/bin/env python3
import argparse
import cv2
import numpy as np
import sys
import os
from pathlib import Path

from .config import HOG_MODEL, CNN_MODEL
from .face_encoder import FaceEncoder
from .face_recognizer import FaceRecognizer
from .camera_handler import CameraHandler
from .utils import get_logger

logger = get_logger(__name__)

def process_frame_with_recognition(frame, recognizer):
    """Process a frame with face recognition and draw bounding boxes"""
    # Convert BGR to RGB (face_recognition uses RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Recognize faces
    results = recognizer.recognize_face_in_frame(rgb_frame)
    
    # Draw bounding boxes and names
    for (top, right, bottom, left), name in results:
        # Draw rectangle around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        # Draw name label
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
        cv2.putText(frame, name, (left + 6, bottom - 6), 
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 1)
    
    return frame

def register_new_person(camera_handler, face_encoder):
    """Register a new person by taking their photos and training the model"""
    name = input("Enter the person's name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return False
    
    # Normalize the name (lowercase, replace spaces with underscores)
    normalized_name = name.lower().replace(" ", "_")
    
    # Number of training images to capture
    try:
        num_images = int(input("How many photos to capture (default: 5): ") or "5")
    except ValueError:
        num_images = 5
    
    print(f"\nCapturing {num_images} photos for {name}...")
    print("Position your face in the camera and press SPACE to capture each photo.")
    print("Press ESC to cancel.")
    
    camera = camera_handler
    if not camera.start():
        print("Failed to start camera.")
        return False
    
    try:
        saved_paths = []
        count = 0
        
        while count < num_images:
            # Get frame
            frame = camera.get_frame()
            if frame is None:
                continue
            
            # Display with instruction
            cv2.putText(frame, f"Press SPACE to capture ({count+1}/{num_images})", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Register New Face", frame)
            
            # Wait for key press
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC key
                print("Registration cancelled.")
                return False
            elif key == 32:  # SPACE key
                # Save image to person directory
                person_dir = Path("data/training") / normalized_name
                person_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate filename
                image_path = str(person_dir / f"{count+1}.jpg")
                
                # Save image
                cv2.imwrite(image_path, frame)
                saved_paths.append(image_path)
                print(f"Captured image {count+1}/{num_images}")
                count += 1
    
    finally:
        camera.stop()
        cv2.destroyAllWindows()
    
    if saved_paths:
        print(f"Successfully captured {len(saved_paths)} images for {name}.")
        print("Training the model with new images...")
        face_encoder.encode_known_faces()
        print("Training complete!")
        return True
    
    return False

def live_recognition(model):
    """Run live face recognition from webcam"""
    recognizer = FaceRecognizer(model=model)
    camera = CameraHandler()
    
    def process_frame(frame):
        return process_frame_with_recognition(frame, recognizer)
    
    print("Starting live recognition...")
    print("Press 'q' to quit")
    
    camera.show_preview(window_name="Face Recognition", process_frame=process_frame)

def main():
    parser = argparse.ArgumentParser(description="Face Recognition System")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Train command
    train_parser = subparsers.add_parser("train", help="Train the face recognition model")
    train_parser.add_argument("--model", choices=["hog", "cnn"], default="hog",
                             help="Face detection model to use (hog is faster, cnn is more accurate)")
    
    # Recognize command
    recognize_parser = subparsers.add_parser("recognize", 
                                          help="Recognize faces in an image")
    recognize_parser.add_argument("image", help="Path to the image to analyze")
    recognize_parser.add_argument("--model", choices=["hog", "cnn"], default="hog",
                                help="Face detection model to use")
    
    # Live recognition command
    live_parser = subparsers.add_parser("live", help="Run live face recognition from webcam")
    live_parser.add_argument("--model", choices=["hog", "cnn"], default="hog",
                          help="Face detection model to use")
    
    # Register command
    register_parser = subparsers.add_parser("register", 
                                         help="Register a new person by taking their photos")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "train":
        print("Training face recognition model...")
        encoder = FaceEncoder(model=args.model)
        encoder.encode_known_faces()
        print("Training complete!")
        
    elif args.command == "recognize":
        if not os.path.exists(args.image):
            print(f"Error: Image file not found: {args.image}")
            return
            
        print(f"Recognizing faces in {args.image}...")
        recognizer = FaceRecognizer(model=args.model)
        recognizer.recognize_faces(args.image)
        
    elif args.command == "live":
        live_recognition(args.model)
        
    elif args.command == "register":
        camera = CameraHandler()
        encoder = FaceEncoder()
        register_new_person(camera, encoder)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()