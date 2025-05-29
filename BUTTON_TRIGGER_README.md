# Button Trigger for Face Recognition Authentication

This implementation provides GPIO button triggering for your face recognition authentication system using a button connected to GPIO pin 16 and a buzzer on GPIO pin 26 for audio feedback.

## 🔒 Security Features

**IMPORTANT**: This implementation includes security protections against brute force attacks:

- **Button Debouncing**: Minimum 0.5 seconds between button presses
- **Authentication Cooldown**: 3-second cooldown period after each authentication attempt
- **No Queuing**: Button presses during authentication or cooldown are ignored (not queued)
- **Single Authentication**: Only one authentication process can run at a time

These features prevent someone from rapidly pressing the button multiple times to trigger hundreds of authentication attempts.

## 🔊 Audio Feedback System

The system provides clear audio feedback for all events:

- **🎵 Startup**: 2 short beeps when system starts
- **🔔 Button Press**: Quick confirmation beep
- **🎶 Auth Start**: 3 beeps when authentication begins
- **✅ Auth Success**: 2 long celebratory beeps (face recognized and authenticated)
- **👤 No Face Detected**: 1 long beep (no face found during auth process)
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
```

### Buzzer Types
- **Active Buzzer**: Recommended - produces sound when voltage is applied
- **Passive Buzzer**: Can work but may require different coding approach
- **Voltage**: 3.3V or 5V compatible (Raspberry Pi GPIO outputs 3.3V)

## Software Setup

### 1. Install Dependencies
```bash
# Install gpiozero if not already installed
pip install gpiozero==2.0.1

# Or install all requirements
pip install -r requirements.txt
```

### 2. Run the Button Trigger

#### Option 1: Full-featured version (recommended)
```bash
python button_trigger.py
```

#### Option 2: Simple version
```bash
python simple_button_trigger.py
```

## Features

### Main Script (`button_trigger.py`)
- **Class-based architecture** for better organization
- **Configurable security settings** (debounce and cooldown times)
- **Advanced buzzer patterns** with threading for non-blocking audio
- **GPIO validation** checks for compatible hardware
- **Directory validation** ensures proper execution context
- **Process management** prevents multiple simultaneous authentications
- **Comprehensive error handling** with detailed feedback
- **Proper GPIO cleanup** on exit

### Simple Script (`simple_button_trigger.py`)
- **Lightweight implementation** with minimal code
- **Built-in security protections** against button spam
- **Basic buzzer functionality** with clear audio feedback
- **Essential error handling** for reliable operation

## Usage

1. **Connect your hardware**:
   - Button to GPIO 16 and ground
   - Buzzer to GPIO 26 and ground
2. **Navigate** to your project directory
3. **Run the script**:
   ```bash
   python button_trigger.py
   ```
4. **Listen for startup beeps** (2 short beeps confirm system is ready)
5. **Press the button** to trigger face recognition authentication with anti-spoofing
6. **Listen to audio feedback** for authentication status
7. **Wait for cooldown** before next button press (3 seconds by default)
8. **Press Ctrl+C** to stop the program (listen for shutdown beeps)

## What Happens When Button is Pressed

1. **Button press validation**: Checks for debounce and cooldown periods
2. **Audio confirmation**: Quick beep confirms valid button press
3. **Authentication start**: 3 beeps indicate auth is starting
4. **Single authentication**: Executes `python -m src.main auth --anti-spoofing`
5. **Authentication runs**: Face recognition with anti-spoofing enabled
6. **Result feedback**: Success (2 long beeps) or failure (5 rapid beeps)
7. **Cooldown period**: 3-second wait before accepting next button press
8. **Ready for next press**: System ready for another authentication

### Security Behavior Examples

- **Rapid button presses**: Only the first press is accepted, others trigger warning beep
- **Button spam**: Protected by debounce (0.5s) and cooldown (3s) periods
- **During authentication**: All button presses trigger warning beep and are ignored
- **After authentication**: Must wait 3 seconds before next attempt

### Audio Feedback Patterns

| Event | Pattern | Description |
|-------|---------|-------------|
| System Startup | ♪♪ | 2 short beeps |
| Valid Button Press | ♪ | Quick confirmation beep |
| Auth Starting | ♪♪♪ | 3 beeps |
| Auth Success | ♪♪♪♪ | 2 long celebratory beeps (face recognized) |
| No Face Detected | ♪♪♪♪ | 1 long beep (timeout/max frames) |
| Camera Error | ♪♪-♪-♪♪-♪-♪♪-♪ | Alternating pattern (camera failed) |
| User Cancelled | ♪♪-♪-♪ | Descending beeps (user quit) |
| Auth Failure | ♪♪♪♪♪ | 5 rapid warning beeps (system error) |
| Cooldown Warning | ♪ | Single warning beep |
| Error | ♪♪♪♪ | 2 long error tones |
| System Shutdown | ♪♪ | 2 shutdown beeps |

## Customization

### Security Settings

You can adjust the security parameters in both scripts:

#### In `button_trigger.py`:
```python
trigger = FaceRecognitionButtonTrigger(
    gpio_pin=16,         # Button GPIO pin
    buzzer_pin=26,       # Buzzer GPIO pin
    debounce_time=1.0,   # 1 second between button presses
    cooldown_time=5.0    # 5 second cooldown after each auth
)
```

#### In `simple_button_trigger.py`:
```python
BUTTON_PIN = 16      # Button GPIO pin
BUZZER_PIN = 26      # Buzzer GPIO pin
DEBOUNCE_TIME = 1.0  # 1 second between button presses
COOLDOWN_TIME = 5.0  # 5 second cooldown after authentication
```

### Change GPIO Pins
Edit the pin variables in the script:
```python
BUTTON_PIN = 18  # Change button to GPIO 18
BUZZER_PIN = 21  # Change buzzer to GPIO 21
```

### Customize Buzzer Patterns
You can modify the buzzer patterns in the scripts:
```python
def buzzer_custom_pattern():
    """Create your own buzzer pattern"""
    buzzer.on()
    time.sleep(0.2)
    buzzer.off()
    time.sleep(0.1)
    buzzer.on()
    time.sleep(0.2)
    buzzer.off()
```

### Modify Authentication Command
Edit the command in the `run_authentication()` function:
```python
# Example: Add different parameters
result = subprocess.run([
    sys.executable, "-m", "src.main", "auth", 
    "--anti-spoofing", 
    "--model", "cnn",  # Use CNN model instead of HOG
    "--window", "20"   # Larger decision window
])
```

### Adjust Timeout
Change the timeout value:
```python
result = subprocess.run(
    [...],
    timeout=180  # 3 minute timeout instead of 2
)
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

5. **No audio from buzzer**
   - Ensure you're using an active buzzer, not a passive one
   - Check power connections
   - Try a different GPIO pin
   - Test buzzer independently

6. **Button presses being ignored**
   - Check if you're in cooldown period (wait 3 seconds after last authentication)
   - Ensure you're not pressing too rapidly (wait 0.5 seconds between presses)
   - Listen for warning beep - this is normal security behavior

7. **Permission errors**
   - Run with appropriate permissions for GPIO access
   - On some systems: `sudo python button_trigger.py`

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

### Testing Security Features
To verify the security protections are working:
1. Press the button rapidly multiple times
2. You should hear warning beeps for ignored presses
3. You should see messages like "Button press too fast - ignored"
4. Only one authentication should start
5. After authentication, button presses should trigger warning beeps for 3 seconds

## Running as a Service

To run the button trigger automatically on boot, create a systemd service:

1. Create service file:
```bash
sudo nano /etc/systemd/system/face-auth-button.service
```

2. Add service configuration:
```ini
[Unit]
Description=Face Recognition Button Trigger
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/face_recognition_project
ExecStart=/usr/bin/python3 /home/pi/face_recognition_project/button_trigger.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Enable and start service:
```bash
sudo systemctl enable face-auth-button.service
sudo systemctl start face-auth-button.service
```

## Safety Notes

- Always use proper GPIO voltage levels (3.3V logic)
- Ensure proper grounding to prevent damage
- Use active buzzers rated for 3.3V or 5V operation
- The built-in debouncing protects against electrical button bounce
- Security features prevent brute force attacks through button spam
- Consider using a physical button with good tactile feedback to prevent accidental multiple presses
- Buzzer audio patterns provide clear feedback without being overwhelming 