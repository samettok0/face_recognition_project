#!/usr/bin/env python3
"""
Face Recognition Lock Integration Test Script

This script demonstrates the integration of GPIO lock control with face recognition.
It provides various test modes to verify the system functionality.

Usage:
    python test_lock_integration.py [test_mode]

Test modes:
    1. lock_only    - Test just the GPIO lock functionality
    2. simulation   - Test face recognition with simulated lock
    3. full         - Test complete integration (requires Raspberry Pi)
    4. manual       - Manual control interface
"""

import sys
import time
import argparse
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gpio_lock_controller import GPIOLockController
from src.biometric_auth import BiometricAuth
from src.config import TRAINING_DIR

def test_lock_only():
    """Test only the GPIO lock functionality"""
    print("="*60)
    print("        GPIO LOCK FUNCTIONALITY TEST")
    print("="*60)
    
    controller = GPIOLockController()
    
    try:
        print(f"🔍 System Detection:")
        print(f"   - Running on Raspberry Pi: {controller.is_raspberry_pi}")
        print(f"   - GPIO Pin: {controller.gpio_pin}")
        print(f"   - Initial Status: {controller.get_lock_status()}")
        
        print(f"\n🧪 Testing Basic Operations:")
        
        # Test unlock
        print("\n1. Testing UNLOCK operation:")
        success = controller.unlock_door("Test User")
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
        print(f"   Status: {controller.get_lock_status()}")
        time.sleep(2)
        
        # Test lock
        print("\n2. Testing LOCK operation:")
        success = controller.lock_door("Test completed")
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
        print(f"   Status: {controller.get_lock_status()}")
        time.sleep(1)
        
        # Test cycle
        print("\n3. Testing CYCLE operations:")
        controller.test_lock_cycle(cycles=2, delay=1.0)
        
        # Test auto-lock
        print("\n4. Testing AUTO-LOCK feature:")
        controller.unlock_door("Auto-lock test")
        print("   Waiting 3 seconds for auto-lock...")
        controller.auto_lock_after_delay(3.0)
        
        print(f"\n✅ All tests completed successfully!")
        print(f"Final status: {controller.get_lock_status()}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
    finally:
        controller.cleanup()

def test_face_recognition_simulation():
    """Test face recognition with simulated responses"""
    print("="*60)
    print("    FACE RECOGNITION + LOCK SIMULATION TEST")
    print("="*60)
    
    # Check if we have trained users
    if not TRAINING_DIR.exists() or not any(TRAINING_DIR.iterdir()):
        print("❌ No trained users found!")
        print(f"Please train some users first using:")
        print(f"   python -m src.main register")
        print(f"   python -m src.main train")
        return
    
    print("🔍 Found trained users:")
    for person_dir in TRAINING_DIR.iterdir():
        if person_dir.is_dir():
            print(f"   - {person_dir.name}")
    
    # Initialize BiometricAuth with short auto-lock for demo
    auth = BiometricAuth(
        recognition_threshold=0.55,
        auto_lock_delay=5.0  # Short delay for demo
    )
    
    # Add authorized users
    for person_dir in TRAINING_DIR.iterdir():
        if person_dir.is_dir():
            auth.add_authorized_user(person_dir.name)
    
    print(f"\n🔒 Initial lock status: {auth.get_lock_status()}")
    
    try:
        # Simulate authentication scenarios
        print("\n🧪 Simulating authentication scenarios:")
        
        print("\n1. Simulating successful authentication:")
        user_list = list(auth.authorized_users)
        if user_list:
            test_user = user_list[0]
            print(f"   Simulating recognition of: {test_user}")
            success = auth.unlock_door(test_user)
            print(f"   Unlock result: {'✅ Success' if success else '❌ Failed'}")
            print(f"   Status: {auth.get_lock_status()}")
            print(f"   Auto-lock will trigger in {auth.auto_lock_delay} seconds...")
            
            # Wait and show auto-lock
            time.sleep(auth.auto_lock_delay + 1)
            print(f"   Status after auto-lock: {auth.get_lock_status()}")
        
        print("\n2. Testing manual lock:")
        auth.unlock_door("Manual test")
        time.sleep(1)
        auth.lock_door("Manual lock test")
        print(f"   Status: {auth.get_lock_status()}")
        
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
    finally:
        auth.lock_controller.cleanup()

def test_full_integration():
    """Test the complete face recognition + lock integration"""
    print("="*60)
    print("      FULL INTEGRATION TEST")
    print("="*60)
    print("This will run actual face recognition with lock control.")
    print("Make sure you're in front of the camera and are a registered user.")
    print("Press Ctrl+C to stop at any time.")
    
    try:
        from src.main import run_authenticate
        print("\nStarting authentication with 5-second auto-lock...")
        run_authenticate(
            model="hog",
            use_anti_spoofing=False,
            auto_lock_delay=5.0
        )
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Integration test failed: {e}")

def manual_control():
    """Manual control interface"""
    print("="*60)
    print("         MANUAL LOCK CONTROL")
    print("="*60)
    
    from src.gpio_lock_controller import manual_lock_control
    manual_lock_control()

def main():
    parser = argparse.ArgumentParser(
        description="Face Recognition Lock Integration Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Modes:
  lock_only     Test only GPIO lock functionality
  simulation    Test face recognition with simulated lock responses
  full          Test complete integration (requires camera and registered users)
  manual        Manual lock control interface

Examples:
  python test_lock_integration.py lock_only
  python test_lock_integration.py simulation
  python test_lock_integration.py full
  python test_lock_integration.py manual
        """
    )
    
    parser.add_argument(
        "test_mode",
        choices=["lock_only", "simulation", "full", "manual"],
        nargs="?",
        default="lock_only",
        help="Test mode to run (default: lock_only)"
    )
    
    args = parser.parse_args()
    
    print("🔐 Face Recognition Lock Integration Test")
    print(f"Running test mode: {args.test_mode}")
    print("-" * 60)
    
    try:
        if args.test_mode == "lock_only":
            test_lock_only()
        elif args.test_mode == "simulation":
            test_face_recognition_simulation()
        elif args.test_mode == "full":
            test_full_integration()
        elif args.test_mode == "manual":
            manual_control()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted. Ensuring lock is secured...")
        # Emergency lock
        try:
            controller = GPIOLockController()
            controller.lock_door("Emergency stop")
            controller.cleanup()
        except:
            pass
    except Exception as e:
        print(f"\n❌ Test failed with unexpected error: {e}")
    
    print("\n🏁 Test completed.")

if __name__ == "__main__":
    main() 