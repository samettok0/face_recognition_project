# Button Trigger for Face Recognition Authentication with RFID Backup

This implementation provides GPIO button triggering for your face recognition authentication system using a button connected to GPIO pin 16, a buzzer on GPIO pin 26 for audio feedback, and RFID backup authentication for elderly care pill box systems.

## 🔒 Security Features

**IMPORTANT**: This implementation includes security protections against brute force attacks:

- **Button Debouncing**: Minimum 0.5 seconds between button presses
- **Authentication Cooldown**: 3-second cooldown period after each authentication attempt
- **No Queuing**: Button presses during authentication or cooldown are ignored (not queued)
- **Single Authentication**: Only one authentication process can run at a time

These features prevent someone from rapidly pressing the button multiple times to trigger hundreds of authentication attempts.

## 🏷️ RFID Backup System

**Perfect for Elderly Care**: The system includes RFID backup authentication that automatically activates when face recognition fails:

- **Primary Authentication**: Face recognition (preferred method)
- **Automatic Fallback**: RFID backup activates when face auth fails
- **30-Second Window**: Time limit for RFID card scanning
- **Multiple Cards**: Support for multiple authorized users/caregivers
- **Audio Guidance**: Clear buzzer feedback guides users through the process

### **Workflow:**
1. **Button Press** → Face recognition starts
2. **Face Success** → ✅ Immediate unlock
3. **Face Failure** → 🏷️ RFID backup automatically activates
4. **Scan Card** → ✅ Unlock if authorized

## 🔊 Audio Feedback System

The system provides clear audio feedback for all events:

- **🎵 Startup**: 2 short beeps when system starts
- **🔔 Button Press**: Quick confirmation beep
- **🎶 Auth Start**: 3 beeps when authentication begins
- **✅ Auth Success**: 2 long celebratory beeps (face recognized and authenticated)
- **👤 No Face Detected**: 1 long beep (no face found during auth process)
- **🏷️ RFID Backup Activated**: 2 short + 1 long beep (scan card now)
- **📥 RFID Card Detected**: 2 quick beeps (card scanned)
- **✅ RFID Success**: 3 beeps + long beep (authorized card unlocks)
- **❌ RFID Unauthorized**: 4 rapid beeps (unknown/invalid card)
- **🚫 RFID Not Allowed**: Single beep + pause + beep (wrong time to scan)
- **⏱️ RFID Timeout**: 3 long beeps (30-second window expired)
- **📷 Camera Error**: Alternating beep pattern (camera failed to start)
- **🛑 User Cancelled**: Descending beeps (user pressed 'q' to quit)
- **❌ Auth Failure**: 5 rapid warning beeps (system/command failure)
- **⏱️ Cooldown Warning**: Single beep when button pressed during cooldown
- **🛑 Shutdown**: 2 beeps when system shuts down

## Hardware Setup

### Required Components
- Raspberry Pi (or compatible GPIO-enabled device)
- Push button or momentary switch
- Active buzzer (3.3V or 5V compatible)
- USB RFID reader (125kHz EM4100 compatible)
- RFID cards/tags (125kHz EM4100/EM410X format)
- 10kΩ pull-up resistor (optional, GPIO has internal pull-up)
- Jumper wires

### Wiring Diagram
```
Button Connection:
- One terminal of button → GPIO 16 (Physical pin 36)
- Other terminal of button → Ground (Physical pin 34 or any GND pin)

Buzzer Connection:
- Positive (+) terminal → GPIO 26 (Physical pin 37)
- Negative (-) terminal → Ground (Physical pin 39 or any GND pin)

RFID Reader Connection:
- USB RFID Reader → Any USB port on Raspberry Pi
- No additional wiring required (plug and play)

Note: The gpiozero library automatically enables internal pull-up resistors
for the button, so no external pull-up resistor is required.
```

### Physical Pin Layout
```
Raspberry Pi GPIO Header:
...
33  34  (34 = GND)
35  36  (36 = GPIO 16 - Button)
37  38  (37 = GPIO 26 - Buzzer)
39  40  (39 = GND)

USB Ports:
- RFID Reader connects to any available USB port
```

### RFID Reader Compatibility
- **Frequency**: 125kHz
- **Format**: EM4100/EM410X cards and tags
- **Interface**: USB (plug and play, appears as keyboard input)
- **Range**: 5-8cm reading distance
- **Output**: 10-digit card ID automatically typed when scanned

## Software Setup

### 1. Install Dependencies
```bash
# Install gpiozero if not already installed
pip install gpiozero==2.0.1

# Or install all requirements
pip install -r requirements.txt
```

### 2. Set Up RFID Cards

**First, set up your authorized RFID cards:**
```bash
python setup_rfid_cards.py
```

This utility allows you to:
- Test your RFID reader
- Add authorized cards (grandma's card, caregiver cards, etc.)
- Remove cards if needed
- List all authorized cards

**Example setup process:**
1. Run the setup utility
2. Choose "5. Test RFID reader" to verify your USB reader works
3. Choose "2. Add new card"
4. Scan grandma's card (it will input the 10-digit ID automatically)
5. Enter a name like "Grandma's Card"
6. Repeat for caregiver cards
7. Choose "6. Save and exit"

### 3. Run the Authentication System

#### Option 1: Complete RFID Backup System (recommended for elderly care)
```bash
python button_trigger_with_rfid.py
```

#### Option 2: Face Recognition Only (original version)
```bash
python button_trigger.py
```

#### Option 3: Simple Version (lightweight)
```bash
python simple_button_trigger.py
```

## Files in the System

### Core Files
- **`button_trigger_with_rfid.py`**: Complete system with RFID backup (recommended)
- **`button_trigger.py`**: Face recognition only with improved buzzer feedback
- **`simple_button_trigger.py`**: Lightweight version without RFID

### Setup and Management
- **`setup_rfid_cards.py`**: RFID card management utility
- **`authorized_rfid_cards.json`**: Stores authorized RFID cards (auto-generated)

### Documentation
- **`BUTTON_TRIGGER_README.md`**: This comprehensive guide

## Features

### Main RFID System (`button_trigger_with_rfid.py`)
- **Complete authentication system** with face + RFID backup
- **Automatic fallback** to RFID when face recognition fails
- **Card management** with JSON storage
- **30-second RFID window** after face auth failure
- **Multiple user support** with named cards
- **Comprehensive audio feedback** for all events
- **Security protections** against button spam and unauthorized access

### Setup Utility (`setup_rfid_cards.py`)
- **Easy card enrollment** with scan-to-add functionality
- **Card management** (add, remove, list cards)
- **RFID reader testing** to verify hardware
- **User-friendly interface** with clear instructions

### Original Systems
- **Face recognition only** versions available for comparison
- **All security features** preserved from original implementation

## Usage

### Initial Setup
1. **Connect hardware**:
   - Button to GPIO 16 and ground
   - Buzzer to GPIO 26 and ground
   - RFID reader to USB port

2. **Set up RFID cards**:
   ```bash
   python setup_rfid_cards.py
   ```

3. **Run the system**:
   ```bash
   python button_trigger_with_rfid.py
   ```

### Daily Usage (Perfect for Elderly Care)

#### **Typical Morning Routine:**
1. **Grandma presses button** → Hears confirmation beep
2. **System starts face recognition** → Hears 3 beeps
3. **Face recognition succeeds** → Hears 2 long success beeps → ✅ **Pills accessible**

#### **When Face Recognition Doesn't Work:**
1. **Grandma presses button** → Face recognition starts
2. **No face detected or poor lighting** → Hears 1 long beep
3. **RFID backup activates automatically** → Hears "2 short + 1 long" beep
4. **Grandma taps her card** → Hears 2 quick card-detected beeps
5. **Card authorized** → Hears success pattern → ✅ **Pills accessible via backup**

#### **Audio Guidance:**
- **Clear feedback**: Every action has a distinct sound
- **No confusion**: Different patterns for different outcomes
- **User-friendly**: Even if screen isn't visible, audio guides the process

### System Behavior Examples

#### **Security Protections:**
- **Rapid button presses**: Only first press accepted, others get warning beep
- **Button spam**: Protected by debounce (0.5s) and cooldown (3s) periods
- **During authentication**: All button presses get warning beep and are ignored
- **RFID wrong time**: Card scans outside backup window get "not allowed" beep
- **Unknown cards**: Unauthorized cards get rapid warning beeps

#### **RFID Backup Scenarios:**
- **No face in view**: 1 long beep → RFID backup → scan card
- **Camera issues**: Alternating beeps → RFID backup → scan card
- **Poor lighting**: Face timeout → RFID backup → scan card
- **User preference**: Can fail face auth intentionally to use card

### Audio Feedback Patterns

| Event | Pattern | Description |
|-------|---------|-------------|
| System Startup | ♪♪ | 2 short beeps |
| Valid Button Press | ♪ | Quick confirmation beep |
| Auth Starting | ♪♪♪ | 3 beeps |
| Face Success | ♪♪♪♪ | 2 long celebratory beeps |
| No Face Detected | ♪♪♪♪ | 1 long beep (activates RFID backup) |
| RFID Backup Active | ♪♪-♪♪♪♪ | 2 short + 1 long beep |
| RFID Card Detected | ♪-♪ | 2 quick beeps |
| RFID Success | ♪♪♪-♪♪♪♪ | 3 beeps + long success beep |
| RFID Unauthorized | ♪♪♪♪ | 4 rapid warning beeps |
| RFID Not Allowed | ♪♪-♪ | Warning pattern |
| RFID Timeout | ♪♪-♪♪-♪♪ | 3 long timeout beeps |
| Camera Error | ♪♪-♪-♪♪-♪ | Alternating pattern |
| User Cancelled | ♪♪-♪-♪ | Descending beeps |
| Cooldown Warning | ♪ | Single warning beep |
| System Shutdown | ♪♪ | 2 shutdown beeps |

## Customization

### Security Settings

You can adjust the security parameters:

#### In `button_trigger_with_rfid.py`:
```python
trigger = FaceRecognitionButtonTrigger(
    gpio_pin=16,         # Button GPIO pin
    buzzer_pin=26,       # Buzzer GPIO pin
    debounce_time=1.0,   # 1 second between button presses
    cooldown_time=5.0    # 5 second cooldown after each auth
)
```

### RFID Settings

#### Modify RFID timeout:
```python
self.rfid_timeout = 45  # 45 seconds instead of 30
```

#### Change GPIO pins:
```python
BUTTON_PIN = 18  # Change button to GPIO 18
BUZZER_PIN = 21  # Change buzzer to GPIO 21
```

### RFID Card Management

#### Add cards programmatically:
```python
# In your script
trigger.add_rfid_card("1234567890", "Nurse Card")
trigger.add_rfid_card("0987654321", "Doctor Card")
```

#### Manage cards via file:
Edit `authorized_rfid_cards.json`:
```json
{
  "1234567890": "Grandma's Card",
  "0987654321": "Caregiver Card",
  "1122334455": "Emergency Card"
}
```

### Customize Buzzer Patterns

You can modify buzzer patterns for different feedback:
```python
def buzzer_custom_pattern(self):
    """Create your own buzzer pattern"""
    def custom():
        self.buzzer.on()
        time.sleep(0.2)
        self.buzzer.off()
        time.sleep(0.1)
        self.buzzer.on()
        time.sleep(0.2)
        self.buzzer.off()
    
    threading.Thread(target=custom, daemon=True).start()
```

## Troubleshooting

### Common Issues

1. **"GPIO support not available"**
   - Ensure you're running on a Raspberry Pi or GPIO-enabled device
   - Check that gpiozero is properly installed

2. **"'src' directory not found"**
   - Run the script from the face_recognition_project root directory
   - Ensure the src/ directory exists with your modules

3. **Button not responding**
   - Check wiring connections
   - Verify GPIO pin number (physical pin 36 = GPIO 16)
   - Test with a multimeter if available

4. **Buzzer not working**
   - Check buzzer wiring (positive to GPIO 26, negative to ground)
   - Verify buzzer type (active buzzer recommended)
   - Test buzzer with a simple circuit
   - Check if buzzer is 3.3V compatible

5. **RFID reader not detected**
   - Ensure USB RFID reader is plugged in
   - Check if reader appears as keyboard device: `lsusb`
   - Test reader independently: `python setup_rfid_cards.py` → option 5
   - Try different USB port

6. **RFID cards not reading**
   - Verify card format (125kHz EM4100/EM410X)
   - Check reading distance (5-8cm from reader)
   - Test with setup utility to see raw card data
   - Ensure cards are not damaged

7. **RFID backup not activating**
   - Ensure face recognition completes (succeeds or fails)
   - Check that RFID backup gets activated (listen for pattern)
   - Verify cards are in authorized list
   - Check 30-second timeout hasn't expired

8. **Cards not being recognized**
   - Verify card ID matches exactly in `authorized_rfid_cards.json`
   - Use setup utility to re-scan and compare IDs
   - Check for extra spaces or characters in card data

9. **Button presses being ignored**
   - Check if you're in cooldown period (wait 3 seconds after last authentication)
   - Ensure you're not pressing too rapidly (wait 0.5 seconds between presses)
   - Listen for warning beep - this is normal security behavior

10. **Permission errors**
    - Run with appropriate permissions for GPIO access
    - On some systems: `sudo python button_trigger_with_rfid.py`

### Testing Hardware

#### Test Button Connection:
```python
from gpiozero import Button
button = Button(16)
button.wait_for_press()
print("Button works!")
```

#### Test Buzzer Connection:
```python
from gpiozero import Buzzer
import time
buzzer = Buzzer(26)
buzzer.on()
time.sleep(1)
buzzer.off()
print("Buzzer works!")
```

#### Test RFID Reader:
```bash
python setup_rfid_cards.py
# Choose option 5: Test RFID reader
# Scan a card and verify 10-digit output
```

### Testing Security Features
To verify the security protections are working:
1. Press the button rapidly multiple times
2. You should hear warning beeps for ignored presses
3. You should see messages like "Button press too fast - ignored"
4. Only one authentication should start
5. After authentication, button presses should trigger warning beeps for 3 seconds

### Testing RFID System
To verify RFID backup functionality:
1. Press button → let face recognition fail (cover camera or look away)
2. Listen for "no face detected" beep followed by RFID activation pattern
3. Scan an authorized card → should hear success pattern and unlock
4. Try scanning unauthorized card → should hear warning beeps
5. Wait 30+ seconds without scanning → should hear timeout pattern

## Running as a Service

To run the system automatically on boot, create a systemd service:

1. Create service file:
```bash
sudo nano /etc/systemd/system/face-auth-rfid.service
```

2. Add service configuration:
```ini
[Unit]
Description=Face Recognition + RFID Backup Authentication
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/face_recognition_project
ExecStart=/usr/bin/python3 /home/pi/face_recognition_project/button_trigger_with_rfid.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start service:
```bash
sudo systemctl enable face-auth-rfid.service
sudo systemctl start face-auth-rfid.service
```

4. Check service status:
```bash
sudo systemctl status face-auth-rfid.service
```

## Safety Notes

- Always use proper GPIO voltage levels (3.3V logic)
- Ensure proper grounding to prevent damage
- Use active buzzers rated for 3.3V or 5V operation
- RFID reader should be USB powered (no additional power needed)
- The built-in debouncing protects against electrical button bounce
- Security features prevent brute force attacks through button spam
- RFID backup only activates after face authentication fails (security feature)
- Consider using a physical button with good tactile feedback to prevent accidental multiple presses
- Buzzer audio patterns provide clear feedback without being overwhelming
- Store RFID card file securely and backup regularly
- Use unique card IDs and avoid default/test cards in production

## Elderly Care Specific Features

### Design Philosophy
- **Primary method**: Face recognition (convenient, hands-free)
- **Automatic backup**: RFID activates only when needed
- **Clear guidance**: Audio feedback guides users through each step
- **No confusion**: Different sounds for different situations
- **Reliability**: Multiple ways to access (face or card)

### User Experience Benefits
- **Independence**: Elderly users can operate without assistance
- **Confidence**: Clear audio feedback reduces uncertainty
- **Accessibility**: Works even with vision or dexterity challenges
- **Backup option**: Card provides reliable alternative access
- **Family peace of mind**: Caregivers can have their own cards

### Caregiver Features
- **Multiple cards**: Each caregiver can have their own authorized card
- **Easy management**: Simple utility to add/remove cards
- **Monitoring**: System logs provide usage information
- **Emergency access**: RFID provides access if primary system fails 