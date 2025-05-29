#!/usr/bin/env python3
"""
Button Trigger for Face Recognition Authentication
This script monitors a button on GPIO pin 16 and triggers
face recognition authentication when pressed.
Includes buzzer feedback on GPIO pin 26.
"""

import subprocess
import sys
import os
import time
import threading
from pathlib import Path
from gpiozero import Button, Buzzer
from signal import pause

class FaceRecognitionButtonTrigger:
    def __init__(self, gpio_pin=16, buzzer_pin=26, debounce_time=0.5, cooldown_time=3.0):
        """
        Initialize the button trigger system
        
        Args:
            gpio_pin (int): GPIO pin number for the button (default: 16)
            buzzer_pin (int): GPIO pin number for the buzzer (default: 26)
            debounce_time (float): Minimum time between button presses in seconds (default: 0.5)
            cooldown_time (float): Cooldown period after authentication in seconds (default: 3.0)
        """
        self.gpio_pin = gpio_pin
        self.buzzer_pin = buzzer_pin
        self.debounce_time = debounce_time
        self.cooldown_time = cooldown_time
        self.button = Button(gpio_pin, bounce_time=debounce_time)
        self.buzzer = Buzzer(buzzer_pin)
        self.is_running_auth = False
        self.last_press_time = 0
        self.last_auth_end_time = 0
        self.setup_button_events()
        
        # Welcome buzzer pattern
        self.buzzer_startup()
        
        print(f"Button trigger initialized on GPIO pin {gpio_pin}")
        print(f"Buzzer initialized on GPIO pin {buzzer_pin}")
        print(f"Debounce time: {debounce_time}s, Cooldown time: {cooldown_time}s")
        print("Press the button to start face recognition authentication...")
        
    def buzzer_startup(self):
        """Play startup buzzer pattern"""
        def startup_pattern():
            self.buzzer.on()
            time.sleep(0.1)
            self.buzzer.off()
            time.sleep(0.1)
            self.buzzer.on()
            time.sleep(0.1)
            self.buzzer.off()
        
        threading.Thread(target=startup_pattern, daemon=True).start()
        
    def buzzer_button_press(self):
        """Play button press confirmation beep"""
        def beep():
            self.buzzer.on()
            time.sleep(0.05)
            self.buzzer.off()
        
        threading.Thread(target=beep, daemon=True).start()
        
    def buzzer_auth_start(self):
        """Play authentication start pattern"""
        def auth_start_pattern():
            for _ in range(3):
                self.buzzer.on()
                time.sleep(0.1)
                self.buzzer.off()
                time.sleep(0.1)
        
        threading.Thread(target=auth_start_pattern, daemon=True).start()
        
    def buzzer_auth_success(self):
        """Play authentication success pattern"""
        def success_pattern():
            # Two long beeps for success
            self.buzzer.on()
            time.sleep(0.3)
            self.buzzer.off()
            time.sleep(0.2)
            self.buzzer.on()
            time.sleep(0.3)
            self.buzzer.off()
        
        threading.Thread(target=success_pattern, daemon=True).start()
        
    def buzzer_auth_failure(self):
        """Play authentication failure pattern"""
        def failure_pattern():
            # Rapid beeps for failure
            for _ in range(5):
                self.buzzer.on()
                time.sleep(0.1)
                self.buzzer.off()
                time.sleep(0.1)
        
        threading.Thread(target=failure_pattern, daemon=True).start()
        
    def buzzer_no_face_detected(self):
        """Play no face detected pattern - single long beep"""
        def no_face_pattern():
            self.buzzer.on()
            time.sleep(0.4)
            self.buzzer.off()
        
        threading.Thread(target=no_face_pattern, daemon=True).start()
        
    def buzzer_camera_error(self):
        """Play camera error pattern - alternating beeps"""
        def camera_error_pattern():
            for _ in range(3):
                self.buzzer.on()
                time.sleep(0.2)
                self.buzzer.off()
                time.sleep(0.3)
                self.buzzer.on()
                time.sleep(0.1)
                self.buzzer.off()
                time.sleep(0.2)
        
        threading.Thread(target=camera_error_pattern, daemon=True).start()
        
    def buzzer_user_cancelled(self):
        """Play user cancelled pattern - descending beeps"""
        def cancelled_pattern():
            self.buzzer.on()
            time.sleep(0.15)
            self.buzzer.off()
            time.sleep(0.1)
            self.buzzer.on()
            time.sleep(0.1)
            self.buzzer.off()
            time.sleep(0.1)
            self.buzzer.on()
            time.sleep(0.05)
            self.buzzer.off()
        
        threading.Thread(target=cancelled_pattern, daemon=True).start()
        
    def buzzer_cooldown_warning(self):
        """Play cooldown warning beep"""
        def warning_beep():
            self.buzzer.on()
            time.sleep(0.2)
            self.buzzer.off()
        
        threading.Thread(target=warning_beep, daemon=True).start()
        
    def buzzer_error(self):
        """Play error pattern"""
        def error_pattern():
            # Long error tone
            self.buzzer.on()
            time.sleep(0.5)
            self.buzzer.off()
            time.sleep(0.2)
            self.buzzer.on()
            time.sleep(0.5)
            self.buzzer.off()
        
        threading.Thread(target=error_pattern, daemon=True).start()
        
    def setup_button_events(self):
        """Setup button event handlers"""
        self.button.when_pressed = self.on_button_pressed
        
    def on_button_pressed(self):
        """Handle button press event with debouncing and cooldown protection"""
        current_time = time.time()
        
        # Check if we're in cooldown period after last authentication
        if current_time - self.last_auth_end_time < self.cooldown_time:
            remaining_cooldown = self.cooldown_time - (current_time - self.last_auth_end_time)
            print(f"⏱️ Cooldown active - please wait {remaining_cooldown:.1f} more seconds")
            self.buzzer_cooldown_warning()
            return
        
        # Check if authentication is already running
        if self.is_running_auth:
            print("🚫 Authentication already running - button press ignored")
            self.buzzer_cooldown_warning()
            return
            
        # Check debounce time (additional protection against rapid presses)
        if current_time - self.last_press_time < self.debounce_time:
            print("🚫 Button press too fast - ignored (debounce protection)")
            return
        
        # Valid button press - start authentication
        self.last_press_time = current_time
        print(f"✅ Button pressed on GPIO {self.gpio_pin} - starting authentication")
        self.buzzer_button_press()
        self.start_authentication()
        
    def start_authentication(self):
        """Start the face recognition authentication process"""
        try:
            self.is_running_auth = True
            print("🔄 Starting face recognition authentication with anti-spoofing...")
            self.buzzer_auth_start()
            
            # Get the current working directory to ensure proper module execution
            current_dir = Path(__file__).parent.absolute()
            
            # Command to execute
            cmd = [sys.executable, "-m", "src.main", "auth", "--anti-spoofing"]
            
            print(f"Executing command: {' '.join(cmd)}")
            print(f"Working directory: {current_dir}")
            
            # Execute the authentication command with output capture
            result = subprocess.run(
                cmd,
                cwd=current_dir,
                capture_output=True,  # Capture output to analyze results
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            # Print the output in real-time style
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
                    self.buzzer_auth_success()
                elif "Failed to start camera" in output_text:
                    print("📷 Camera failed to start")
                    self.buzzer_camera_error()
                elif "Authentication failed: Maximum attempts reached" in output_text:
                    print("⏱️ No face detected - Maximum attempts reached")
                    self.buzzer_no_face_detected()
                elif "Authentication failed: Timeout reached" in output_text:
                    print("⏱️ No face detected - Timeout reached")
                    self.buzzer_no_face_detected()
                elif "Authentication failed" in output_text:
                    print("❌ Authentication failed - No face detected")
                    self.buzzer_no_face_detected()
                elif "User quit the application" in output_text:
                    print("🛑 Authentication cancelled by user")
                    self.buzzer_user_cancelled()
                else:
                    # Fallback - if we can't determine, assume no face detected
                    print("❓ Authentication completed - No face detected")
                    self.buzzer_no_face_detected()
            else:
                print(f"❌ Authentication command failed with return code: {result.returncode}")
                self.buzzer_auth_failure()
                
        except subprocess.TimeoutExpired:
            print("⏱️ Authentication command timed out after 2 minutes")
            self.buzzer_auth_failure()
        except KeyboardInterrupt:
            print("\n🛑 Authentication interrupted by user")
        except Exception as e:
            print(f"❌ Error running authentication command: {e}")
            self.buzzer_error()
        finally:
            self.is_running_auth = False
            self.last_auth_end_time = time.time()
            print(f"💡 Authentication finished. Cooldown period: {self.cooldown_time}s")
            
    def cleanup(self):
        """Cleanup GPIO resources"""
        print("Cleaning up GPIO resources...")
        # Shutdown buzzer pattern
        try:
            for _ in range(2):
                self.buzzer.on()
                time.sleep(0.1)
                self.buzzer.off()
                time.sleep(0.1)
        except:
            pass
        
        self.button.close()
        self.buzzer.close()
        
    def run(self):
        """Main run loop"""
        try:
            print("🚀 Face Recognition Button Trigger is running")
            print("🔒 Security features enabled:")
            print(f"   - Button debouncing: {self.debounce_time}s minimum between presses")
            print(f"   - Authentication cooldown: {self.cooldown_time}s after each attempt")
            print("   - No queuing of multiple button presses")
            print("🔊 Buzzer feedback enabled:")
            print("   - Button press: Short beep")
            print("   - Auth start: 3 beeps")
            print("   - Auth success: 2 long beeps")
            print("   - Auth failure: 5 rapid beeps")
            print("   - No face detected: 1 long beep")
            print("   - Camera error: Alternating beeps")
            print("   - User cancelled: Descending beeps")
            print("   - Cooldown warning: Single beep")
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
    
    # Initialize and run the button trigger with security features and buzzer
    # You can adjust these values for your security requirements:
    # - gpio_pin: Button GPIO pin (default: 16)
    # - buzzer_pin: Buzzer GPIO pin (default: 26) 
    # - debounce_time: Minimum time between button presses (default: 0.5s)
    # - cooldown_time: Cooldown after authentication attempt (default: 3.0s)
    trigger = FaceRecognitionButtonTrigger(
        gpio_pin=16,
        buzzer_pin=26,
        debounce_time=0.5,  # 500ms between button presses
        cooldown_time=3.0   # 3 second cooldown after each auth
    )
    trigger.run()

if __name__ == "__main__":
    main() 