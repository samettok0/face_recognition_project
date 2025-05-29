#!/bin/bash

# Face Recognition + RFID System - Complete Startup Script
# This script safely starts the system with full cleanup

echo "🚀 Starting Face Recognition + RFID System..."

# Export required environment variables
export DISPLAY=:0
export HOME=/home/pillguard
export USER=pillguard
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Kill any existing instances
echo "🛑 Stopping existing processes..."
pkill -f button_trigger_with_rfid.py
pkill -f face_recognition_main.py
sleep 3

# Clean up GPIO resources (force cleanup)
echo "🔧 Cleaning up GPIO resources..."
# Reset GPIO pins to default state
echo "16" > /sys/class/gpio/unexport 2>/dev/null || true
echo "18" > /sys/class/gpio/unexport 2>/dev/null || true  
echo "26" > /sys/class/gpio/unexport 2>/dev/null || true

# Clean up lgpio notification files
echo "🧹 Cleaning up lgpio files..."
rm -f /home/pillguard/face_recognition_project/.lgd-nfy* 2>/dev/null || true
rm -f /tmp/.lgd-nfy* 2>/dev/null || true
rm -f /.lgd-nfy* 2>/dev/null || true

# Wait for GPIO cleanup to complete
echo "⏳ Waiting for GPIO cleanup (5 seconds)..."
sleep 5

# Change to project directory
echo "📁 Changing to project directory..."
cd /home/pillguard/face_recognition_project

# Check if directory exists
if [ ! -d "/home/pillguard/face_recognition_project" ]; then
    echo "❌ Project directory not found!"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "facerecogenv" ]; then
    echo "❌ Virtual environment not found!"
    exit 1
fi

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source facerecogenv/bin/activate

# Check if script exists
if [ ! -f "button_trigger_with_rfid.py" ]; then
    echo "❌ Script file not found!"
    exit 1
fi

# Create log file if it doesn't exist
touch /home/pillguard/face_auth.log

# Wait a bit more for system to be fully ready
echo "⏳ Waiting for system to be ready (10 seconds)..."
sleep 10

# Start the script
echo "🎯 Starting Face Recognition + RFID system..."
echo "===============================================" >> /home/pillguard/face_auth.log
echo "$(date): System startup initiated" >> /home/pillguard/face_auth.log
echo "===============================================" >> /home/pillguard/face_auth.log

# Run the main script
python button_trigger_with_rfid.py >> /home/pillguard/face_auth.log 2>&1 &

echo "✅ Face Recognition + RFID system started!"
echo "📋 Check logs: tail -f /home/pillguard/face_auth.log" 