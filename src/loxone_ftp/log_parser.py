import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class TemperatureReading:
    """Data class for temperature readings"""

    def __init__(self, timestamp: datetime, temperature: float, sensor_name: str = None):
        """
        Initialize temperature reading.

        Args:
            timestamp: Time of reading
            temperature: Temperature value
            sensor_name: Optional name of temperature sensor
        """
        self.timestamp = timestamp
        self.temperature = temperature
        self.sensor_name = sensor_name

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'temperature': self.temperature,
            'sensor_name': self.sensor_name,
        }

    def __repr__(self) -> str:
        return f"TemperatureReading(timestamp={self.timestamp}, temperature={self.temperature}°C, sensor={self.sensor_name})"


class LogParser:
    """Parser for Loxone temperature log files"""

    # Common Loxone log formats
    # Format 1: YYYY-MM-DD HH:MM:SS,temperature
    PATTERN_STANDARD = r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})[,\s]+(-?\d+\.?\d*)'

    # Format 2: DD.MM.YYYY HH:MM:SS,temperature (European format)
    PATTERN_EU = r'(\d{2}\.\d{2}\.\d{4}\s\d{2}:\d{2}:\d{2})[,\s]+(-?\d+\.?\d*)'

    # Format 3: Timestamp in milliseconds or unix timestamp
    PATTERN_UNIX = r'(\d{10,13})[,\s]+(-?\d+\.?\d*)'

    # Format 4: CSV with header (sensor_name,timestamp,temperature)
    PATTERN_CSV = r'([^,]*?)\s*,\s*(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*,\s*(-?\d+\.?\d*)'

    DATETIME_FORMATS = [
        '%Y-%m-%d %H:%M:%S',
        '%d.%m.%Y %H:%M:%S',
    ]

    def __init__(self):
        """Initialize log parser"""
        self.compiled_patterns = {
            'standard': re.compile(self.PATTERN_STANDARD),
            'eu': re.compile(self.PATTERN_EU),
            'unix': re.compile(self.PATTERN_UNIX),
            'csv': re.compile(self.PATTERN_CSV),
        }

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """
        Parse timestamp string in various formats.

        Args:
            timestamp_str: Timestamp string to parse

        Returns:
            datetime object or None if parsing fails
        """
        # Try standard formats first
        for fmt in self.DATETIME_FORMATS:
            try:
                return datetime.strptime(timestamp_str.strip(), fmt)
            except ValueError:
                continue

        # Try unix timestamp
        try:
            timestamp_int = int(timestamp_str)
            # Check if it's milliseconds (13 digits) or seconds (10 digits)
            if timestamp_int > 9999999999:
                return datetime.fromtimestamp(timestamp_int / 1000)
            else:
                return datetime.fromtimestamp(timestamp_int)
        except (ValueError, OSError):
            pass

        logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return None

    def _parse_temperature(self, temp_str: str) -> Optional[float]:
        """
        Parse temperature value.

        Args:
            temp_str: Temperature string

        Returns:
            float value or None if parsing fails
        """
        try:
            return float(temp_str.strip())
        except ValueError:
            logger.warning(f"Could not parse temperature: {temp_str}")
            return None

    def parse_line_standard(self, line: str) -> Optional[TemperatureReading]:
        """
        Parse line in standard format (YYYY-MM-DD HH:MM:SS,temperature).

        Args:
            line: Line from log file

        Returns:
            TemperatureReading or None if parsing fails
        """
        match = self.compiled_patterns['standard'].search(line)
        if not match:
            return None

        timestamp_str, temp_str = match.groups()
        timestamp = self._parse_timestamp(timestamp_str)
        temperature = self._parse_temperature(temp_str)

        if timestamp and temperature is not None:
            return TemperatureReading(timestamp, temperature)
        return None

    def parse_line_eu(self, line: str) -> Optional[TemperatureReading]:
        """
        Parse line in EU format (DD.MM.YYYY HH:MM:SS,temperature).

        Args:
            line: Line from log file

        Returns:
            TemperatureReading or None if parsing fails
        """
        match = self.compiled_patterns['eu'].search(line)
        if not match:
            return None

        timestamp_str, temp_str = match.groups()
        timestamp = self._parse_timestamp(timestamp_str)
        temperature = self._parse_temperature(temp_str)

        if timestamp and temperature is not None:
            return TemperatureReading(timestamp, temperature)
        return None

    def parse_line_csv(self, line: str) -> Optional[TemperatureReading]:
        """
        Parse CSV format line (sensor_name,timestamp,temperature).

        Args:
            line: Line from log file

        Returns:
            TemperatureReading or None if parsing fails
        """
        match = self.compiled_patterns['csv'].search(line)
        if not match:
            return None

        sensor_name, timestamp_str, temp_str = match.groups()
        timestamp = self._parse_timestamp(timestamp_str)
        temperature = self._parse_temperature(temp_str)

        if timestamp and temperature is not None:
            return TemperatureReading(
                timestamp,
                temperature,
                sensor_name=sensor_name if sensor_name else None
            )
        return None

    def parse_line(self, line: str, sensor_name: str = None) -> Optional[TemperatureReading]:
        """
        Attempt to parse line using all known formats.

        Args:
            line: Line from log file
            sensor_name: Optional sensor name to attach to reading

        Returns:
            TemperatureReading or None if parsing fails
        """
        if not line or line.startswith('#'):
            return None

        # Try CSV format first (includes sensor name)
        reading = self.parse_line_csv(line)
        if reading:
            return reading

        # Try standard format
        reading = self.parse_line_standard(line)
        if reading:
            if sensor_name:
                reading.sensor_name = sensor_name
            return reading

        # Try EU format
        reading = self.parse_line_eu(line)
        if reading:
            if sensor_name:
                reading.sensor_name = sensor_name
            return reading

        return None

    def parse_file(self, file_path: str) -> List[TemperatureReading]:
        """
        Parse entire log file.

        Args:
            file_path: Path to log file

        Returns:
            List of TemperatureReading objects
        """
        readings = []
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return readings

        sensor_name = file_path.stem  # Use filename without extension as sensor name

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    reading = self.parse_line(line, sensor_name)
                    if reading:
                        readings.append(reading)
                    else:
                        logger.debug(f"Could not parse line {line_num} in {file_path.name}")

            logger.info(f"Parsed {len(readings)} temperature readings from {file_path.name}")
            return readings

        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return readings

    def parse_files(self, file_paths: List[str]) -> Dict[str, List[TemperatureReading]]:
        """
        Parse multiple log files.

        Args:
            file_paths: List of paths to log files

        Returns:
            Dictionary mapping filenames to lists of TemperatureReading objects
        """
        results = {}
        for file_path in file_paths:
            readings = self.parse_file(file_path)
            filename = Path(file_path).name
            results[filename] = readings

        return results

    @staticmethod
    def get_temperature_statistics(readings: List[TemperatureReading]) -> Dict:
        """
        Calculate statistics for temperature readings.

        Args:
            readings: List of TemperatureReading objects

        Returns:
            Dictionary with min, max, avg, and count
        """
        if not readings:
            return {
                'count': 0,
                'min': None,
                'max': None,
                'average': None,
            }

        temperatures = [r.temperature for r in readings]
        return {
            'count': len(readings),
            'min': min(temperatures),
            'max': max(temperatures),
            'average': sum(temperatures) / len(temperatures),
        }
