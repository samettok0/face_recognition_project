#!/usr/bin/env python3
import argparse
import cv2
import numpy as np
import sys
import os
from pathlib import Path

from .face_encoder import FaceEncoder
from .biometric_auth import BiometricAuth
from .camera_handler import CameraHandler
from .utils import get_logger

logger = get_logger(__name__)

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
        num_images = int(input("How many photos to capture (default: 10): ") or "10")
    except ValueError:
        num_images = 10
    
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

def run_authenticate():
    """Run one-time authentication attempt"""
    auth = BiometricAuth(recognition_threshold=0.55)
    
    # Add all users from training directory as authorized
    training_dir = Path("data/training")
    if training_dir.exists():
        for person_dir in training_dir.iterdir():
            if person_dir.is_dir():
                auth.add_authorized_user(person_dir.name)
    
    print("Starting authentication...")
    print("Looking for authorized user. Press 'q' to quit.")
    
    success, username = auth.authenticate(max_attempts=30, timeout=20)
    
    if success:
        print(f"✅ Authentication successful: {username}")
    else:
        print("❌ Authentication failed")

def run_continuous_monitoring():
    """Run continuous monitoring and authentication"""
    auth = BiometricAuth(
        recognition_threshold=0.55,  # Adjust based on your needs
        consecutive_matches_required=3  # How many frames must match
    )
    
    # Add all users from training directory as authorized
    training_dir = Path("data/training")
    if training_dir.exists():
        for person_dir in training_dir.iterdir():
            if person_dir.is_dir():
                auth.add_authorized_user(person_dir.name)
                print(f"Authorized user: {person_dir.name}")
    
    print("Starting continuous monitoring...")
    print("Looking for authorized users. Press 'q' to quit.")
    
    auth.run_continuous_monitoring()

def main():
    parser = argparse.ArgumentParser(description="Face Recognition Authentication System")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Train command
    train_parser = subparsers.add_parser("train", help="Train the face recognition model")
    train_parser.add_argument("--model", choices=["hog", "cnn"], default="hog",
                             help="Face detection model to use (hog is faster, cnn is more accurate)")
    
    # Authentication command
    auth_parser = subparsers.add_parser("auth", 
                                      help="Run one-time authentication")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", 
                                        help="Run continuous monitoring for authorized faces")
    
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
        
    elif args.command == "auth":
        run_authenticate()
        
    elif args.command == "monitor":
        run_continuous_monitoring()
        
    elif args.command == "register":
        camera = CameraHandler()
        encoder = FaceEncoder()
        register_new_person(camera, encoder)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()