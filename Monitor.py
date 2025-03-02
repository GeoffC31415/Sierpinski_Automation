#!/usr/bin/env python3
"""
Vivarium Environment Controller

This module provides automated control for a vivarium environment,
managing temperature and lighting based on time of day and sensor readings.
"""
import sys
import time
import logging
import traceback

import RPi.GPIO as GPIO

from datetime import datetime
from os import popen
from os.path import dirname, join
from typing import Optional

PROJ_ROOT = dirname(__file__)
sys.path.append(PROJ_ROOT)

from src.config import Config
from src.thermistor import ThermistorManager
from src.heater import Heater
from src.led_lighting import LEDController
from src.data_logger import DataLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(join(dirname(__file__), 'vivarium.log'))
    ]
)
logger = logging.getLogger('vivarium')

class VivariumController:
    """Main controller for the vivarium environment"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the vivarium controller
        
        Args:
            config_path: Optional path to a JSON configuration file
        """
        # Initialize configuration
        self.config = Config(config_path)
        
        # Set up GPIO
        GPIO.setmode(GPIO.BCM)
        
        # Initialize components
        self.thermistor_manager = ThermistorManager(self.config)
        self.heater = Heater(self.config)
        self.led_controller = LEDController(self.config)
        self.data_logger = DataLogger(self.config)
    
    def run(self) -> None:
        """Run the main control loop"""
        logger.info("Vivarium controller starting")
        
        try:
            while True:
                current_time = datetime.now()
                
                # Update heater based on temperature
                heater_data = self.heater.update_by_temperature(self.thermistor_manager)
                
                # Update LEDs based on time
                led_data = self.led_controller.update_by_time(current_time)
                
                # Log temperature data
                if heater_data['median_temp'] is not None:
                    self.data_logger.log_temperatures(
                        heater_data['temperatures'],
                        heater_data['median_temp']
                    )
                
                # Log other data fields
                self.data_logger.log_data({
                    'heater_state': heater_data['heater_state'],
                    'target_temp': heater_data['target_temp'],
                    'temp_pi': self._get_pi_temp(),
                    'light': led_data['light']
                })
                
                # Flush logs to InfluxDB
                self.data_logger.flush()
                
                # Wait for next cycle
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("Controller stopped by user")
        except Exception as e:
            logger.error(f"Error in controller: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Clean up
            self._cleanup()
    
    def _get_pi_temp(self) -> float:
        """Get the Raspberry Pi's CPU temperature
        
        Returns:
            CPU temperature in Celsius
        """
        try:
            temp = popen("vcgencmd measure_temp").readline()
            return float(temp[5:-3])
        except Exception as e:
            logger.error(f"Failed to get Pi temperature: {e}")
            return 0.0
    
    def _cleanup(self) -> None:
        """Clean up resources before exiting"""
        logger.info("Cleaning up")
        GPIO.cleanup()


def main():
    """Main entry point for the vivarium controller"""
    # Get config path from command line argument, if provided
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Create and run the controller
    controller = VivariumController(config_path)
    controller.run()


if __name__ == '__main__':
    main()
