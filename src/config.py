import json
import logging

from typing import Any, Dict, Optional
from enum import Enum

logger = logging.getLogger('vivarium')


class DeviceState(Enum):
    """Enum representing possible device states"""
    ON = True
    OFF = False
    UNKNOWN = None


class Config:
    """Configuration manager for the vivarium controller"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration with default or provided values
        
        Args:
            config_path: Optional path to a JSON configuration file
        """
        self.run_id = 'v1'
        self.verbose = True
        
        # Default configuration
        self.config: Dict[str, Any] = {
            'heater': {
                'pins': [17, 27],
                'deadzone': {
                    'temp': 0.1,
                    'time': 180
                },
                'daycycle': {
                    'avgT': 26,
                    'deltaT': 2,
                    'coldest_hour': 2
                }
            },
            'leds': {
                'pin': 18,
                'sunrise': 6,  # hour of day (0-23)
                'sunset': 20   # hour of day (0-23)
            },
            'thermistors': {
                'adc_address1': 0x68,
                'adc_address2': 0x69,
                'bit_rate': 18,
                'calibration_file': './data/thermistors.json'
            },
            'data': {
                'measurement_name': 'vivarium2'
            }
        }
        
        # Override with file configuration if provided
        if config_path:
            self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> None:
        """Load configuration from JSON file
        
        Args:
            config_path: Path to the JSON configuration file
        """
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                
            # Update the default config with values from file
            # This is a simple update, for nested dicts you may want a recursive update
            for key, value in file_config.items():
                if isinstance(value, dict) and key in self.config and isinstance(self.config[key], dict):
                    self.config[key].update(value)
                else:
                    self.config[key] = value
                    
            logger.info(f"Loaded configuration from {config_path}")
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load configuration: {e}")
            logger.warning("Using default configuration")