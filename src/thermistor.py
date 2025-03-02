import sys
import time
import json
import logging
from ADCPi import ADCPi

import numpy as np

from os.path import dirname, join
from typing import Dict, List

from src.config import Config

logger = logging.getLogger('vivarium')


class ThermistorManager:
    """Manages thermistor sensors to read temperature"""
    
    def __init__(self, config: Config):
        """Initialize the thermistor manager
        
        Args:
            config: Configuration object with thermistor settings
        """
        self.config = config
        self.thermistor_config = config.config['thermistors']
        
        # Initialize ADC
        self.adc = ADCPi(
            self.thermistor_config['adc_address1'],
            self.thermistor_config['adc_address2'],
            self.thermistor_config['bit_rate']
        )
        
        # Load thermistor calibration data
        self.calibration = self._load_calibration(
            self.thermistor_config['calibration_file']
        )
    
    def _load_calibration(self, calibration_file: str) -> Dict[str, np.ndarray]:
        """Load thermistor calibration data from file
        
        Args:
            calibration_file: Path to the calibration JSON file
            
        Returns:
            Dictionary with calibration data
        """
        try:
            calibration_path = join(dirname(__file__), calibration_file)
            with open(calibration_path, 'r') as f:
                data = json.load(f)

            # Convert lists to numpy arrays for efficient computation
            data['temps'] = np.array(data['temps'])
            data['voltages'] = np.array(data['voltages'])
            return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load thermistor calibration: {e}")
            sys.exit(1)
    
    def take_readings(self, num_samples: int = 1) -> List[List[float]]:
        """Take temperature readings from all sensors
        
        Args:
            num_samples: Number of readings to take per sensor
            
        Returns:
            List of readings, each reading contains values from all sensors
        """
        readings = []
        
        for _ in range(num_samples):
            sample = []
            for i in range(4):  # Assuming 4 sensors
                voltage = self.adc.read_voltage(i + 1)
                temperature = self._volts_to_centigrade(voltage, i)
                sample.append(temperature)
            
            readings.append(sample)
            if num_samples > 1:
                time.sleep(1)  # Wait between samples
                
        return readings
    
    def _volts_to_centigrade(self, volts: float, sensor_num: int) -> float:
        """Convert voltage reading to temperature in Celsius
        
        Args:
            volts: Voltage reading from the sensor
            sensor_num: Sensor number (0-3)
            
        Returns:
            Temperature in Celsius
        """
        x = self.calibration['voltages'][sensor_num]
        y = self.calibration['temps']
        return float(np.interp(volts, x, y))
    
    @staticmethod
    def calculate_median(temperatures: List[float]) -> float:
        """Calculate the median temperature from a list of readings
        
        Args:
            temperatures: List of temperature readings
            
        Returns:
            Median temperature
        """
        sorted_temps = sorted(temperatures)
        n = len(sorted_temps)
        
        if n % 2 == 0:
            middle1 = sorted_temps[n // 2 - 1]
            middle2 = sorted_temps[n // 2]
            return (middle1 + middle2) / 2
        else:
            return sorted_temps[n // 2]

