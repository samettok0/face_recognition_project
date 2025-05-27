#!/usr/bin/env python3
import time
import platform
from typing import Optional
from .utils import logger

class GPIOLockController:
    """
    GPIO Lock Controller for Raspberry Pi
    Controls a lock mechanism connected to GPIO pin 18
    """
    
    def __init__(self, gpio_pin: int = 18):
        """
        Initialize the GPIO lock controller
        
        Args:
            gpio_pin: GPIO pin number for lock control (default: 18)
        """
        self.gpio_pin = gpio_pin
        self.lock = None
        self.is_raspberry_pi = self._check_if_raspberry_pi()
        self.lock_state = "LOCKED"  # Track current state
        
        if self.is_raspberry_pi:
            try:
                from gpiozero import LED
                self.lock = LED(self.gpio_pin)
                logger.info(f"GPIO lock controller initialized on pin {self.gpio_pin}")
                # Start in locked state
                self.lock_door()
            except ImportError:
                logger.error("gpiozero library not found. Install with: pip install gpiozero")
                self.lock = None
            except Exception as e:
                logger.error(f"Failed to initialize GPIO: {e}")
                self.lock = None
        else:
            logger.warning("Not running on Raspberry Pi - GPIO lock controller in simulation mode")
    
    def _check_if_raspberry_pi(self) -> bool:
        """Check if running on a Raspberry Pi"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'BCM' in cpuinfo or 'Raspberry Pi' in cpuinfo
        except:
            return False
    
    def unlock_door(self, username: Optional[str] = None) -> bool:
        """
        Unlock the door (turn on GPIO pin)
        
        Args:
            username: Name of the user requesting unlock (for logging)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.lock is not None:
                self.lock.on()
                self.lock_state = "UNLOCKED"
                user_info = f" for {username}" if username else ""
                logger.info(f"🔓 DOOR UNLOCKED - GPIO Pin {self.gpio_pin} ON{user_info}")
                print(f"🔓 DOOR UNLOCKED - Access granted{user_info}")
                return True
            else:
                # Simulation mode
                self.lock_state = "UNLOCKED"
                user_info = f" for {username}" if username else ""
                logger.info(f"🔓 [SIMULATION] DOOR UNLOCKED{user_info}")
                print(f"🔓 [SIMULATION] DOOR UNLOCKED - Access granted{user_info}")
                return True
        except Exception as e:
            logger.error(f"Failed to unlock door: {e}")
            print(f"❌ Failed to unlock door: {e}")
            return False
    
    def lock_door(self, reason: str = "Default") -> bool:
        """
        Lock the door (turn off GPIO pin)
        
        Args:
            reason: Reason for locking (for logging)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.lock is not None:
                self.lock.off()
                self.lock_state = "LOCKED"
                logger.info(f"🔒 DOOR LOCKED - GPIO Pin {self.gpio_pin} OFF - Reason: {reason}")
                print(f"🔒 DOOR LOCKED - Reason: {reason}")
                return True
            else:
                # Simulation mode
                self.lock_state = "LOCKED"
                logger.info(f"🔒 [SIMULATION] DOOR LOCKED - Reason: {reason}")
                print(f"🔒 [SIMULATION] DOOR LOCKED - Reason: {reason}")
                return True
        except Exception as e:
            logger.error(f"Failed to lock door: {e}")
            print(f"❌ Failed to lock door: {e}")
            return False
    
    def get_lock_status(self) -> str:
        """
        Get current lock status
        
        Returns:
            str: Current lock state ("LOCKED" or "UNLOCKED")
        """
        if self.lock is not None:
            actual_state = "UNLOCKED" if self.lock.is_lit else "LOCKED"
            return actual_state
        else:
            return self.lock_state
    
    def test_lock_cycle(self, cycles: int = 3, delay: float = 2.0) -> None:
        """
        Test the lock by cycling it on and off
        
        Args:
            cycles: Number of lock/unlock cycles to perform
            delay: Delay between state changes in seconds
        """
        print(f"Starting lock test cycle - {cycles} cycles with {delay}s delays...")
        
        for i in range(cycles):
            print(f"\n--- Test Cycle {i+1}/{cycles} ---")
            
            # Unlock
            self.unlock_door("TEST")
            time.sleep(delay)
            
            # Lock
            self.lock_door("Test cycle")
            time.sleep(delay)
        
        print("\nLock test cycle completed!")
        print(f"Final status: {self.get_lock_status()}")
    
    def auto_lock_after_delay(self, delay_seconds: float = 5.0) -> None:
        """
        Automatically lock the door after a delay
        
        Args:
            delay_seconds: Time to wait before locking (in seconds)
        """
        if self.get_lock_status() == "UNLOCKED":
            logger.info(f"Auto-lock scheduled in {delay_seconds} seconds")
            print(f"⏰ Door will auto-lock in {delay_seconds} seconds")
            time.sleep(delay_seconds)
            self.lock_door("Auto-lock timeout")
    
    def cleanup(self) -> None:
        """Clean up GPIO resources and ensure door is locked"""
        try:
            self.lock_door("Cleanup/Shutdown")
            if self.lock is not None:
                # GPIO cleanup is handled automatically by gpiozero
                logger.info("GPIO lock controller cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Manual control functions for testing
def manual_lock_control():
    """Manual control interface for testing the lock"""
    print("="*50)
    print("        MANUAL LOCK CONTROL")
    print("="*50)
    
    controller = GPIOLockController()
    
    print("\nCommands:")
    print("  'unlock' or 'on' - Unlock the door")
    print("  'lock' or 'off' - Lock the door")
    print("  'status' - Check current lock status")
    print("  'test' - Run automatic test cycle")
    print("  'auto' - Test auto-lock feature")
    print("  'quit' or 'q' - Exit")
    print()
    
    try:
        while True:
            try:
                command = input("Enter command: ").lower().strip()
                
                if command in ['unlock', 'on']:
                    controller.unlock_door("Manual Control")
                elif command in ['lock', 'off']:
                    controller.lock_door("Manual command")
                elif command == 'status':
                    status = controller.get_lock_status()
                    print(f"Lock status: {status}")
                elif command == 'test':
                    controller.test_lock_cycle()
                elif command == 'auto':
                    print("Unlocking door and testing auto-lock in 3 seconds...")
                    controller.unlock_door("Auto-lock test")
                    controller.auto_lock_after_delay(3.0)
                elif command in ['quit', 'q']:
                    break
                else:
                    print("Invalid command. Try 'unlock', 'lock', 'status', 'test', 'auto', or 'quit'")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    finally:
        controller.cleanup()
        print("\nExiting manual control...")

if __name__ == "__main__":
    manual_lock_control() 