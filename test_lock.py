#!/usr/bin/env python3
"""
Standalone GPIO Lock Test Script

This script tests the GPIO lock functionality independently of the face recognition system.
It's useful for verifying that the lock mechanism works correctly before integrating
with the full authentication system.

Usage:
    python test_lock.py                    # Run basic test
    python test_lock.py --cycles 5         # Run 5 test cycles
    python test_lock.py --manual           # Manual control mode
"""

import time
import argparse
import sys
from pathlib import Path

# Add src directory to path so we can import our modules
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from gpio_lock import GPIOLock
    from config import GPIO_LOCK_PIN, LOCK_UNLOCK_DURATION
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def run_basic_test(cycles: int = 3):
    """Run basic lock test cycles"""
    print("="*50)
    print("        GPIO LOCK BASIC TEST")
    print("="*50)
    print(f"Testing GPIO lock on pin {GPIO_LOCK_PIN}")
    print(f"Unlock duration: {LOCK_UNLOCK_DURATION} seconds")
    print(f"Test cycles: {cycles}")
    print()
    
    # Initialize lock
    lock = GPIOLock(gpio_pin=GPIO_LOCK_PIN, unlock_duration=LOCK_UNLOCK_DURATION)
    
    try:
        # Show initial status
        print(f"Initial lock status: {lock.get_status()}")
        print()
        
        # Run test cycle
        success = lock.test_lock_cycle(cycles=cycles)
        
        if success:
            print("\n✅ Basic test completed successfully!")
        else:
            print("\n❌ Basic test failed!")
            
        # Test individual unlock with simulated user
        print("\n--- Testing authentication unlock ---")
        print("Simulating successful authentication for user 'TestUser'...")
        lock.unlock("TestUser")
        
        print(f"\nFinal lock status: {lock.get_status()}")
        
    except Exception as e:
        print(f"❌ Lock test error: {e}")
    finally:
        # Ensure cleanup
        lock.cleanup()
        print("\nBasic test completed.")

def run_manual_control():
    """Run manual control mode for interactive testing"""
    print("="*50)
    print("        GPIO LOCK MANUAL CONTROL")
    print("="*50)
    print(f"GPIO Pin: {GPIO_LOCK_PIN}")
    print(f"Unlock Duration: {LOCK_UNLOCK_DURATION} seconds")
    print()
    
    # Initialize lock
    lock = GPIOLock(gpio_pin=GPIO_LOCK_PIN, unlock_duration=LOCK_UNLOCK_DURATION)
    
    print("Manual Lock Control Commands:")
    print("  'unlock' or 'u' - Unlock the door")
    print("  'lock' or 'l' - Lock the door")
    print("  'status' or 's' - Check lock status")
    print("  'test' or 't' - Run test cycle")
    print("  'auth' or 'a' - Simulate authentication unlock")
    print("  'quit' or 'q' - Exit")
    print()
    
    try:
        while True:
            try:
                command = input("Enter command: ").lower().strip()
                
                if command in ['unlock', 'u']:
                    if lock.is_initialized and lock.lock_device:
                        lock.lock_device.on()
                        print("🔓 Manual unlock - Lock activated")
                    else:
                        print("🔓 Manual unlock (simulated)")
                        
                elif command in ['lock', 'l']:
                    success = lock.lock()
                    if success:
                        print("🔒 Manual lock completed")
                    else:
                        print("❌ Manual lock failed")
                        
                elif command in ['status', 's']:
                    status = lock.get_status()
                    print(f"Lock status: {status}")
                    
                elif command in ['test', 't']:
                    print("\nRunning test cycle...")
                    lock.test_lock_cycle(cycles=2)
                    
                elif command in ['auth', 'a']:
                    username = input("Enter username for authentication test: ").strip()
                    if not username:
                        username = "TestUser"
                    print(f"\nSimulating authentication for '{username}'...")
                    lock.unlock(username)
                    
                elif command in ['quit', 'q']:
                    break
                    
                else:
                    print("Invalid command. Try 'unlock', 'lock', 'status', 'test', 'auth', or 'quit'")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                
    finally:
        lock.cleanup()
        print("\nManual control session ended.")

def main():
    parser = argparse.ArgumentParser(description="GPIO Lock Test Script")
    parser.add_argument("--cycles", type=int, default=3,
                       help="Number of test cycles to run (default: 3)")
    parser.add_argument("--manual", action="store_true",
                       help="Run in manual control mode")
    parser.add_argument("--pin", type=int, default=None,
                       help="Override GPIO pin number (default: from config)")
    parser.add_argument("--duration", type=float, default=None,
                       help="Override unlock duration in seconds (default: from config)")
    
    args = parser.parse_args()
    
    # Override config values if specified
    if args.pin is not None:
        global GPIO_LOCK_PIN
        GPIO_LOCK_PIN = args.pin
        print(f"Using GPIO pin {GPIO_LOCK_PIN} (overridden)")
        
    if args.duration is not None:
        global LOCK_UNLOCK_DURATION
        LOCK_UNLOCK_DURATION = args.duration
        print(f"Using unlock duration {LOCK_UNLOCK_DURATION}s (overridden)")
    
    try:
        if args.manual:
            run_manual_control()
        else:
            run_basic_test(cycles=args.cycles)
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 