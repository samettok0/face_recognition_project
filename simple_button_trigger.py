#!/usr/bin/env python3
"""
Simple Button Trigger for Face Recognition Authentication
Monitors a button on GPIO pin 16 and triggers authentication when pressed.
"""

import subprocess
import sys
from gpiozero import Button
from signal import pause

# GPIO pin for the button
BUTTON_PIN = 16

# Global flag to prevent multiple simultaneous authentications
is_running_auth = False

def run_authentication():
    """Run the face recognition authentication command"""
    global is_running_auth
    
    if is_running_auth:
        print("Authentication is already running, please wait...")
        return
    
    try:
        is_running_auth = True
        print("🔄 Starting face recognition authentication with anti-spoofing...")
        
        # Execute the authentication command
        result = subprocess.run(
            [sys.executable, "-m", "src.main", "auth", "--anti-spoofing"],
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode == 0:
            print("✅ Authentication completed successfully")
        else:
            print(f"❌ Authentication failed with return code: {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("⏱️ Authentication timed out after 2 minutes")
    except Exception as e:
        print(f"❌ Error running authentication: {e}")
    finally:
        is_running_auth = False
        print("💡 Ready for next button press...")

def button_pressed():
    """Handle button press event"""
    print(f"Button pressed on GPIO {BUTTON_PIN}!")
    run_authentication()

def main():
    """Main function"""
    print(f"🚀 Button trigger initialized on GPIO pin {BUTTON_PIN}")
    print("Press the button to start face recognition authentication...")
    print("Press Ctrl+C to exit")
    print("-" * 50)
    
    # Setup button
    button = Button(BUTTON_PIN)
    button.when_pressed = button_pressed
    
    try:
        # Keep the program running
        pause()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down button trigger...")
    finally:
        button.close()

if __name__ == "__main__":
    main() 