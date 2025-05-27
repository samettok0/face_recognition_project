# Face Recognition Lock System

This document describes the GPIO lock integration with the face recognition system for Raspberry Pi 5.

## Overview

The face recognition system now includes integrated GPIO lock control that:
- 🔒 Keeps the lock **LOCKED** by default (GPIO pin OFF)
- 🔓 **UNLOCKS** the door when an authorized user is recognized (GPIO pin ON)
- ⏰ **Automatically locks** again after a specified duration (default: 5 seconds)
- 🛡️ Uses `gpiozero` library for Pi 5 compatibility (no SOC peripheral base address errors)

## Hardware Setup

### GPIO Connection
- **GPIO Pin 14** is used by default for lock control
- Connect your lock mechanism to GPIO pin 14
- **Lock State**: GPIO OFF = Locked, GPIO ON = Unlocked

### Wiring
```
Raspberry Pi 5     →     Lock Mechanism
GPIO Pin 14        →     Control Signal
Ground (Pin 6)     →     Ground
5V (Pin 2)         →     Power (if needed)
```

## Installation

1. **Install gpiozero** (if not already installed):
   ```bash
   pip install gpiozero==2.0.1
   ```

2. **Update requirements** (already added to requirements.txt):
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start

#### 1. Test Lock Hardware
Test just the GPIO lock functionality without face recognition:
```bash
python run_face_lock.py lock-test
```

**Options:**
- **Automatic test cycle**: Runs multiple lock/unlock cycles
- **Manual control**: Interactive commands (`unlock`, `lock`, `status`, `quit`)

#### 2. Face Recognition + Lock Demo
Run face recognition with automatic lock control:
```bash
python run_face_lock.py face-auth
```

#### 3. Continuous Monitoring
Run continuous monitoring that unlocks for any authorized user:
```bash
python run_face_lock.py continuous
```

### Using the Main System

#### 1. Register Users First
```bash
python -m src.main register
# Follow prompts to register authorized users
```

#### 2. Train the Model
```bash
python -m src.main train
```

#### 3. Run Authentication with Lock Control
```bash
python -m src.main auth
# Now includes automatic lock control when users are recognized
```

#### 4. Test Lock Only
```bash
python -m src.main lock-test
# Quick GPIO lock functionality test
```

### Advanced Usage

#### Custom GPIO Pin
Use a different GPIO pin (e.g., pin 18):
```bash
python run_face_lock.py lock-test --pin 18
python run_face_lock.py face-auth --pin 18
```

#### Custom Test Cycles
```bash
python -m src.main lock-test --pin 14 --cycles 5 --duration 3.0
```

## How It Works

### 1. Lock States
- **🔒 LOCKED**: GPIO pin 14 is OFF (default state)
- **🔓 UNLOCKED**: GPIO pin 14 is ON (temporary state)

### 2. Authentication Flow
1. Camera captures frames continuously
2. Face recognition processes each frame
3. When authorized user is detected:
   - Lock unlocks (GPIO ON)
   - Timer starts (default: 5 seconds)
   - Lock automatically locks again (GPIO OFF)
4. System continues monitoring

### 3. Security Features
- **Fail-safe**: Lock defaults to LOCKED state
- **Auto-lock**: Always locks again after timeout
- **Error handling**: Lock stays secure even if errors occur
- **Cleanup**: Ensures locked state when program exits

## Configuration

### Default Settings
```python
GPIO_PIN = 14           # GPIO pin for lock control
UNLOCK_DURATION = 5.0   # Seconds to keep unlocked
CONSECUTIVE_MATCHES = 2 # Face recognition matches required
RECOGNITION_THRESHOLD = 0.55  # Face recognition confidence
```

### Customizing Lock Duration
Edit `src/gpio_lock_controller.py` or use the unlock_for_user function:
```python
from src.gpio_lock_controller import unlock_for_user
unlock_for_user("username", duration=10.0)  # 10 seconds
```

## API Reference

### GPIOLockController Class

```python
from src.gpio_lock_controller import GPIOLockController

controller = GPIOLockController(pin=14, unlock_duration=5.0)

# Basic operations
controller.lock_door()                    # Lock immediately
controller.unlock_door(duration=5.0)     # Unlock for duration
controller.unlock_temporary(duration=5.0) # Unlock then auto-lock
controller.get_status()                   # Get current status
controller.test_lock_cycle(cycles=3)      # Test functionality
```

### Convenience Functions

```python
from src.gpio_lock_controller import get_lock_controller, unlock_for_user

# Get singleton controller instance
controller = get_lock_controller(pin=14, unlock_duration=5.0)

# Unlock for specific user
unlock_for_user("John", duration=5.0)
```

## Troubleshooting

### Common Issues

#### 1. "Cannot determine SOC peripheral base address"
- ✅ **Fixed**: Using `gpiozero` instead of RPi.GPIO
- This error won't occur with the new implementation

#### 2. "Permission denied" for GPIO
```bash
sudo python run_face_lock.py lock-test
# Or add user to gpio group:
sudo usermod -a -G gpio $USER
# Then logout and login again
```

#### 3. Lock not responding
- Check wiring connections
- Verify GPIO pin number
- Test with basic lock test: `python run_face_lock.py lock-test`

#### 4. Face recognition not triggering lock
- Ensure users are registered: `python -m src.main register`
- Check recognition threshold in BiometricAuth
- Verify users are in authorized list

### Debug Mode
Enable verbose logging by setting log level in `src/utils.py` or use print statements to debug the flow.

### GPIO Simulation Mode
If running on non-Pi hardware, the system automatically enters simulation mode and prints lock actions instead of controlling GPIO.

## Example Workflows

### Initial Setup
```bash
# 1. Register users
python -m src.main register

# 2. Train model
python -m src.main train

# 3. Test lock hardware
python run_face_lock.py lock-test

# 4. Test full system
python run_face_lock.py face-auth
```

### Daily Operation
```bash
# Start continuous monitoring
python run_face_lock.py continuous
# System now automatically unlocks for authorized users
```

### Testing and Debugging
```bash
# Test just the lock
python run_face_lock.py lock-test

# Test face recognition only
python -m src.main auth

# Test with different settings
python -m src.main lock-test --pin 18 --cycles 5
```

## Safety Considerations

1. **Fail-Safe Design**: System defaults to locked state
2. **Auto-Lock Timer**: Prevents accidentally leaving door unlocked
3. **Error Handling**: Lock remains secure even during errors
4. **Exit Cleanup**: Always locks door when program exits
5. **Power Loss**: Physical lock should fail to secure state

## Integration Notes

- The lock controller integrates seamlessly with existing face recognition code
- No changes needed to existing user registration or training workflows
- Compatible with all existing face recognition features (anti-spoofing, head pose, etc.)
- Uses the same logging system for consistent debugging

## Support

For issues with:
- **Face Recognition**: Check existing face recognition documentation
- **GPIO Lock**: Review this document and test with `lock-test` mode
- **Hardware**: Verify wiring and power supply
- **Software**: Check logs in `face_recognition.log` 