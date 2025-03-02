import sys
import math
import logging
import wiringpi

from datetime import datetime, timedelta
from typing import Any, Dict
from os.path import dirname

PROJ_ROOT = dirname(dirname(dirname(dirname(__file__))))
sys.path.append(PROJ_ROOT)

from config import Config

logger = logging.getLogger('vivarium')

class LEDController:
    """Controls the vivarium LED lighting system"""
    
    def __init__(self, config: Config):
        """Initialize the LED controller
        
        Args:
            config: Configuration object with LED settings
        """
        self.config = config
        self.led_config = config.config['leds']
        self.pin = self.led_config['pin']
        self.sunrise = timedelta(hours=self.led_config['sunrise'])
        self.sunset = timedelta(hours=self.led_config['sunset'])
        
        self.brightness = 0
        
        # Initialize WiringPi for PWM
        wiringpi.wiringPiSetupGpio()
        wiringpi.pinMode(self.pin, 2)  # Set to PWM mode
        wiringpi.pwmWrite(self.pin, 0)  # Start with LEDs off
    
    def update_by_time(self, current_time: datetime) -> Dict[str, Any]:
        """Update LED brightness based on time of day
        
        Args:
            current_time: Current datetime
            
        Returns:
            Dictionary with LED state for logging
        """
        # Get current time as timedelta since midnight
        now = current_time - datetime(current_time.year, current_time.month, current_time.day)
        
        # Calculate day proportion (0 to 1) based on sunrise/sunset
        if now < self.sunrise or now > self.sunset:
            # Outside daylight hours
            day_prop = 0
        else:
            # During daylight hours
            day_prop = (now - self.sunrise) / (self.sunset - self.sunrise)
        
        # Use a sine curve raised to power of 3 for natural light curve
        # (gradual sunrise, steady day, gradual sunset)
        brightness_factor = max(0, math.sin(day_prop * math.pi)**3)
        
        # Scale for LED hardware (0-1024 for WiringPi PWM)
        new_brightness = int(1024 * brightness_factor + 0.5)
        
        # Only update if brightness changed
        if new_brightness != self.brightness:
            wiringpi.pwmWrite(self.pin, new_brightness)
            self.brightness = new_brightness
            logger.debug(f"Set LED brightness to {self.brightness}/1024")
        
        return {'light': self.brightness}
