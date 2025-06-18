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
from .utils import logger, draw_recognition_feedback_on_frame, draw_enhanced_anti_spoofing_feedback, draw_authentication_status, validate_face_size_and_distance, calculate_face_quality_score
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
    """Run one-time authentication attempt with enhanced anti-spoofing"""
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
    
    # Initialize spoof detector and enhanced decision gate
    spoof_detector = AntiSpoofing()
    if use_anti_spoofing:
        spoof_detector.set_threshold(live_threshold)
    
    # Enhanced decision gate with quality checks
    min_quality = max(8, window - 7)  # Require at least 8 quality frames, or window-7
    gate = DecisionGate(window, min_live, min_match, min_quality)
    
    anti_spoof_msg = " with enhanced anti-spoofing" if use_anti_spoofing else ""
    print(f"Starting authentication{anti_spoof_msg}...")
    print(f"Using window={window}, min_live={min_live}, min_match={min_match}, min_quality={min_quality}")
    print("Looking for authorized user. Press 'q' to quit.")
    print("⚠️  Enhanced security: Face must be at proper distance and quality.")
    
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
            
            # Initialize quality check for any detected face
            is_quality = False
            is_match = False
            matched_name = "Unknown"
            
            # First, check quality for any detected face (not just recognized ones)
            if results:
                # Use the first detected face for quality validation
                bbox, name, confidence = results[0]
                
                # Enhanced face quality validation for any detected face
                if validate_face_size_and_distance(frame, bbox):
                    quality_score = calculate_face_quality_score(frame, bbox)
                    is_quality = quality_score > 0.6  # Require 60% quality score
                    
                    if not is_quality:
                        print(f"⚠️  Face quality too low ({quality_score:.2f}) - potential bypass attempt")
                    else:
                        print(f"✅ Face quality good ({quality_score:.2f})")
                else:
                    print(f"⚠️  Face distance/size validation failed - potential bypass attempt")
            
            # Now check for recognized faces
            for bbox, name, confidence in results:
                if name != "Unknown" and name in auth.authorized_users:
                    is_match = True
                    matched_name = name
                    print(f"MATCH! Recognized {name} with confidence {confidence:.2f}")
                    break
                else:
                    print(f"Found face: {name} with confidence {confidence:.2f}")
            
            # Check for liveness if anti-spoofing is enabled
            is_live = True  # Default to True if anti-spoofing not enabled
            if use_anti_spoofing:
                try:
                    is_live = spoof_detector.is_live(frame)
                    if not is_live:
                        print("⚠️  Anti-spoofing detected potential fake face")
                except Exception as e:
                    print(f"Anti-spoofing error: {e}")
                    is_live = True  # Fallback to True on error
            
            # Debug info
            print(f"Frame {frame_count}/{max_frames}: Match={is_match} ({matched_name}), Live={is_live}, Quality={is_quality}")
            
            # Update enhanced decision gate
            gate_result = gate.update(is_live, is_match, is_quality)
            status = gate.get_status()
            print(f"Gate status: {status['live']} live, {status['match']} match, {status['quality']} quality")
            
            if gate_result:
                print(f"✅ Authentication successful - {matched_name}")
                print("🎉 All security checks passed: liveness, recognition, and face quality")
                
                # Show success message in GUI for 3 seconds
                success_start_time = time.time()
                while time.time() - success_start_time < 3.0:
                    success_frame = camera.get_frame()
                    if success_frame is not None:
                        # Draw success message on frame
                        annotated_frame = draw_authentication_status(
                            success_frame, 
                            "AUTHENTICATION SUCCESSFUL", 
                            f"Welcome, {matched_name}!",
                            is_success=True
                        )
                        cv2.imshow("Authentication", annotated_frame)
                        
                        # Check for 'q' key to quit
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    
                    time.sleep(0.03)  # Small delay
                
                # Unlock the lock
                auth.unlock_lock(matched_name)
                
                # Exit the program on successful authentication
                print("Exiting application after successful authentication...")
                time.sleep(1)  # Brief pause before exit
                sys.exit(0)
            
            # Show feedback on frame
            try:
                # Use the enhanced anti-spoofing display function
                annotated_frame = draw_enhanced_anti_spoofing_feedback(frame, results, is_live)
                
                # Add frame counter and quality info
                cv2.putText(annotated_frame, f"Frame: {frame_count}/{max_frames}", (10, 60),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                # Add quality status
                quality_color = (0, 255, 0) if is_quality else (0, 0, 255)
                quality_text = "Quality: GOOD" if is_quality else "Quality: POOR"
                cv2.putText(annotated_frame, quality_text, (10, 90),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, quality_color, 2)
                
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
            print("💡 Tip: Ensure face is at proper distance (not too close or far)")
            
            # Show failure message in GUI for 3 seconds
            failure_start_time = time.time()
            while time.time() - failure_start_time < 3.0:
                failure_frame = camera.get_frame()
                if failure_frame is not None:
                    # Draw failure message on frame
                    annotated_frame = draw_authentication_status(
                        failure_frame, 
                        "AUTHENTICATION FAILED", 
                        f"Exceeded {max_frames} frames limit",
                        is_success=False
                    )
                    cv2.imshow("Authentication", annotated_frame)
                    
                    # Check for 'q' key to quit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                time.sleep(0.03)  # Small delay
                
        elif time.time() - start_time >= 60:
            print("❌ Authentication failed: Timeout reached")
            print("💡 Tip: Ensure face is at proper distance (not too close or far)")
            
            # Show timeout message in GUI for 3 seconds
            timeout_start_time = time.time()
            while time.time() - timeout_start_time < 3.0:
                timeout_frame = camera.get_frame()
                if timeout_frame is not None:
                    # Draw timeout message on frame
                    annotated_frame = draw_authentication_status(
                        timeout_frame, 
                        "AUTHENTICATION FAILED", 
                        "Timeout reached (60 seconds)",
                        is_success=False
                    )
                    cv2.imshow("Authentication", annotated_frame)
                    
                    # Check for 'q' key to quit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                time.sleep(0.03)  # Small delay
        else:
            print("❌ Authentication failed")
            print("💡 Tip: Ensure face is at proper distance (not too close or far)")
            
            # Show generic failure message in GUI for 3 seconds
            generic_failure_start_time = time.time()
            while time.time() - generic_failure_start_time < 3.0:
                generic_failure_frame = camera.get_frame()
                if generic_failure_frame is not None:
                    # Draw generic failure message on frame
                    annotated_frame = draw_authentication_status(
                        generic_failure_frame, 
                        "AUTHENTICATION FAILED", 
                        "No authorized user detected",
                        is_success=False
                    )
                    cv2.imshow("Authentication", annotated_frame)
                    
                    # Check for 'q' key to quit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                time.sleep(0.03)  # Small delay
    
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

def run_lock_test(cycles: int = 3):
    """Test the GPIO lock functionality"""
    from .gpio_lock import GPIOLock
    from .config import GPIO_LOCK_PIN, LOCK_UNLOCK_DURATION, GPIO_LOCK_ACTIVE_HIGH
    
    print("="*50)
    print("        GPIO LOCK TEST")
    print("="*50)
    print(f"Testing GPIO lock on pin {GPIO_LOCK_PIN}")
    print(f"Unlock duration: {LOCK_UNLOCK_DURATION} seconds")
    relay_type = "active HIGH" if GPIO_LOCK_ACTIVE_HIGH else "active LOW"
    print(f"Relay type: {relay_type}")
    print()
    
    # Initialize lock
    lock = GPIOLock(gpio_pin=GPIO_LOCK_PIN, unlock_duration=LOCK_UNLOCK_DURATION, active_high=GPIO_LOCK_ACTIVE_HIGH)
    
    try:
        # Show initial status
        print(f"Initial lock status: {lock.get_status()}")
        print()
        
        # Run test cycle
        success = lock.test_lock_cycle(cycles=cycles)
        
        if success:
            print("\n✅ Lock test completed successfully!")
        else:
            print("\n❌ Lock test failed!")
            
        # Test individual unlock
        print("\n--- Testing individual unlock ---")
        lock.unlock("TestUser")
        
        print(f"\nFinal lock status: {lock.get_status()}")
        
    except Exception as e:
        print(f"❌ Lock test error: {e}")
    finally:
        # Ensure cleanup
        lock.cleanup()
        print("\nLock test completed.")

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
    
    # Lock test command
    lock_test_parser = subparsers.add_parser("lock_test",
                                           help="Test the GPIO lock functionality")
    lock_test_parser.add_argument("--cycles", type=int, default=3,
                                help="Number of lock/unlock cycles to test (default: 3)")
    
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
        
    elif args.command == "lock_test":
        run_lock_test(cycles=args.cycles)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()