# Button Trigger for Face Recognition Authentication

This implementation provides GPIO button triggering for your face recognition authentication system using a button connected to GPIO pin 16.

## Hardware Setup

### Required Components
- Raspberry Pi (or compatible GPIO-enabled device)
- Push button or momentary switch
- 10kΩ pull-up resistor (optional, GPIO has internal pull-up)
- Jumper wires

### Wiring Diagram
```
Button Connection:
- One terminal of button → GPIO 16 (Physical pin 36)
- Other terminal of button → Ground (Physical pin 34 or any GND pin)

Note: The gpiozero library automatically enables internal pull-up resistors,
so no external pull-up resistor is required.
```

### Physical Pin Layout
```
Raspberry Pi GPIO Header:
...
33  34  (34 = GND)
35  36  (36 = GPIO 16)
37  38
39  40
```

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
- **GPIO validation** checks for compatible hardware
- **Directory validation** ensures proper execution context
- **Process management** prevents multiple simultaneous authentications
- **Comprehensive error handling** with detailed feedback
- **Proper GPIO cleanup** on exit

### Simple Script (`simple_button_trigger.py`)
- **Lightweight implementation** with minimal code
- **Basic button handling** for straightforward use cases
- **Essential error handling** for reliable operation

## Usage

1. **Connect your button** to GPIO pin 16 and ground
2. **Navigate** to your project directory
3. **Run the script**:
   ```bash
   python button_trigger.py
   ```
4. **Press the button** to trigger face recognition authentication with anti-spoofing
5. **Press Ctrl+C** to stop the program

## What Happens When Button is Pressed

1. Button press is detected on GPIO pin 16
2. Script executes: `python -m src.main auth --anti-spoofing`
3. Face recognition authentication starts with anti-spoofing enabled
4. Authentication runs for up to 2 minutes or until completion
5. Results are displayed in the terminal
6. System is ready for the next button press

## Customization

### Change GPIO Pin
Edit the `BUTTON_PIN` variable in the script:
```python
BUTTON_PIN = 18  # Change to your desired GPIO pin
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

4. **Permission errors**
   - Run with appropriate permissions for GPIO access
   - On some systems: `sudo python button_trigger.py`

### Testing Button Connection
You can test if your button is properly connected:
```python
from gpiozero import Button
button = Button(16)
button.wait_for_press()
print("Button works!")
```

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
- Use debounced buttons or implement software debouncing if needed
- The script includes protection against multiple simultaneous authentications 