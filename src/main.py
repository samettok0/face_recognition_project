#!/usr/bin/env python3
import argparse
import cv2
import numpy as np
import sys
import os
import time
from pathlib import Path

from .face_encoder import FaceEncoder
from .biometric_auth import BiometricAuth
from .camera_handler import CameraHandler
from .head_pose_detector import HeadPoseDetector
from .head_pose_demo import run_head_pose_demo
from .guided_registration import register_user_guided
from .anti_spoofing import AntiSpoofing
from .decision_gate import DecisionGate
from .utils import logger, draw_recognition_feedback_on_frame
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

def run_authenticate(model: str = "hog", use_anti_spoofing: bool = False, 
                   window: int = 15, min_live: int = 12, min_match: int = 12,
                   live_threshold: float = 0.9):
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
                print(f"Authorized user: {person_dir.name}")
    
    # Initialize spoof detector and decision gate
    spoof_detector = AntiSpoofing()
    if use_anti_spoofing:
        spoof_detector.set_threshold(live_threshold)
    
    gate = DecisionGate(window, min_live, min_match)
    
    anti_spoof_msg = " with anti-spoofing" if use_anti_spoofing else ""
    print(f"Starting authentication{anti_spoof_msg}...")
    print(f"Using window={window}, min_live={min_live}, min_match={min_match}")
    print("Looking for authorized user. Press 'q' to quit.")
    
    # Start camera
    camera = CameraHandler()
    if not camera.start():
        print("Failed to start camera")
        return
    
    try:
        start_time = time.time()
        matched_name = "Unknown"  # Fix: Initialize matched_name
        max_frames = 120  # Maximum frames to process (about 4 seconds with default timing)
        frame_count = 0
        
        # Get initial camera frame to check format
        initial_frame = camera.get_frame()
        if initial_frame is not None:
            print(f"Camera frame info - Shape: {initial_frame.shape}, Type: {initial_frame.dtype}")
        else:
            print("WARNING: Could not get initial frame from camera")
        
        while time.time() - start_time < 60 and frame_count < max_frames:  # 1 minute timeout or max frames
            frame = camera.get_frame()
            if frame is None:
                print("Warning: Camera returned None frame, retrying...")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Process frame for facial recognition
            try:
                results = auth.recognizer.recognize_face_in_frame(frame)
                
                # If we have no results but no error was thrown, debug the image
                if not results and frame_count % 30 == 0:  # Debug every 30 frames
                    print(f"No faces detected in frame {frame_count}. Frame shape: {frame.shape}, dtype: {frame.dtype}")
            except Exception as e:
                print(f"Error during face recognition: {e}")
                results = []
            
            # Check if any recognized face belongs to authorized user
            is_match = False
            for bbox, name, confidence in results:
                if name != "Unknown" and name in auth.authorized_users:
                    is_match = True
                    matched_name = name  # Fix: Save matched name
                    print(f"MATCH! Recognized {name} with confidence {confidence:.2f}")
                    break
                else:
                    print(f"Found face: {name} with confidence {confidence:.2f}")
            
            # Check for liveness if anti-spoofing is enabled
            is_live = True  # Default to True if anti-spoofing not enabled
            if use_anti_spoofing:
                try:
                    is_live = spoof_detector.is_live(frame)
                except Exception as e:
                    print(f"Anti-spoofing error: {e}")
                    is_live = True  # Fallback to True on error
            
            # Debug info
            print(f"Frame {frame_count}/{max_frames}: Match={is_match} ({matched_name}), Live={is_live}")
            
            # Update decision gate
            gate_result = gate.update(is_live, is_match)
            print(f"Gate status: {sum(gate.live_q)}/{len(gate.live_q)} live, {sum(gate.match_q)}/{len(gate.match_q)} match")
            
            if gate_result:
                print(f"✅ Authentication successful - {matched_name}")
                auth.unlock_lock(matched_name)
                # Exit the program on successful authentication
                print("Exiting application after successful authentication...")
                time.sleep(2)  # Allow time to see the success message
                sys.exit(0)
            
            # Show feedback on frame
            try:
                annotated_frame = draw_recognition_feedback_on_frame(frame, results)
                # Use actual values not symbols for clarity
                status_text = f"Match: {is_match}, Live: {is_live}"
                cv2.putText(annotated_frame, status_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if is_live and is_match else (0, 0, 255), 2)
                
                # Add frame counter
                cv2.putText(annotated_frame, f"Frame: {frame_count}/{max_frames}", (10, 60),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                cv2.imshow("Authentication", annotated_frame)
            except Exception as e:
                print(f"Error displaying frame: {e}")
                # Still show original frame as fallback
                try:
                    cv2.imshow("Authentication", frame)
                except:
                    pass
            
            # Check for 'q' key to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("User quit the application.")
                break
                
            time.sleep(0.03)  # Small delay between frames
        
        # If we got here, authentication was not successful
        if frame_count >= max_frames:
            print("❌ Authentication failed: Maximum attempts reached")
        elif time.time() - start_time >= 60:
            print("❌ Authentication failed: Timeout reached")
        else:
            print("❌ Authentication failed")
    
    finally:
        camera.stop()
        cv2.destroyAllWindows()

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
    auth_parser.add_argument("--window", type=int, default=15,
                           help="Number of recent frames to keep for decision gate")
    auth_parser.add_argument("--min-live", type=int, default=12,
                           help="Minimum number of frames that must pass liveness check")
    auth_parser.add_argument("--min-match", type=int, default=12,
                           help="Minimum number of frames that must match an authorized user")
    auth_parser.add_argument("--live-threshold", type=float, default=0.9,
                           help="Threshold for liveness detection (0.0-1.0)")
    
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
        run_authenticate(model=args.model, use_anti_spoofing=args.anti_spoofing,
                        window=args.window, min_live=args.min_live, min_match=args.min_match,
                        live_threshold=args.live_threshold)
        
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