#!/usr/bin/env python3

"""
Test script for guided registration functionality
"""

from .guided_registration import register_user_guided

if __name__ == "__main__":
    print("Testing guided registration with head pose detection")
    register_user_guided()