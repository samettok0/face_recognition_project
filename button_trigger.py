#!/usr/bin/env python3
"""
Button Trigger for Face Recognition Authentication
This script monitors a button on GPIO pin 16 and triggers
face recognition authentication when pressed.
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from gpiozero import Button
from signal import pause

class FaceRecognitionButtonTrigger:
    def __init__(self, gpio_pin=16):
        """
        Initialize the button trigger system
        
        Args:
            gpio_pin (int): GPIO pin number for the button (default: 16)
        """
        self.gpio_pin = gpio_pin
        self.button = Button(gpio_pin)
        self.is_running_auth = False
        self.setup_button_events()
        print(f"Button trigger initialized on GPIO pin {gpio_pin}")
        print("Press the button to start face recognition authentication...")
        
    def setup_button_events(self):
        """Setup button event handlers"""
        self.button.when_pressed = self.on_button_pressed
        self.button.when_released = self.on_button_released
        
    def on_button_pressed(self):
        """Handle button press event"""
        print(f"Button pressed on GPIO {self.gpio_pin}")
        if not self.is_running_auth:
            self.start_authentication()
        else:
            print("Authentication is already running, please wait...")
            
    def on_button_released(self):
        """Handle button release event"""
        print(f"Button released on GPIO {self.gpio_pin}")
        
    def start_authentication(self):
        """Start the face recognition authentication process"""
        try:
            self.is_running_auth = True
            print("🔄 Starting face recognition authentication with anti-spoofing...")
            
            # Get the current working directory to ensure proper module execution
            current_dir = Path(__file__).parent.absolute()
            
            # Command to execute
            cmd = [sys.executable, "-m", "src.main", "auth", "--anti-spoofing"]
            
            print(f"Executing command: {' '.join(cmd)}")
            print(f"Working directory: {current_dir}")
            
            # Execute the authentication command
            result = subprocess.run(
                cmd,
                cwd=current_dir,
                capture_output=False,  # Allow real-time output
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                print("✅ Authentication command completed successfully")
            else:
                print(f"❌ Authentication command failed with return code: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            print("⏱️ Authentication command timed out after 2 minutes")
        except KeyboardInterrupt:
            print("\n🛑 Authentication interrupted by user")
        except Exception as e:
            print(f"❌ Error running authentication command: {e}")
        finally:
            self.is_running_auth = False
            print("💡 Ready for next button press...")
            
    def cleanup(self):
        """Cleanup GPIO resources"""
        print("Cleaning up GPIO resources...")
        self.button.close()
        
    def run(self):
        """Main run loop"""
        try:
            print("🚀 Face Recognition Button Trigger is running")
            print("Press Ctrl+C to exit")
            print("-" * 50)
            
            # Keep the program running and wait for button presses
            pause()
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down button trigger...")
        finally:
            self.cleanup()

def main():
    """Main function"""
    # Check if we're running on a system with GPIO support
    try:
        from gpiozero import Device
        # Test if we can access GPIO
        Device.ensure_pin_factory()
        print("✅ GPIO support detected")
    except Exception as e:
        print(f"❌ GPIO support not available: {e}")
        print("This script requires a Raspberry Pi or compatible GPIO-enabled device")
        sys.exit(1)
    
    # Check if the src module exists
    if not Path("src").exists():
        print("❌ Error: 'src' directory not found in current directory")
        print("Please run this script from the face_recognition_project root directory")
        sys.exit(1)
    
    # Initialize and run the button trigger
    trigger = FaceRecognitionButtonTrigger(gpio_pin=16)
    trigger.run()

if __name__ == "__main__":
    main() 