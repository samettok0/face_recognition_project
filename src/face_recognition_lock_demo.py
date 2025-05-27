#!/usr/bin/env python3
"""
Face Recognition Lock Demo Script
Combines face recognition authentication with GPIO lock control
Uses gpiozero library for Pi 5 compatibility
"""

import time
import sys
import argparse
from pathlib import Path

# Add the src directory to the path for imports
sys.path.append(str(Path(__file__).parent))

from gpio_lock_controller import get_lock_controller, unlock_for_user
from biometric_auth import BiometricAuth
from face_encoder import FaceEncoder
from camera_handler import CameraHandler
from config import TRAINING_DIR
from utils import logger

def test_lock_only():
    """Test just the lock functionality without face recognition"""
    print("="*60)
    print("           LOCK TESTING SCRIPT")
    print("="*60)
    print("GPIO Pin 14 Control Test")
    print("This script controls a lock mechanism connected to GPIO pin 14")
    print()
    
    controller = get_lock_controller()
    
    try:
        # Initial state
        controller.lock_door()
        print("Lock initialized in LOCKED state")
        print()
        
        # Choose test mode
        print("Select test mode:")
        print("1. Automatic test cycle")
        print("2. Manual control")
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            cycles = int(input("Number of cycles (default 3): ") or "3")
            duration = float(input("Duration per state in seconds (default 2.0): ") or "2.0")
            controller.test_lock_cycle(cycles=cycles, cycle_duration=duration)
        elif choice == "2":
            manual_lock_control(controller)
        else:
            print("Invalid choice. Starting manual control...")
            manual_lock_control(controller)
            
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Lock test error: {e}")
    
    finally:
        # Ensure lock is in locked state when exiting
        controller.cleanup()
        print("\nExiting... Lock set to LOCKED state")

def manual_lock_control(controller):
    """Manual control of the lock"""
    print("\nManual Lock Control")
    print("Commands:")
    print("  'unlock' or 'on' - Unlock door temporarily (5 seconds)")
    print("  'unlock <seconds>' - Unlock door for specific duration")
    print("  'lock' or 'off' - Lock door immediately")
    print("  'test' - Run automatic test cycle")
    print("  'status' - Check current lock status")
    print("  'quit' or 'q' - Exit")
    print()
    
    while True:
        try:
            command = input("Enter command: ").lower().strip()
            
            if command in ['unlock', 'on']:
                controller.unlock_temporary(5.0)
            elif command.startswith('unlock '):
                try:
                    duration = float(command.split()[1])
                    controller.unlock_temporary(duration)
                except (IndexError, ValueError):
                    print("Invalid duration. Use: unlock <seconds>")
            elif command in ['lock', 'off']:
                controller.lock_door()
            elif command == 'test':
                controller.test_lock_cycle(cycles=3, cycle_duration=2.0)
            elif command == 'status':
                status = controller.get_status()
                print(f"Lock status: {status}")
            elif command in ['quit', 'q']:
                break
            else:
                print("Invalid command. Try 'unlock', 'lock', 'test', 'status', or 'quit'")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def test_face_recognition_with_lock():
    """Test face recognition authentication with lock control"""
    print("="*60)
    print("      FACE RECOGNITION LOCK DEMO")
    print("="*60)
    print("Combining face recognition with GPIO lock control")
    print("Authorized users will unlock the door for 5 seconds")
    print()
    
    # Initialize lock controller
    lock_controller = get_lock_controller()
    
    # Set initial state to locked
    lock_controller.lock_door()
    print("Lock initialized in LOCKED state")
    print()
    
    # Initialize biometric authentication
    auth = BiometricAuth(
        recognition_threshold=0.55,
        consecutive_matches_required=2,  # Reduced for demo
        model="hog",  # Faster for demo
        use_anti_spoofing=False  # Disabled for simpler demo
    )
    
    # Add all users from training directory as authorized
    training_dir = TRAINING_DIR
    authorized_count = 0
    if training_dir.exists():
        for person_dir in training_dir.iterdir():
            if person_dir.is_dir():
                auth.add_authorized_user(person_dir.name)
                authorized_count += 1
                print(f"✓ Authorized user: {person_dir.name}")
    
    if authorized_count == 0:
        print("❌ No authorized users found!")
        print(f"Please register users first using: python -m src.main register")
        print(f"Training directory: {training_dir}")
        return
    
    print(f"\n✓ {authorized_count} authorized user(s) loaded")
    print("\n🔍 Starting face recognition...")
    print("Look at the camera to authenticate and unlock the door")
    print("Press 'q' to quit")
    print()
    
    try:
        # Start authentication loop
        camera = CameraHandler()
        if not camera.start():
            print("❌ Failed to start camera")
            return
        
        consecutive_matches = {}
        start_time = time.time()
        frame_count = 0
        max_runtime = 120  # 2 minutes max
        
        while time.time() - start_time < max_runtime:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Process frame for facial recognition
            try:
                results = auth.recognizer.recognize_face_in_frame(frame)
            except Exception as e:
                print(f"Recognition error: {e}")
                results = []
            
            # Check for authorized users
            authenticated_user = None
            for bbox, name, confidence in results:
                if name != "Unknown" and name in auth.authorized_users:
                    # Track consecutive matches
                    consecutive_matches[name] = consecutive_matches.get(name, 0) + 1
                    
                    print(f"👤 Recognized: {name} (confidence: {confidence:.2f}) "
                          f"- Match {consecutive_matches[name]}/{auth.consecutive_matches_required}")
                    
                    # Check if we have enough consecutive matches
                    if consecutive_matches[name] >= auth.consecutive_matches_required:
                        authenticated_user = name
                        break
                else:
                    # Reset consecutive matches for other users
                    for other_name in list(consecutive_matches.keys()):
                        if other_name != name:
                            consecutive_matches[other_name] = 0
            
            # Handle successful authentication
            if authenticated_user:
                print(f"\n✅ AUTHENTICATION SUCCESSFUL!")
                print(f"👤 Welcome, {authenticated_user}!")
                
                # Unlock the door
                print("🔓 Unlocking door...")
                success = unlock_for_user(authenticated_user, duration=5.0)
                
                if success:
                    print("✅ Door unlocked successfully!")
                    print("⏰ Door will lock automatically in 5 seconds...")
                else:
                    print("❌ Failed to unlock door")
                
                # Reset and continue
                consecutive_matches = {}
                time.sleep(6)  # Wait for lock cycle to complete
                print("\n🔍 Continuing to monitor for authorized users...")
            
            # Show basic status every 30 frames
            if frame_count % 30 == 0:
                print(f"🔍 Monitoring... (Frame {frame_count}, {len(results)} faces detected)")
            
            # Check for quit
            if frame_count % 10 == 0:  # Check less frequently to avoid blocking
                try:
                    import cv2
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                except:
                    pass
            
            time.sleep(0.05)  # Small delay
        
        print("\n⏰ Session timeout reached")
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during face recognition: {e}")
        logger.error(f"Face recognition demo error: {e}")
    finally:
        try:
            camera.stop()
        except:
            pass
        
        # Ensure door is locked
        lock_controller.lock_door()
        print("🔒 Door locked for security")

def continuous_monitoring_mode():
    """Run continuous monitoring with automatic lock control"""
    print("="*60)
    print("    CONTINUOUS MONITORING MODE")
    print("="*60)
    print("Door will automatically unlock for authorized users")
    print("and lock again after 5 seconds")
    print()
    
    # Initialize lock controller
    lock_controller = get_lock_controller()
    lock_controller.lock_door()
    
    # Custom success handler that controls the lock
    def on_auth_success(username: str):
        print(f"\n🎉 Access granted to {username}!")
        unlock_for_user(username, duration=5.0)
        print("⏰ Door will lock automatically in 5 seconds...")
        time.sleep(6)  # Wait for lock cycle
        print("🔍 Resuming monitoring...")
    
    # Initialize and run continuous monitoring
    auth = BiometricAuth(
        recognition_threshold=0.55,
        consecutive_matches_required=2,
        model="hog",
        use_anti_spoofing=False
    )
    
    # Add authorized users
    training_dir = TRAINING_DIR
    if training_dir.exists():
        for person_dir in training_dir.iterdir():
            if person_dir.is_dir():
                auth.add_authorized_user(person_dir.name)
                print(f"✓ Authorized user: {person_dir.name}")
    
    print("\n🔍 Starting continuous monitoring...")
    print("Press 'q' to quit")
    
    try:
        auth.run_continuous_monitoring(on_success=on_auth_success)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")
    finally:
        lock_controller.lock_door()
        print("🔒 Door locked for security")

def main():
    parser = argparse.ArgumentParser(description="Face Recognition Lock Demo")
    parser.add_argument("mode", choices=["lock-test", "face-auth", "continuous"], 
                       help="Demo mode to run")
    parser.add_argument("--pin", type=int, default=14,
                       help="GPIO pin for lock control (default: 14)")
    
    args = parser.parse_args()
    
    print(f"🔧 Using GPIO pin {args.pin} for lock control")
    
    # Initialize lock controller with specified pin
    get_lock_controller(pin=args.pin, unlock_duration=5.0)
    
    try:
        if args.mode == "lock-test":
            test_lock_only()
        elif args.mode == "face-auth":
            test_face_recognition_with_lock()
        elif args.mode == "continuous":
            continuous_monitoring_mode()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        logger.error(f"Demo error: {e}")
    finally:
        # Ensure cleanup
        controller = get_lock_controller()
        controller.cleanup()

if __name__ == "__main__":
    main() 