#!/usr/bin/env python3
"""
Simple Button Trigger for Face Recognition Authentication
Monitors a button on GPIO pin 16 and triggers authentication when pressed.
Includes buzzer feedback on GPIO pin 26.
"""

import subprocess
import sys
import time
import threading
from gpiozero import Button, Buzzer
from signal import pause

# GPIO pins
BUTTON_PIN = 16
BUZZER_PIN = 26

# Security settings
DEBOUNCE_TIME = 0.5  # Minimum time between button presses (seconds)
COOLDOWN_TIME = 3.0  # Cooldown period after authentication (seconds)

# Global flags and timing
is_running_auth = False
last_press_time = 0
last_auth_end_time = 0

# Initialize buzzer
buzzer = Buzzer(BUZZER_PIN)

def buzzer_beep(duration=0.1, count=1, interval=0.1):
    """Simple buzzer function with threading"""
    def beep_pattern():
        for _ in range(count):
            buzzer.on()
            time.sleep(duration)
            buzzer.off()
            if count > 1:
                time.sleep(interval)
    
    threading.Thread(target=beep_pattern, daemon=True).start()

def buzzer_startup():
    """Startup beeps"""
    buzzer_beep(duration=0.1, count=2, interval=0.1)

def buzzer_button_press():
    """Quick button press confirmation"""
    buzzer_beep(duration=0.05, count=1)

def buzzer_auth_start():
    """Authentication starting"""
    buzzer_beep(duration=0.1, count=3, interval=0.1)

def buzzer_auth_success():
    """Authentication success - two long beeps"""
    def success_pattern():
        buzzer.on()
        time.sleep(0.3)
        buzzer.off()
        time.sleep(0.2)
        buzzer.on()
        time.sleep(0.3)
        buzzer.off()
    
    threading.Thread(target=success_pattern, daemon=True).start()

def buzzer_auth_failure():
    """Authentication failure - rapid beeps"""
    buzzer_beep(duration=0.1, count=5, interval=0.1)

def buzzer_no_face_detected():
    """No face detected - single long beep"""
    buzzer_beep(duration=0.4, count=1)

def buzzer_camera_error():
    """Camera error - alternating pattern"""
    def camera_error_pattern():
        for _ in range(3):
            buzzer.on()
            time.sleep(0.2)
            buzzer.off()
            time.sleep(0.3)
            buzzer.on()
            time.sleep(0.1)
            buzzer.off()
            time.sleep(0.2)
    
    threading.Thread(target=camera_error_pattern, daemon=True).start()

def buzzer_user_cancelled():
    """User cancelled - descending beeps"""
    def cancelled_pattern():
        buzzer.on()
        time.sleep(0.15)
        buzzer.off()
        time.sleep(0.1)
        buzzer.on()
        time.sleep(0.1)
        buzzer.off()
        time.sleep(0.1)
        buzzer.on()
        time.sleep(0.05)
        buzzer.off()
    
    threading.Thread(target=cancelled_pattern, daemon=True).start()

def buzzer_cooldown_warning():
    """Cooldown warning"""
    buzzer_beep(duration=0.2, count=1)

def run_authentication():
    """Run the face recognition authentication command"""
    global is_running_auth, last_auth_end_time
    
    try:
        is_running_auth = True
        print("🔄 Starting face recognition authentication with anti-spoofing...")
        buzzer_auth_start()
        
        # Execute the authentication command with output capture
        result = subprocess.run(
            [sys.executable, "-m", "src.main", "auth", "--anti-spoofing"],
            capture_output=True,  # Capture output to analyze results
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Analyze the output to determine the actual result
        output_text = result.stdout + result.stderr
        
        if result.returncode == 0:
            # Check what actually happened based on output
            if "✅ Authentication successful" in output_text:
                print("🎉 Authentication successful - Face recognized!")
                buzzer_auth_success()
            elif "Failed to start camera" in output_text:
                print("📷 Camera failed to start")
                buzzer_camera_error()
            elif "Authentication failed: Maximum attempts reached" in output_text:
                print("⏱️ No face detected - Maximum attempts reached")
                buzzer_no_face_detected()
            elif "Authentication failed: Timeout reached" in output_text:
                print("⏱️ No face detected - Timeout reached")
                buzzer_no_face_detected()
            elif "Authentication failed" in output_text:
                print("❌ Authentication failed - No face detected")
                buzzer_no_face_detected()
            elif "User quit the application" in output_text:
                print("🛑 Authentication cancelled by user")
                buzzer_user_cancelled()
            else:
                # Fallback - if we can't determine, assume no face detected
                print("❓ Authentication completed - No face detected")
                buzzer_no_face_detected()
        else:
            print(f"❌ Authentication command failed with return code: {result.returncode}")
            buzzer_auth_failure()
            
    except subprocess.TimeoutExpired:
        print("⏱️ Authentication timed out after 2 minutes")
        buzzer_auth_failure()
    except Exception as e:
        print(f"❌ Error running authentication: {e}")
        buzzer_auth_failure()
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
        buzzer_cooldown_warning()
        return
    
    # Check if authentication is already running
    if is_running_auth:
        print("🚫 Authentication already running - button press ignored")
        buzzer_cooldown_warning()
        return
    
    # Check debounce time (protection against rapid presses)
    if current_time - last_press_time < DEBOUNCE_TIME:
        print("🚫 Button press too fast - ignored (debounce protection)")
        return
    
    # Valid button press - start authentication
    last_press_time = current_time
    print(f"✅ Button pressed on GPIO {BUTTON_PIN} - starting authentication")
    buzzer_button_press()
    run_authentication()

def main():
    """Main function"""
    # Startup buzzer
    buzzer_startup()
    
    print(f"🚀 Button trigger initialized on GPIO pin {BUTTON_PIN}")
    print(f"🔊 Buzzer initialized on GPIO pin {BUZZER_PIN}")
    print("🔒 Security features enabled:")
    print(f"   - Button debouncing: {DEBOUNCE_TIME}s minimum between presses")
    print(f"   - Authentication cooldown: {COOLDOWN_TIME}s after each attempt")
    print("   - No queuing of multiple button presses")
    print("🔊 Buzzer feedback:")
    print("   - Button press: Quick beep")
    print("   - Auth start: 3 beeps")
    print("   - Auth success: 2 long beeps")
    print("   - Auth failure: 5 rapid beeps")
    print("   - No face detected: 1 long beep")
    print("   - Camera error: Alternating beeps")
    print("   - User cancelled: Descending beeps")
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
        # Shutdown buzzer pattern
        try:
            buzzer_beep(duration=0.1, count=2, interval=0.1)
            time.sleep(0.5)  # Wait for buzzer to finish
        except:
            pass
    finally:
        button.close()
        buzzer.close()

if __name__ == "__main__":
    main() 