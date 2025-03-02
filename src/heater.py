import sys
import math
import logging
import RPi.GPIO as GPIO

from typing import Any, Dict
from datetime import datetime
from os.path import dirname

PROJ_ROOT = dirname(dirname(dirname(dirname(__file__))))
sys.path.append(PROJ_ROOT)

from config import Config
from src.config import DeviceState
from src.thermistor import ThermistorManager

logger = logging.getLogger('vivarium')


class Heater:
    """Controls the vivarium heating system"""
    
    def __init__(self, config: Config):
        """Initialize the heater controller
        
        Args:
            config: Configuration object with heater settings
        """
        self.config = config
        self.heater_config = config.config['heater']
        self.pins = self.heater_config['pins']
        self.deadzone = self.heater_config['deadzone']
        self.daycycle = self.heater_config['daycycle']
        
        self.state = DeviceState.UNKNOWN
        self.last_change = datetime(2000, 1, 1)
        
        # Initialize GPIO pins
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
    
    def set_power(self, power: bool) -> None:
        """Set the heater power state
        
        Args:
            power: True to turn heater on, False to turn it off
        """
        new_state = DeviceState.ON if power else DeviceState.OFF
        
        if new_state != self.state:
            logger.info(f"Setting heater to {power}")
            
            # GPIO.LOW turns the relay ON, GPIO.HIGH turns it OFF (inverted logic)
            output_value = GPIO.LOW if power else GPIO.HIGH
            
            for pin in self.pins:
                GPIO.output(pin, output_value)
                
            self.state = new_state
            self.last_change = datetime.now()
    
    def update_by_temperature(self, thermistor_manager: ThermistorManager) -> Dict[str, Any]:
        """Update heater state based on current temperature and target
        
        Args:
            thermistor_manager: ThermistorManager instance to get temperature readings
            
        Returns:
            Dictionary with temperature data and heater state for logging
        """
        # Get temperature readings
        readings = thermistor_manager.take_readings(1)[0]
        
        # Calculate target temperature based on time of day
        now = datetime.now()
        target_temp = self._calculate_target_temp(now)
        
        # Filter out any faulty readings (e.g., exactly 13 degrees)
        valid_readings = [r for r in readings if r != 13]
        if not valid_readings:
            logger.warning("No valid temperature readings")
            return {
                'temperatures': readings,
                'median_temp': None,
                'target_temp': target_temp,
                'heater_state': self.state.value
            }
        
        median_temp = thermistor_manager.calculate_median(valid_readings)
        power_needed = median_temp < target_temp
        
        # Check if we're in the deadzone
        time_since_change = (datetime.now() - self.last_change).total_seconds()
        in_temp_deadzone = abs(median_temp - target_temp) < self.deadzone['temp']
        in_time_deadzone = time_since_change < self.deadzone['time']
        
        # Only change state if we're outside the deadzone or initializing
        if (not (in_temp_deadzone or in_time_deadzone)) or self.state == DeviceState.UNKNOWN:
            self.set_power(power_needed)
        
        # Return data for logging
        return {
            'temperatures': readings,
            'median_temp': median_temp,
            'target_temp': target_temp,
            'heater_state': self.state.value
        }
    
    def _calculate_target_temp(self, time: datetime) -> float:
        """Calculate target temperature based on time of day
        
        Args:
            time: Current datetime
            
        Returns:
            Target temperature in Celsius
        """
        # Extract parameters
        avg_temp = self.daycycle['avgT']
        delta_temp = self.daycycle['deltaT']
        coldest_hour = self.daycycle['coldest_hour']
        
        # Calculate time angle (time of day in radians)
        now_hour = time.hour + time.minute / 60
        angular_time = ((now_hour - coldest_hour) % 24) / 12 * math.pi
        
        # Calculate temperature using cosine curve
        target = avg_temp - (math.cos(angular_time) * delta_temp)
        return target
