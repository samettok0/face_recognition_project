#!/usr/bin/env python3
"""
GPIO Lock Controller for Raspberry Pi 5
Uses gpiozero library to control a lock mechanism via GPIO pin 14
"""

import time
from typing import Optional
from .utils import logger

try:
    from gpiozero import LED
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("gpiozero library not available. GPIO lock functionality disabled.")

class GPIOLockController:
    """
    Controls a lock mechanism using GPIO pin 14
    Uses gpiozero.LED class which works reliably on Pi 5
    """
    
    def __init__(self, pin: int = 14, unlock_duration: float = 5.0):
        """
        Initialize the GPIO lock controller
        
        Args:
            pin: GPIO pin number for lock control (default: 14)
            unlock_duration: How long to keep lock unlocked in seconds (default: 5.0)
        """
        self.pin = pin
        self.unlock_duration = unlock_duration
        self.lock = None
        self.is_initialized = False
        
        if GPIO_AVAILABLE:
            try:
                self.lock = LED(self.pin)
                self.is_initialized = True
                # Initialize in locked state
                self.lock_door()
                logger.info(f"GPIO Lock Controller initialized on pin {self.pin}")
            except Exception as e:
                logger.error(f"Failed to initialize GPIO lock controller: {e}")
                self.is_initialized = False
        else:
            logger.warning("GPIO not available - running in simulation mode")
    
    def lock_door(self) -> bool:
        """
        Lock the door (turn off GPIO pin)
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            logger.info("🔒 [SIMULATION] LOCK LOCKED - GPIO Pin {} OFF".format(self.pin))
            print("🔒 [SIMULATION] LOCK LOCKED")
            return True
            
        try:
            self.lock.off()
            logger.info(f"🔒 LOCK LOCKED - GPIO Pin {self.pin} OFF")
            print("🔒 LOCK LOCKED")
            return True
        except Exception as e:
            logger.error(f"Failed to lock door: {e}")
            return False
    
    def unlock_door(self, duration: Optional[float] = None) -> bool:
        """
        Unlock the door (turn on GPIO pin) for specified duration
        
        Args:
            duration: How long to keep unlocked in seconds (uses default if None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        unlock_time = duration if duration is not None else self.unlock_duration
        
        if not self.is_initialized:
            logger.info("🔓 [SIMULATION] LOCK UNLOCKED - GPIO Pin {} ON for {:.1f}s".format(
                self.pin, unlock_time))
            print(f"🔓 [SIMULATION] LOCK UNLOCKED for {unlock_time:.1f}s")
            return True
            
        try:
            self.lock.on()
            logger.info(f"🔓 LOCK UNLOCKED - GPIO Pin {self.pin} ON")
            print(f"🔓 LOCK UNLOCKED for {unlock_time:.1f}s")
            return True
        except Exception as e:
            logger.error(f"Failed to unlock door: {e}")
            return False
    
    def unlock_temporary(self, duration: Optional[float] = None) -> bool:
        """
        Unlock the door temporarily, then automatically lock it again
        
        Args:
            duration: How long to keep unlocked in seconds (uses default if None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        unlock_time = duration if duration is not None else self.unlock_duration
        
        # Unlock the door
        if not self.unlock_door(unlock_time):
            return False
            
        # Wait for specified duration
        logger.info(f"Door will automatically lock again in {unlock_time:.1f} seconds...")
        time.sleep(unlock_time)
        
        # Lock the door again
        return self.lock_door()
    
    def get_status(self) -> str:
        """
        Get current lock status
        
        Returns:
            str: Status description
        """
        if not self.is_initialized:
            return "SIMULATION MODE - Status unknown"
            
        try:
            if self.lock.is_lit:
                return "UNLOCKED (GPIO ON)"
            else:
                return "LOCKED (GPIO OFF)"
        except Exception as e:
            logger.error(f"Failed to get lock status: {e}")
            return "ERROR - Cannot read status"
    
    def test_lock_cycle(self, cycles: int = 3, cycle_duration: float = 2.0) -> bool:
        """
        Test the lock by cycling it multiple times
        
        Args:
            cycles: Number of lock/unlock cycles to perform
            cycle_duration: How long each state lasts in seconds
            
        Returns:
            bool: True if all tests successful, False otherwise
        """
        logger.info(f"Starting lock test cycle: {cycles} cycles, {cycle_duration}s each")
        print(f"Starting lock test cycle: {cycles} cycles...")
        
        try:
            for i in range(cycles):
                print(f"\n--- Cycle {i+1}/{cycles} ---")
                
                # Unlock
                if not self.unlock_door(cycle_duration):
                    logger.error(f"Failed to unlock during cycle {i+1}")
                    return False
                time.sleep(cycle_duration)
                
                # Lock
                if not self.lock_door():
                    logger.error(f"Failed to lock during cycle {i+1}")
                    return False
                time.sleep(cycle_duration)
            
            print(f"\n✅ Lock test cycle completed successfully!")
            logger.info("Lock test cycle completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Lock test cycle failed: {e}")
            print(f"❌ Lock test cycle failed: {e}")
            return False
    
    def cleanup(self):
        """
        Clean up GPIO resources and ensure lock is in locked state
        """
        try:
            if self.is_initialized and self.lock:
                self.lock_door()  # Ensure locked state
                # gpiozero LED objects don't need explicit cleanup
                logger.info("GPIO lock controller cleaned up")
        except Exception as e:
            logger.error(f"Error during GPIO cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()

# Global lock controller instance
_lock_controller = None

def get_lock_controller(pin: int = 14, unlock_duration: float = 5.0) -> GPIOLockController:
    """
    Get the global lock controller instance (singleton pattern)
    
    Args:
        pin: GPIO pin number for lock control
        unlock_duration: Default unlock duration in seconds
        
    Returns:
        GPIOLockController: The lock controller instance
    """
    global _lock_controller
    if _lock_controller is None:
        _lock_controller = GPIOLockController(pin=pin, unlock_duration=unlock_duration)
    return _lock_controller

def unlock_for_user(username: str, duration: float = 5.0) -> bool:
    """
    Convenience function to unlock door for a specific user
    
    Args:
        username: Name of the authenticated user
        duration: How long to keep unlocked in seconds
        
    Returns:
        bool: True if successful, False otherwise
    """
    controller = get_lock_controller()
    logger.info(f"🔓 Access granted to {username}")
    print(f"🔓 Access granted to {username}")
    return controller.unlock_temporary(duration) 