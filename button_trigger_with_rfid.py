#!/usr/bin/env python3
"""
Button Trigger for Face Recognition Authentication with RFID Backup
This script monitors a button on GPIO pin 16 and triggers face recognition.
If face recognition fails, it activates RFID backup authentication.
Includes buzzer feedback on GPIO pin 26.
"""

import subprocess
import sys
import os
import time
import threading
import json
from pathlib import Path
from gpiozero import Button, Buzzer
from signal import pause
import keyboard
import queue
import select

# Import GPIO lock functionality
try:
    sys.path.append(str(Path(__file__).parent / "src"))
    from src.gpio_lock import GPIOLock
    from src.config import GPIO_LOCK_PIN, LOCK_UNLOCK_DURATION, ENABLE_GPIO_LOCK, GPIO_LOCK_ACTIVE_HIGH
    LOCK_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import lock modules: {e}")
    print("RFID unlock will be simulated only.")
    LOCK_AVAILABLE = False

class FaceRecognitionButtonTrigger:
    def __init__(self, gpio_pin=16, buzzer_pin=26, debounce_time=0.5, cooldown_time=3.0):
        """
        Initialize the button trigger system with RFID backup
        
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
        self.rfid_backup_active = False
        self.last_press_time = 0
        self.last_auth_end_time = 0
        
        # Initialize GPIO lock for RFID unlock
        if LOCK_AVAILABLE and ENABLE_GPIO_LOCK:
            self.gpio_lock = GPIOLock(gpio_pin=GPIO_LOCK_PIN, unlock_duration=LOCK_UNLOCK_DURATION, active_high=GPIO_LOCK_ACTIVE_HIGH)
            print(f"🔒 GPIO Lock initialized for RFID backup on pin {GPIO_LOCK_PIN}")
        else:
            self.gpio_lock = None
            if LOCK_AVAILABLE:
                print("⚠️  GPIO lock disabled in configuration - RFID unlock will be simulated")
            else:
                print("⚠️  GPIO lock not available - RFID unlock will be simulated")
        
        # RFID settings
        self.rfid_timeout = 30  # 30 seconds to scan RFID after face auth fails
        self.rfid_input_buffer = ""
        self.rfid_input_queue = queue.Queue()
        
        # Load authorized RFID cards
        self.authorized_rfid_cards = self.load_authorized_rfid_cards()
        
        self.setup_button_events()
        self.setup_rfid_monitoring()
        
        # Welcome buzzer pattern
        self.buzzer_startup()
        
        print(f"Button trigger initialized on GPIO pin {gpio_pin}")
        print(f"Buzzer initialized on GPIO pin {buzzer_pin}")
        print(f"RFID backup system initialized")
        print(f"Authorized RFID cards: {len(self.authorized_rfid_cards)}")
        if self.gpio_lock:
            lock_type = "active HIGH" if GPIO_LOCK_ACTIVE_HIGH else "active LOW"
            print(f"🔒 Physical lock control enabled on GPIO pin {GPIO_LOCK_PIN} ({lock_type})")
            print(f"🔒 Lock unlock duration: {LOCK_UNLOCK_DURATION} seconds")
        else:
            print("🔒 Physical lock control: DISABLED (simulation mode)")
        print(f"Debounce time: {debounce_time}s, Cooldown time: {cooldown_time}s")
        print("Press the button to start face recognition authentication...")
        
    def load_authorized_rfid_cards(self):
        """Load authorized RFID cards from file"""
        rfid_file = Path("authorized_rfid_cards.json")
        if rfid_file.exists():
            try:
                with open(rfid_file, 'r') as f:
                    cards = json.load(f)
                    return cards
            except Exception as e:
                print(f"Error loading RFID cards: {e}")
        
        # Default cards - add your card numbers here
        default_cards = {
            "1234567890": "Admin Card",
            "0987654321": "Backup Card",
            # Add your actual RFID card numbers here
        }
        
        # Save default cards
        self.save_authorized_rfid_cards(default_cards)
        return default_cards
    
    def save_authorized_rfid_cards(self, cards):
        """Save authorized RFID cards to file"""
        rfid_file = Path("authorized_rfid_cards.json")
        try:
            with open(rfid_file, 'w') as f:
                json.dump(cards, f, indent=2)
        except Exception as e:
            print(f"Error saving RFID cards: {e}")
    
    def add_rfid_card(self, card_id, card_name):
        """Add a new authorized RFID card"""
        self.authorized_rfid_cards[card_id] = card_name
        self.save_authorized_rfid_cards(self.authorized_rfid_cards)
        print(f"Added RFID card: {card_id} ({card_name})")
    
    def setup_rfid_monitoring(self):
        """Setup RFID input monitoring"""
        def rfid_input_thread():
            """Monitor for RFID input in a separate thread"""
            current_input = ""
            
            while True:
                try:
                    # Monitor stdin for RFID input (acts like keyboard)
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        char = sys.stdin.read(1)
                        
                        if char.isdigit():
                            current_input += char
                            # RFID reader sends 10 digits
                            if len(current_input) == 10:
                                self.rfid_input_queue.put(current_input)
                                current_input = ""
                        elif char in ['\n', '\r']:
                            # End of RFID input
                            if len(current_input) >= 8:  # Minimum valid length
                                self.rfid_input_queue.put(current_input)
                            current_input = ""
                        elif not char.isprintable():
                            # Reset on non-printable characters
                            current_input = ""
                            
                    time.sleep(0.01)
                except:
                    time.sleep(0.1)
        
        # Start RFID monitoring thread
        rfid_thread = threading.Thread(target=rfid_input_thread, daemon=True)
        rfid_thread.start()
    
    def process_rfid_input(self):
        """Process RFID input from queue"""
        while not self.rfid_input_queue.empty():
            try:
                rfid_data = self.rfid_input_queue.get_nowait()
                self.handle_rfid_scan(rfid_data)
            except queue.Empty:
                break
    
    def handle_rfid_scan(self, rfid_data):
        """Handle RFID card scan"""
        print(f"🏷️ RFID card detected: {rfid_data}")
        self.buzzer_rfid_detected()
        
        if not self.rfid_backup_active:
            print("🚫 RFID backup not active - complete face authentication first")
            self.buzzer_rfid_not_allowed()
            return
        
        # Check if card is authorized
        if rfid_data in self.authorized_rfid_cards:
            card_name = self.authorized_rfid_cards[rfid_data]
            print(f"✅ RFID Authentication successful - {card_name}")
            self.buzzer_rfid_success()
            self.unlock_via_rfid(card_name)
        else:
            print("❌ RFID card not authorized")
            self.buzzer_rfid_unauthorized()
    
    def unlock_via_rfid(self, card_name):
        """Unlock using RFID authentication"""
        print(f"🔓 Unlocking via RFID - {card_name}")
        
        try:
            if self.gpio_lock:
                # Use physical GPIO lock - same as face recognition system
                success = self.gpio_lock.unlock(card_name)
                if success:
                    print("🎉 Lock opened via RFID backup authentication!")
                else:
                    print("❌ Failed to unlock via RFID - lock operation failed")
                    self.buzzer_camera_error()  # Use error buzzer pattern
            else:
                # Fallback to simulation if GPIO lock is not available
                print("🔓 SIMULATED RFID UNLOCK: Access granted")
                print(f"   (Would unlock for {LOCK_UNLOCK_DURATION if LOCK_AVAILABLE else 5.0} seconds)")
                # Simulate the unlock duration
                time.sleep(LOCK_UNLOCK_DURATION if LOCK_AVAILABLE else 5.0)
                print("🔒 Simulated lock secured again")
                print("🎉 Simulated lock opened via RFID backup authentication!")
                
        except Exception as e:
            print(f"❌ Error during RFID unlock operation: {e}")
            self.buzzer_camera_error()
        
        # Reset states
        self.rfid_backup_active = False
        self.last_auth_end_time = time.time()
    
    def unlock_via_face_recognition(self):
        """Unlock using face recognition authentication"""
        print("🔓 Unlocking via face recognition")
        
        try:
            if self.gpio_lock:
                # Use physical GPIO lock - same as RFID system
                success = self.gpio_lock.unlock("Face Recognition")
                if success:
                    print("🎉 Lock opened via face recognition authentication!")
                else:
                    print("❌ Failed to unlock via face recognition - lock operation failed")
                    self.buzzer_camera_error()  # Use error buzzer pattern
            else:
                # Fallback to simulation if GPIO lock is not available
                print("🔓 SIMULATED FACE UNLOCK: Access granted")
                print(f"   (Would unlock for {LOCK_UNLOCK_DURATION if LOCK_AVAILABLE else 5.0} seconds)")
                # Simulate the unlock duration
                time.sleep(LOCK_UNLOCK_DURATION if LOCK_AVAILABLE else 5.0)
                print("🔒 Simulated lock secured again")
                print("🎉 Simulated lock opened via face recognition authentication!")
                
        except Exception as e:
            print(f"❌ Error during face recognition unlock operation: {e}")
            self.buzzer_camera_error()
        
        # Set auth end time for cooldown
        self.last_auth_end_time = time.time()
    
    def activate_rfid_backup(self):
        """Activate RFID backup mode after face auth failure"""
        self.rfid_backup_active = True
        print("🏷️ RFID backup activated - scan your card within 30 seconds")
        self.buzzer_rfid_backup_activated()
        
        # Start timeout timer
        def rfid_timeout():
            time.sleep(self.rfid_timeout)
            if self.rfid_backup_active:
                self.rfid_backup_active = False
                print("⏱️ RFID backup timeout - please try again")
                self.buzzer_rfid_timeout()
        
        threading.Thread(target=rfid_timeout, daemon=True).start()
    
    # Buzzer patterns
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
        
    def buzzer_no_face_detected(self):
        """Play no face detected pattern - single long beep"""
        def no_face_pattern():
            self.buzzer.on()
            time.sleep(0.4)
            self.buzzer.off()
        
        threading.Thread(target=no_face_pattern, daemon=True).start()
        
    def buzzer_rfid_backup_activated(self):
        """RFID backup mode activated"""
        def rfid_activate_pattern():
            for _ in range(2):
                self.buzzer.on()
                time.sleep(0.15)
                self.buzzer.off()
                time.sleep(0.1)
            time.sleep(0.2)
            self.buzzer.on()
            time.sleep(0.2)
            self.buzzer.off()
        
        threading.Thread(target=rfid_activate_pattern, daemon=True).start()
        
    def buzzer_rfid_detected(self):
        """RFID card detected"""
        def rfid_detected_pattern():
            self.buzzer.on()
            time.sleep(0.08)
            self.buzzer.off()
            time.sleep(0.05)
            self.buzzer.on()
            time.sleep(0.08)
            self.buzzer.off()
        
        threading.Thread(target=rfid_detected_pattern, daemon=True).start()
        
    def buzzer_rfid_success(self):
        """RFID authentication successful"""
        def rfid_success_pattern():
            for _ in range(3):
                self.buzzer.on()
                time.sleep(0.1)
                self.buzzer.off()
                time.sleep(0.1)
            time.sleep(0.1)
            self.buzzer.on()
            time.sleep(0.4)
            self.buzzer.off()
        
        threading.Thread(target=rfid_success_pattern, daemon=True).start()
        
    def buzzer_rfid_unauthorized(self):
        """RFID card not authorized"""
        def rfid_unauth_pattern():
            for _ in range(4):
                self.buzzer.on()
                time.sleep(0.05)
                self.buzzer.off()
                time.sleep(0.05)
        
        threading.Thread(target=rfid_unauth_pattern, daemon=True).start()
        
    def buzzer_rfid_not_allowed(self):
        """RFID not allowed at this time"""
        def not_allowed_pattern():
            self.buzzer.on()
            time.sleep(0.2)
            self.buzzer.off()
            time.sleep(0.1)
            self.buzzer.on()
            time.sleep(0.1)
            self.buzzer.off()
        
        threading.Thread(target=not_allowed_pattern, daemon=True).start()
        
    def buzzer_rfid_timeout(self):
        """RFID backup timeout"""
        def timeout_pattern():
            for _ in range(3):
                self.buzzer.on()
                time.sleep(0.2)
                self.buzzer.off()
                time.sleep(0.2)
        
        threading.Thread(target=timeout_pattern, daemon=True).start()
        
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
        
    def buzzer_cooldown_warning(self):
        """Play cooldown warning beep"""
        def warning_beep():
            self.buzzer.on()
            time.sleep(0.2)
            self.buzzer.off()
        
        threading.Thread(target=warning_beep, daemon=True).start()
        
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
            self.rfid_backup_active = False  # Reset RFID backup
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
                    print("🎉 Face recognition successful!")
                    self.buzzer_auth_success()
                    # Unlock the lock for successful face authentication
                    self.unlock_via_face_recognition()
                else:
                    # Face recognition failed - activate RFID backup
                    if "Failed to start camera" in output_text:
                        print("📷 Camera failed - activating RFID backup")
                    elif "Authentication failed: Maximum attempts reached" in output_text:
                        print("⏱️ No face detected - activating RFID backup")
                    elif "Authentication failed: Timeout reached" in output_text:
                        print("⏱️ Timeout reached - activating RFID backup")
                    else:
                        print("❌ Face authentication failed - activating RFID backup")
                    
                    self.buzzer_no_face_detected()
                    time.sleep(1)  # Brief pause
                    self.activate_rfid_backup()
            else:
                print(f"❌ Authentication command failed with return code: {result.returncode}")
                print("🏷️ Activating RFID backup due to system error")
                self.activate_rfid_backup()
                
        except subprocess.TimeoutExpired:
            print("⏱️ Authentication command timed out after 2 minutes")
            print("🏷️ Activating RFID backup due to timeout")
            self.activate_rfid_backup()
        except KeyboardInterrupt:
            print("\n🛑 Authentication interrupted by user")
        except Exception as e:
            print(f"❌ Error running authentication command: {e}")
            print("🏷️ Activating RFID backup due to error")
            self.activate_rfid_backup()
        finally:
            self.is_running_auth = False
            if not self.rfid_backup_active:
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
        
        # Clean up GPIO lock
        if self.gpio_lock:
            self.gpio_lock.cleanup()
            print("🔒 GPIO lock cleanup completed")
        
    def run(self):
        """Main run loop"""
        try:
            print("🚀 Face Recognition + RFID Backup System Running")
            print("🔒 Security features enabled:")
            print(f"   - Button debouncing: {self.debounce_time}s minimum between presses")
            print(f"   - Authentication cooldown: {self.cooldown_time}s after each attempt")
            print("   - No queuing of multiple button presses")
            if self.gpio_lock:
                lock_type = "active HIGH" if GPIO_LOCK_ACTIVE_HIGH else "active LOW"
                print(f"🔒 Physical lock control: GPIO pin {GPIO_LOCK_PIN} ({lock_type}), {LOCK_UNLOCK_DURATION}s unlock duration")
            else:
                print("🔒 Physical lock control: DISABLED (simulation mode)")
            print("🔊 Buzzer feedback enabled:")
            print("   - Button press: Short beep")
            print("   - Auth start: 3 beeps")
            print("   - Face success: 2 long beeps + UNLOCK")
            print("   - No face detected: 1 long beep")
            print("   - RFID backup activated: 2 short + 1 long beep")
            print("   - RFID detected: 2 quick beeps")
            print("   - RFID success: 3 beeps + long beep + UNLOCK")
            print("   - RFID unauthorized: 4 rapid beeps")
            print("🏷️ RFID Backup System:")
            print("   - Activates when face recognition fails")
            print("   - 30-second window to scan card")
            print("   - Authorized cards unlock the system")
            print("🔓 Lock Control:")
            print("   - Face recognition success → Physical lock unlock")
            print("   - RFID backup success → Physical lock unlock")
            if self.gpio_lock:
                print(f"   - Both methods use GPIO pin {GPIO_LOCK_PIN} for {LOCK_UNLOCK_DURATION}s")
            else:
                print("   - Both methods use simulation mode (GPIO disabled)")
            print("Press Ctrl+C to exit")
            print("-" * 50)
            
            # Keep the program running and wait for button presses
            while True:
                # Process any RFID input
                self.process_rfid_input()
                time.sleep(0.1)
            
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
    
    # Initialize and run the button trigger with RFID backup
    trigger = FaceRecognitionButtonTrigger(
        gpio_pin=16,
        buzzer_pin=26,
        debounce_time=0.5,  # 500ms between button presses
        cooldown_time=3.0   # 3 second cooldown after each auth
    )
    trigger.run()

if __name__ == "__main__":
    main() 