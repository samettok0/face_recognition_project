#!/usr/bin/env python3
"""
Simple Face Recognition Lock Demo

This script demonstrates basic lock control functionality similar to your original
Raspberry Pi test script, but integrated with the face recognition system.

Usage:
    python simple_lock_demo.py
"""

import sys
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gpio_lock_controller import GPIOLockController

def lock_on():
    """Turn on the lock (unlock the door) - same as your original function"""
    controller = GPIOLockController()
    success = controller.unlock_door("Manual Control")
    if success:
        print("🔓 LOCK UNLOCKED - GPIO Pin 18 ON")
    return success

def lock_off():
    """Turn off the lock (lock the door) - same as your original function"""
    controller = GPIOLockController()
    success = controller.lock_door("Manual Control")
    if success:
        print("🔒 LOCK LOCKED - GPIO Pin 18 OFF")
    return success

def test_lock_cycle():
    """Test the lock by cycling it on and off - same as your original function"""
    print("Starting lock test cycle...")
    controller = GPIOLockController()
    
    for i in range(5):
        print(f"\n--- Cycle {i+1} ---")
        
        # Unlock
        controller.unlock_door("Test")
        time.sleep(2)
        
        # Lock
        controller.lock_door("Test cycle")
        time.sleep(2)
    
    controller.cleanup()
    print("\nLock test cycle completed!")

def manual_control():
    """Manual control of the lock - enhanced version of your original function"""
    print("\nManual Lock Control")
    print("Commands:")
    print("  'on' or 'unlock' - Turn lock on (unlock door)")
    print("  'off' or 'lock' - Turn lock off (lock door)")
    print("  'test' - Run automatic test cycle")
    print("  'status' - Check current lock status")
    print("  'face_auth' - Run face recognition authentication")
    print("  'quit' or 'q' - Exit")
    print()
    
    controller = GPIOLockController()
    
    try:
        while True:
            try:
                command = input("Enter command: ").lower().strip()
                
                if command in ['on', 'unlock']:
                    controller.unlock_door("Manual Control")
                elif command in ['off', 'lock']:
                    controller.lock_door("Manual command")
                elif command == 'test':
                    controller.test_lock_cycle(cycles=3, delay=2.0)
                elif command == 'status':
                    status = controller.get_lock_status()
                    print(f"Lock status: {status}")
                elif command == 'face_auth':
                    print("Starting face recognition authentication...")
                    print("This will run the full face recognition system.")
                    try:
                        from src.main import run_authenticate
                        run_authenticate(auto_lock_delay=5.0)
                    except Exception as e:
                        print(f"Face recognition failed: {e}")
                elif command in ['quit', 'q']:
                    break
                else:
                    print("Invalid command. Try 'on', 'off', 'test', 'status', 'face_auth', or 'quit'")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    finally:
        controller.cleanup()

def main():
    print("="*50)
    print("    FACE RECOGNITION LOCK DEMO")
    print("="*50)
    print("GPIO Pin 18 Control with Face Recognition Integration")
    print("This script controls a lock mechanism connected to GPIO pin 18")
    print("Plus integrates with the face recognition authentication system")
    print()
    
    try:
        # Initialize and show status
        controller = GPIOLockController()
        print(f"System Detection:")
        print(f"  - Running on Raspberry Pi: {controller.is_raspberry_pi}")
        print(f"  - GPIO Pin: {controller.gpio_pin}")
        print(f"  - Initial Status: {controller.get_lock_status()}")
        print()
        
        # Choose test mode
        print("Select test mode:")
        print("1. Automatic test cycle (like your original script)")
        print("2. Manual control (enhanced version)")
        print("3. Face recognition authentication with lock")
        print("4. Quick lock/unlock test")
        
        choice = input("Enter choice (1, 2, 3, or 4): ").strip()
        
        if choice == "1":
            test_lock_cycle()
        elif choice == "2":
            manual_control()
        elif choice == "3":
            print("\nStarting face recognition authentication...")
            print("Make sure you have registered users and are in front of the camera.")
            try:
                from src.main import run_authenticate
                run_authenticate(auto_lock_delay=10.0)
            except Exception as e:
                print(f"Face recognition authentication failed: {e}")
        elif choice == "4":
            print("\nQuick test:")
            print("Unlocking...")
            controller.unlock_door("Quick test")
            time.sleep(3)
            print("Locking...")
            controller.lock_door("Quick test")
        else:
            print("Invalid choice. Starting manual control...")
            manual_control()
            
    except Exception as e:
        print(f"Error initializing system: {e}")
        if "GPIO" in str(e):
            print("Make sure you're running on a Raspberry Pi with GPIO access")
        print("Note: The system will work in simulation mode on non-Raspberry Pi systems")
    
    finally:
        # Ensure lock is off when exiting (same as your original script)
        try:
            controller = GPIOLockController()
            controller.lock_door("Script exit")
            print("\nExiting... Lock set to LOCKED state")
        except:
            pass

if __name__ == "__main__":
    main() 