#!/usr/bin/env python3
"""
Run the biometric authentication API server

This script starts the API server in standalone mode.
It can be used for testing or when there is no existing Flask app.

Usage:
    python run_api_server.py
"""

import sys
import os
import logging
from src.flask_integration import start_standalone_server
from src.utils import logger

if __name__ == "__main__":
    # Configure logging to console for better visibility
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    
    logger.info("Starting biometric authentication API server...")
    try:
        start_standalone_server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error starting server: {e}") 