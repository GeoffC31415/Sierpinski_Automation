import logging
import influx_handler

from typing import Any, Dict, List

from src.config import Config

logger = logging.getLogger('vivarium')

class DataLogger:
    """Handles logging data to InfluxDB"""
    
    def __init__(self, config: Config):
        """Initialize the data logger
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.measurement = config.config['data']['measurement_name']
        self.run_id = config.run_id
        self.pending_logs = []
    
    def log_data(self, fields: Dict[str, Any]) -> None:
        """Log data fields to the pending logs list
        
        Args:
            fields: Dictionary of fields to log
        """
        self.pending_logs.append({
            'measurement': self.measurement,
            'tags': {'run': self.run_id},
            'fields': fields
        })
    
    def log_temperatures(self, readings: List[float], median_temp: float) -> None:
        """Log temperature readings
        
        Args:
            readings: List of temperature readings
            median_temp: Median temperature
        """
        temps = {'temp' + str(i): r for i, r in enumerate(readings)}
        temps['temp_avg'] = median_temp
        self.log_data(temps)
    
    def flush(self) -> bool:
        """Send all pending logs to InfluxDB
        
        Returns:
            True if successful, False otherwise
        """
        if not self.pending_logs:
            return True
            
        success = influx_handler.write(self.pending_logs)
        
        if success:
            self.pending_logs = []
            return True
        else:
            logger.error("Problem writing sensor data to InfluxDB")
            return False
