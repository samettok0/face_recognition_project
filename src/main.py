#!/usr/bin/env python3
import argparse
import cv2
import numpy as np
import sys
import os
import time
import signal
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
from .gpio_lock_controller import GPIOLockController

# Global variable to store the auth instance for cleanup
auth_instance = None

def signal_handler(signum, frame):
    """Handle Ctrl+C and cleanup GPIO resources"""
    global auth_instance
    print("\n🛑 Interrupted! Cleaning up and securing lock...")
    if auth_instance:
        try:
            auth_instance.lock_door("Emergency shutdown")
            auth_instance.lock_controller.cleanup()
        except:
            pass
    sys.exit(0)

# Set up signal handler for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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
                   live_threshold: float = 0.9, auto_lock_delay: float = 10.0):
    """Run one-time authentication attempt"""
    global auth_instance
    
    auth = BiometricAuth(
        recognition_threshold=0.55, 
        model=model,
        use_anti_spoofing=use_anti_spoofing,
        auto_lock_delay=auto_lock_delay
    )
    auth_instance = auth  # Store for cleanup
    
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
    print(f"Auto-lock delay: {auto_lock_delay} seconds")
    print(f"Initial lock status: {auth.get_lock_status()}")
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
                auth.unlock_door(matched_name)
                print(f"🔓 Door unlocked! Will auto-lock in {auto_lock_delay} seconds")
                print("Exiting application after successful authentication...")
                time.sleep(2)  # Allow time to see the success message
                sys.exit(0)
            
            # Show feedback on frame
            try:
                annotated_frame = draw_recognition_feedback_on_frame(frame, results)
                
                # Create a semi-transparent overlay for text background
                overlay = annotated_frame.copy()
                cv2.rectangle(overlay, (0, 0), (300, 70), (0, 0, 0), -1)
                # Apply the overlay with transparency
                alpha = 0.5
                cv2.addWeighted(overlay, alpha, annotated_frame, 1 - alpha, 0, annotated_frame)
                
                # Different display based on whether faces are detected
                if not results:
                    # No faces detected - show only that message
                    cv2.putText(annotated_frame, "No faces detected", (10, 30),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                else:
                    # Faces detected - show match and live status
                    match_text = f"Match: {is_match}"
                    live_text = f"Live: {is_live}"
                    
                    # Determine status color
                    match_color = (0, 255, 0) if is_match else (0, 0, 255)
                    live_color = (0, 255, 0) if is_live else (0, 0, 255)
                    
                    # Add status texts with separate positioning
                    cv2.putText(annotated_frame, match_text, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, match_color, 2)
                    cv2.putText(annotated_frame, live_text, (160, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, live_color, 2)
                
                # Always show frame counter on a different line
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
        # Ensure lock is secured before exit
        try:
            auth.lock_door("Application exit")
            auth.lock_controller.cleanup()
        except:
            pass
        camera.stop()
        cv2.destroyAllWindows()

def run_continuous_monitoring(model: str = "hog", use_anti_spoofing: bool = False, 
                            auto_lock_delay: float = 10.0):
    """Run continuous monitoring and authentication"""
    global auth_instance
    
    auth = BiometricAuth(
        recognition_threshold=0.55,
        consecutive_matches_required=3,
        model=model,
        use_anti_spoofing=use_anti_spoofing,
        auto_lock_delay=auto_lock_delay
    )
    auth_instance = auth  # Store for cleanup
    
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

def test_lock_system():
    """Test the GPIO lock system"""
    print("="*50)
    print("        LOCK SYSTEM TEST")
    print("="*50)
    
    controller = GPIOLockController()
    
    try:
        print(f"Initial lock status: {controller.get_lock_status()}")
        print("Testing lock system functionality...")
        
        # Test basic operations
        print("\n1. Testing basic lock/unlock operations:")
        controller.test_lock_cycle(cycles=2, delay=1.5)
        
        print("\n2. Testing auto-lock feature:")
        controller.unlock_door("Auto-lock test")
        print("   Waiting 3 seconds for auto-lock...")
        controller.auto_lock_after_delay(3.0)
        
        print(f"\nFinal lock status: {controller.get_lock_status()}")
        print("✅ Lock system test completed successfully!")
        
    except Exception as e:
        print(f"❌ Lock system test failed: {e}")
    finally:
        controller.cleanup()

def manual_lock_control():
    """Manual lock control interface"""
    from .gpio_lock_controller import manual_lock_control
    manual_lock_control()

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
    auth_parser.add_argument("--auto-lock-delay", type=float, default=10.0,
                           help="Seconds to wait before auto-locking after successful authentication")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", 
                                        help="Run continuous monitoring for authorized faces")
    monitor_parser.add_argument("--model", choices=["hog", "cnn"], default="hog",
                              help="Face detection model to use (hog is faster, cnn is more accurate)")
    monitor_parser.add_argument("--anti-spoofing", action="store_true",
                              help="Enable anti-spoofing detection to prevent fake face attacks")
    monitor_parser.add_argument("--auto-lock-delay", type=float, default=10.0,
                              help="Seconds to wait before auto-locking after successful authentication")
    
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
    
    # Lock testing command
    test_lock_parser = subparsers.add_parser("test_lock",
                                           help="Test the GPIO lock system functionality")
    
    # Manual lock control command
    manual_lock_parser = subparsers.add_parser("manual_lock",
                                             help="Manual lock control interface")
    
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
                        live_threshold=args.live_threshold, auto_lock_delay=args.auto_lock_delay)
        
    elif args.command == "monitor":
        run_continuous_monitoring(model=args.model, use_anti_spoofing=args.anti_spoofing,
                                auto_lock_delay=args.auto_lock_delay)
        
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
        
    elif args.command == "test_lock":
        test_lock_system()
        
    elif args.command == "manual_lock":
        manual_lock_control()
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()