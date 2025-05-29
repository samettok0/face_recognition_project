# Face Recognition + RFID Backup Authentication System

🏥 **Elderly Care Pill Box Security System**  
🔒 **Dual Authentication: Face Recognition + RFID Backup**  
🔊 **Audio Feedback & GPIO Lock Control**

---

## 📋 Project Overview

This system provides secure access control for an elderly care pill box using advanced biometric authentication with a reliable backup method. The system combines face recognition technology with RFID card authentication to ensure accessible yet secure medication access.

### 🎯 Key Features

- **🔐 Dual Authentication Methods**
  - Primary: Face recognition with anti-spoofing
  - Backup: RFID card authentication
- **🔊 Audio Feedback System**
  - Button press confirmation
  - Authentication status sounds
  - Different patterns for different states
- **🔒 Physical Lock Control**
  - GPIO-controlled electronic lock
  - 5-second unlock duration
  - Active LOW signal (configurable)
- **🚨 Security Features**
  - Button debouncing (500ms)
  - Authentication cooldown (3 seconds)
  - Anti-spoofing protection
  - Authorized card management
- **🔄 Automatic Startup**
  - Boots with Raspberry Pi
  - Process monitoring and restart
  - GPIO cleanup and recovery

---

## 🏗️ System Architecture

### Hardware Components
- **Raspberry Pi 4** (or compatible)
- **USB Camera** (face recognition)
- **USB RFID Reader** (HID keyboard emulation)
- **Push Button** (GPIO pin 16)
- **Electronic Lock** (GPIO pin 18)
- **Buzzer** (GPIO pin 26)

### Software Stack
- **Python 3.8+**
- **OpenCV** for camera operations
- **face-recognition** library
- **gpiozero** for GPIO control
- **Custom GPIO lock system**
- **Anti-spoofing detection**

---

## 🔄 System Flow

```
┌─────────────────┐
│  Button Press   │ (GPIO 16)
└─────┬───────────┘
      │
      ▼
┌─────────────────┐
│ Face Recognition│ ◄─── Camera activation
│   (Primary)     │      Anti-spoofing check
└─────┬───────────┘      User identification
      │
      ├─── SUCCESS ──► ┌──────────────┐
      │                │ Unlock Lock  │ (GPIO 18)
      │                │ Success Buzz │ (GPIO 26)
      │                └──────────────┘
      │
      └─── FAILURE ──► ┌──────────────┐
                       │ RFID Backup  │
                       │  Activated   │ ◄─── 30-second window
                       └─────┬────────┘      Scan authorized card
                             │
                             ├─── VALID CARD ──► Unlock Lock
                             │
                             └─── TIMEOUT/INVALID ──► Access Denied
```

### 🎯 Authentication Process

1. **Button Trigger** - User presses button on GPIO pin 16
2. **Face Recognition** - Camera activates, performs anti-spoofing check
3. **Success Path** - Face recognized → GPIO lock opens for 5 seconds
4. **Failure Path** - Face not recognized → RFID backup activates
5. **RFID Backup** - 30-second window to scan authorized RFID card
6. **Lock Control** - Both methods use same GPIO lock mechanism

---

## 🚀 Installation & Setup

### Prerequisites
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install python3-pip python3-venv git cmake

# Enable camera
sudo raspi-config
# Interface Options → Camera → Enable
```

### Project Setup
```bash
# Clone repository
git clone <repository-url>
cd face_recognition_project

# Create virtual environment
python3 -m venv facerecogenv
source facerecogenv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### GPIO Setup
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER

# For RFID input access
sudo usermod -a -G input $USER

# Logout and login for group changes
```

---

## 🎮 Manual Operation

### Start System Manually
```bash
cd /home/pillguard/face_recognition_project
source facerecogenv/bin/activate
python3 button_trigger_with_rfid.py
```

### Add RFID Cards
```bash
# Edit authorized cards
nano authorized_rfid_cards.json

# Example format:
{
  "1234567890": "Admin Card",
  "0987654321": "Backup Card"
}
```

### Test Components
```bash
# Test face recognition only
python3 -m src.main auth --anti-spoofing

# Test GPIO lock
python3 -c "
from src.gpio_lock import GPIOLock
lock = GPIOLock()
lock.unlock('Test')
"
```

---

## 🔧 Troubleshooting Guide

### 🚨 GPIO Busy Error

**Problem**: `GPIO pin already in use` or `Resource busy`

**Solutions**:
```bash
# Method 1: Kill existing processes
pkill -f "button_trigger_with_rfid.py"
pkill -f "face_recognition"
sleep 2

# Method 2: Unexport GPIO pins
echo 16 > /sys/class/gpio/unexport 2>/dev/null
echo 18 > /sys/class/gpio/unexport 2>/dev/null
echo 26 > /sys/class/gpio/unexport 2>/dev/null

# Method 3: Clean lgpio files
rm -f /dev/shm/.lgd-nfy* 2>/dev/null
rm -f /tmp/.lgd-nfy* 2>/dev/null

# Method 4: Restart if persistent
sudo reboot
```

### 📷 Camera Issues

**Problem**: Camera not detected or permission denied

```bash
# Check camera
ls /dev/video*

# Test camera
raspistill -o test.jpg

# Check permissions
groups $USER | grep video

# Add to video group if needed
sudo usermod -a -G video $USER
```

### 🏷️ RFID Not Working

**Problem**: RFID cards not detected

```bash
# Check USB RFID reader
lsusb | grep -i hid

# Test RFID input
# (In terminal, scan card - should type numbers)

# Check input permissions
groups $USER | grep input

# Add to input group
sudo usermod -a -G input $USER
```

### 🔊 No Audio Feedback

**Problem**: Buzzer not working

```bash
# Test buzzer manually
python3 -c "
from gpiozero import Buzzer
import time
buzzer = Buzzer(26)
buzzer.on()
time.sleep(0.5)
buzzer.off()
"

# Check GPIO connections
gpio readall
```

### 🔄 System Not Starting

**Problem**: System doesn't start automatically

```bash
# Check cron jobs
crontab -l

# Check cron logs
sudo tail -f /var/log/syslog | grep CRON

# Check system log
tail -f /home/pillguard/face_auth.log

# Manual cron entry:
@reboot sleep 15 && /home/pillguard/face_recognition_project/start_face_auth_complete.sh > /home/pillguard/face_auth.log 2>&1
```

---

## 🔧 System Configuration

### GPIO Pin Assignment
| Component | GPIO Pin | Type | Notes |
|-----------|----------|------|-------|
| Button | 16 | Input | Pull-up resistor |
| Lock | 18 | Output | Active LOW |
| Buzzer | 26 | Output | PWM capable |

### Configuration Files
- `src/config.py` - GPIO settings, timing parameters
- `authorized_rfid_cards.json` - Authorized RFID cards
- `requirements.txt` - Python dependencies

### Audio Patterns
- **Button Press**: Short beep (50ms)
- **Auth Start**: 3 quick beeps
- **Face Success**: 2 long beeps (300ms each)
- **RFID Backup**: 2 short + 1 long beep
- **RFID Success**: 3 beeps + long beep
- **Error/Unauthorized**: Rapid beeps

---

## 📊 System Status Commands

### Check System Health
```bash
# Check if running
ps aux | grep button_trigger_with_rfid

# Check GPIO status
gpio readall

# Check camera
v4l2-ctl --list-devices

# Check USB devices
lsusb

# Check system resources
top
free -h
df -h
```

### Monitor Logs
```bash
# Real-time system log
tail -f /home/pillguard/face_auth.log

# System messages
sudo tail -f /var/log/syslog

# Check for errors
grep -i error /home/pillguard/face_auth.log
```

---

## 🔒 Security Features

### Face Recognition
- **Anti-spoofing detection** prevents photo attacks
- **Multiple attempt protection** (3 attempts max)
- **Timeout protection** (2-minute maximum)
- **Quality checks** ensure good face capture

### RFID System
- **Authorized card list** in JSON format
- **Card ID validation** (minimum 8 characters)
- **30-second timeout** for card scanning
- **Unauthorized card alerts**

### System Security
- **Button debouncing** prevents rapid presses
- **Authentication cooldown** prevents spam attempts
- **Process isolation** in virtual environment
- **GPIO cleanup** on system shutdown

---

## 🚀 Quick Start Commands

### Emergency Manual Start
```bash
# Full cleanup and restart
sudo pkill -f button_trigger_with_rfid; sleep 2; cd /home/pillguard/face_recognition_project; source facerecogenv/bin/activate; python3 button_trigger_with_rfid.py
```

### Quick GPIO Reset
```bash
# One-liner GPIO cleanup
for pin in 16 18 26; do echo $pin > /sys/class/gpio/unexport 2>/dev/null; done; rm -f /dev/shm/.lgd-nfy* /tmp/.lgd-nfy* 2>/dev/null
```

### System Health Check
```bash
# All-in-one health check
echo "=== SYSTEM HEALTH ===" && ps aux | grep -E "(button_trigger|face_recognition)" && echo "=== GPIO STATUS ===" && gpio readall | grep -E "(16|18|26)" && echo "=== CAMERA ===" && ls /dev/video* && echo "=== USB DEVICES ===" && lsusb | grep -i hid
```

---

## 📞 Support Information

### File Locations
- **Main Script**: `button_trigger_with_rfid.py`
- **Face Recognition**: `src/main.py`
- **GPIO Lock**: `src/gpio_lock.py`
- **Configuration**: `src/config.py`
- **Logs**: `/home/pillguard/face_auth.log`
- **RFID Cards**: `authorized_rfid_cards.json`

### System Requirements
- **OS**: Raspberry Pi OS (Bullseye or newer)
- **Python**: 3.8+
- **Memory**: 2GB RAM minimum
- **Storage**: 8GB SD card minimum
- **Camera**: USB webcam or Pi Camera
- **RFID**: USB HID-compatible reader

### Performance Notes
- **Startup Time**: ~30 seconds after boot
- **Face Recognition**: 3-5 seconds per attempt
- **RFID Response**: Instant detection
- **Lock Duration**: 5 seconds (configurable)
- **Cooldown Period**: 3 seconds between attempts

---

**🎯 This system provides reliable, secure, and user-friendly access control for elderly care applications with comprehensive troubleshooting support for seamless operation.** 