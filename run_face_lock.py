#!/usr/bin/env python3
"""
Face Recognition Lock System - Easy Run Script
This script provides easy access to all face recognition lock functionality
"""

import sys
import os
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    # Import and run the main demo
    from face_recognition_lock_demo import main
    main() 