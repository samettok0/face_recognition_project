#!/usr/bin/env python3
"""
GPIO Lock Controller for Face Recognition System

This module handles the physical lock mechanism using GPIO pins on Raspberry Pi.
It provides methods to lock and unlock the door based on authentication results.
"""

import time
import logging
from typing import Optional
try:
    from gpiozero import LED, Device
    from gpiozero.pins.lgpio import LGPIOFactory
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: GPIO libraries not available. Lock functionality will be simulated.")

# Set up logging
logger = logging.getLogger(__name__)

class GPIOLock:
    """
    GPIO-based lock controller for door access control
    
    This class manages a physical lock mechanism connected to a GPIO pin.
    When activated, it unlocks the door for a specified duration.
    """
    
    def __init__(self, gpio_pin: int = 18, unlock_duration: float = 5.0):
        """
        Initialize the GPIO lock controller
        
        Args:
            gpio_pin: GPIO pin number (BCM numbering) connected to the lock relay
            unlock_duration: How long to keep the lock unlocked (in seconds)
        """
        self.gpio_pin = gpio_pin
        self.unlock_duration = unlock_duration
        self.lock_device: Optional[LED] = None
        self.is_initialized = False
        
        # Initialize GPIO if available
        if GPIO_AVAILABLE:
            try:
                # Set the pin factory to lgpio for Raspberry Pi 5 compatibility
                Device.pin_factory = LGPIOFactory()
                
                # Initialize the lock control pin
                self.lock_device = LED(self.gpio_pin)
                
                # Ensure lock starts in locked state
                self.lock_device.off()
                self.is_initialized = True
                
                logger.info(f"GPIO lock initialized on pin {self.gpio_pin}")
                print(f"🔒 GPIO Lock initialized on pin {self.gpio_pin}")
                
            except Exception as e:
                logger.error(f"Failed to initialize GPIO lock: {e}")
                print(f"❌ Failed to initialize GPIO lock: {e}")
                print("Lock functionality will be simulated.")
                self.is_initialized = False
        else:
            logger.warning("GPIO not available - lock functionality will be simulated")
            print("⚠️  GPIO not available - lock functionality will be simulated")
    
    def unlock(self, username: str) -> bool:
        """
        Unlock the door for the specified duration
        
        Args:
            username: Name of the authenticated user
            
        Returns:
            True if unlock was successful, False otherwise
        """
        try:
            if self.is_initialized and self.lock_device:
                # Physical unlock
                self.lock_device.on()
                logger.info(f"🔓 PHYSICAL UNLOCK: Access granted to {username} - GPIO Pin {self.gpio_pin} ON")
                print(f"🔓 PHYSICAL UNLOCK: Access granted to {username}")
                print(f"   GPIO Pin {self.gpio_pin} activated for {self.unlock_duration} seconds")
                
                # Keep unlocked for specified duration
                time.sleep(self.unlock_duration)
                
                # Lock again
                self.lock_device.off()
                logger.info(f"🔒 PHYSICAL LOCK: Door locked again - GPIO Pin {self.gpio_pin} OFF")
                print(f"🔒 Door locked again after {self.unlock_duration} seconds")
                
            else:
                # Simulated unlock
                logger.info(f"🔓 SIMULATED UNLOCK: Access granted to {username}")
                print(f"🔓 SIMULATED UNLOCK: Access granted to {username}")
                print(f"   (Would activate GPIO Pin {self.gpio_pin} for {self.unlock_duration} seconds)")
                
                # Simulate the unlock duration
                time.sleep(self.unlock_duration)
                
                logger.info(f"🔒 SIMULATED LOCK: Door locked again")
                print(f"🔒 Simulated door locked again after {self.unlock_duration} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during unlock operation: {e}")
            print(f"❌ Error during unlock operation: {e}")
            return False
    
    def lock(self) -> bool:
        """
        Manually lock the door (ensure lock is in locked state)
        
        Returns:
            True if lock was successful, False otherwise
        """
        try:
            if self.is_initialized and self.lock_device:
                self.lock_device.off()
                logger.info(f"🔒 MANUAL LOCK: GPIO Pin {self.gpio_pin} OFF")
                print(f"🔒 Door manually locked - GPIO Pin {self.gpio_pin} OFF")
            else:
                logger.info(f"🔒 SIMULATED MANUAL LOCK")
                print(f"🔒 Simulated door manually locked")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during lock operation: {e}")
            print(f"❌ Error during lock operation: {e}")
            return False
    
    def get_status(self) -> str:
        """
        Get the current status of the lock
        
        Returns:
            String describing the current lock status
        """
        if self.is_initialized and self.lock_device:
            status = "UNLOCKED" if self.lock_device.is_lit else "LOCKED"
            return f"GPIO Pin {self.gpio_pin}: {status}"
        else:
            return "SIMULATED MODE: Status unknown"
    
    def test_lock_cycle(self, cycles: int = 3) -> bool:
        """
        Test the lock by cycling it on and off
        
        Args:
            cycles: Number of lock/unlock cycles to perform
            
        Returns:
            True if test completed successfully, False otherwise
        """
        print(f"🔧 Starting lock test cycle ({cycles} cycles)...")
        logger.info(f"Starting lock test cycle with {cycles} cycles")
        
        try:
            for i in range(cycles):
                print(f"\n--- Test Cycle {i+1}/{cycles} ---")
                
                # Unlock
                if self.is_initialized and self.lock_device:
                    self.lock_device.on()
                    print(f"🔓 Test unlock - GPIO Pin {self.gpio_pin} ON")
                else:
                    print(f"🔓 Test unlock (simulated)")
                
                time.sleep(2)
                
                # Lock
                if self.is_initialized and self.lock_device:
                    self.lock_device.off()
                    print(f"🔒 Test lock - GPIO Pin {self.gpio_pin} OFF")
                else:
                    print(f"🔒 Test lock (simulated)")
                
                time.sleep(1)
            
            print(f"\n✅ Lock test cycle completed successfully!")
            logger.info("Lock test cycle completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Lock test failed: {e}")
            logger.error(f"Lock test failed: {e}")
            return False
    
    def cleanup(self):
        """
        Clean up GPIO resources and ensure lock is in locked state
        """
        try:
            if self.is_initialized and self.lock_device:
                self.lock_device.off()  # Ensure locked state
                logger.info("GPIO lock cleanup completed - lock secured")
                print("🔒 GPIO lock cleanup completed - lock secured")
        except Exception as e:
            logger.error(f"Error during GPIO cleanup: {e}")
            print(f"❌ Error during GPIO cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup() 