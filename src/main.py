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
from .head_pose_detector import HeadPoseDetector
from .head_pose_demo import run_head_pose_demo
from .guided_registration import register_user_guided
from .anti_spoofing import AntiSpoofing
from .utils import logger
from .config import TRAINING_DIR

def register_new_person(camera_handler, face_encoder):
    """Register a new person by taking their photos and training the model"""
    name = input("Enter the person's name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return False
    
    # Number of training images to capture
    try:
        num_images = int(input("How many photos to capture (default: 10): ") or "10")
    except ValueError:
        num_images = 10
    
    # Use the centralized method in FaceEncoder
    success = face_encoder.register_person_from_camera(camera_handler, name, num_images)
    
    if success:
        print(f"Successfully registered {name} and trained the model.")
        return True
    else:
        print("Registration failed or was cancelled.")
        return False

def run_authenticate(model: str = "hog", use_anti_spoofing: bool = False):
    """Run one-time authentication attempt"""
    auth = BiometricAuth(
        recognition_threshold=0.55, 
        model=model,
        use_anti_spoofing=use_anti_spoofing
    )
    
    # Add all users from training directory as authorized
    training_dir = TRAINING_DIR
    if training_dir.exists():
        for person_dir in training_dir.iterdir():
            if person_dir.is_dir():
                auth.add_authorized_user(person_dir.name)
    
    anti_spoof_msg = " with anti-spoofing" if use_anti_spoofing else ""
    print(f"Starting authentication{anti_spoof_msg}...")
    print("Looking for authorized user. Press 'q' to quit.")
    
    success, username = auth.authenticate(max_attempts=30, timeout=20)
    
    if success:
        print(f"✅ Authentication successful: {username}")
    else:
        print("❌ Authentication failed")

def run_continuous_monitoring(model: str = "hog", use_anti_spoofing: bool = False):
    """Run continuous monitoring and authentication"""
    auth = BiometricAuth(
        recognition_threshold=0.55,  # Adjust based on your needs
        consecutive_matches_required=3,  # How many frames must match
        model=model,
        use_anti_spoofing=use_anti_spoofing
    )
    
    # Add all users from training directory as authorized
    training_dir = TRAINING_DIR
    if training_dir.exists():
        for person_dir in training_dir.iterdir():
            if person_dir.is_dir():
                auth.add_authorized_user(person_dir.name)
                print(f"Authorized user: {person_dir.name}")
    
    anti_spoof_msg = " with anti-spoofing" if use_anti_spoofing else ""
    print(f"Starting continuous monitoring{anti_spoof_msg}...")
    print("Looking for authorized users. Press 'q' to quit.")
    
    auth.run_continuous_monitoring()

def run_anti_spoofing_demo(camera_index: int = 0):
    """Run the anti-spoofing demo to detect fake vs real faces"""
    print("Starting anti-spoofing demonstration...")
    print("This will detect if a face is real or fake.")
    print("Press 'q' to quit.")
    
    spoof_detector = AntiSpoofing()
    spoof_detector.run_demo(camera_index=camera_index)

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
    auth_parser.add_argument("--model", choices=["hog", "cnn"], default="hog",
                           help="Face detection model to use (hog is faster, cnn is more accurate)")
    auth_parser.add_argument("--anti-spoofing", action="store_true",
                           help="Enable anti-spoofing detection to prevent fake face attacks")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", 
                                        help="Run continuous monitoring for authorized faces")
    monitor_parser.add_argument("--model", choices=["hog", "cnn"], default="hog",
                              help="Face detection model to use (hog is faster, cnn is more accurate)")
    monitor_parser.add_argument("--anti-spoofing", action="store_true",
                              help="Enable anti-spoofing detection to prevent fake face attacks")
    
    # Regular Register command
    register_parser = subparsers.add_parser("register", 
                                         help="Register a new person by taking their photos")
    
    # Guided Register command with head pose detection
    guided_register_parser = subparsers.add_parser("guided-register", 
                                               help="Register a new person with guided head pose detection")
    
    # Head pose demo command
    head_pose_parser = subparsers.add_parser("head_pose", 
                                         help="Run head pose detection demo")
                                         
    # Anti-spoofing demo command
    anti_spoof_parser = subparsers.add_parser("anti_spoof",
                                          help="Run anti-spoofing detection demo")
    anti_spoof_parser.add_argument("--camera", type=int, default=0,
                                help="Camera index to use (default: 0)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "train":
        print("Training face recognition model...")
        encoder = FaceEncoder(model=args.model)
        encoder.encode_known_faces()
        print("Training complete!")
        
    elif args.command == "auth":
        run_authenticate(model=args.model, use_anti_spoofing=args.anti_spoofing)
        
    elif args.command == "monitor":
        run_continuous_monitoring(model=args.model, use_anti_spoofing=args.anti_spoofing)
        
    elif args.command == "register":
        camera = CameraHandler()
        encoder = FaceEncoder()
        register_new_person(camera, encoder)
        
    elif args.command == "guided-register":
        register_user_guided()
        
    elif args.command == "head_pose":
        run_head_pose_demo()
        
    elif args.command == "anti_spoof":
        run_anti_spoofing_demo(camera_index=args.camera)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()