#!/usr/bin/env python3
"""
Simple Button Trigger for Face Recognition Authentication
Monitors a button on GPIO pin 16 and triggers authentication when pressed.
"""

import subprocess
import sys
import time
from gpiozero import Button
from signal import pause

# GPIO pin for the button
BUTTON_PIN = 16

# Security settings
DEBOUNCE_TIME = 0.5  # Minimum time between button presses (seconds)
COOLDOWN_TIME = 3.0  # Cooldown period after authentication (seconds)

# Global flags and timing
is_running_auth = False
last_press_time = 0
last_auth_end_time = 0

def run_authentication():
    """Run the face recognition authentication command"""
    global is_running_auth, last_auth_end_time
    
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
        last_auth_end_time = time.time()
        print(f"💡 Authentication finished. Cooldown period: {COOLDOWN_TIME}s")

def button_pressed():
    """Handle button press event with security protection"""
    global last_press_time
    current_time = time.time()
    
    # Check if we're in cooldown period after last authentication
    if current_time - last_auth_end_time < COOLDOWN_TIME:
        remaining_cooldown = COOLDOWN_TIME - (current_time - last_auth_end_time)
        print(f"⏱️ Cooldown active - please wait {remaining_cooldown:.1f} more seconds")
        return
    
    # Check if authentication is already running
    if is_running_auth:
        print("🚫 Authentication already running - button press ignored")
        return
    
    # Check debounce time (protection against rapid presses)
    if current_time - last_press_time < DEBOUNCE_TIME:
        print("🚫 Button press too fast - ignored (debounce protection)")
        return
    
    # Valid button press - start authentication
    last_press_time = current_time
    print(f"✅ Button pressed on GPIO {BUTTON_PIN} - starting authentication")
    run_authentication()

def main():
    """Main function"""
    print(f"🚀 Button trigger initialized on GPIO pin {BUTTON_PIN}")
    print("🔒 Security features enabled:")
    print(f"   - Button debouncing: {DEBOUNCE_TIME}s minimum between presses")
    print(f"   - Authentication cooldown: {COOLDOWN_TIME}s after each attempt")
    print("   - No queuing of multiple button presses")
    print("Press the button to start face recognition authentication...")
    print("Press Ctrl+C to exit")
    print("-" * 50)
    
    # Setup button with hardware debouncing
    button = Button(BUTTON_PIN, bounce_time=DEBOUNCE_TIME)
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