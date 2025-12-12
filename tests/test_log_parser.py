import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.loxone_ftp.log_parser import LogParser, TemperatureReading


class TestTemperatureReading:
    """Test cases for TemperatureReading"""

    def test_creation(self):
        """Test creating temperature reading"""
        ts = datetime(2025, 1, 1, 12, 0, 0)
        reading = TemperatureReading(ts, 22.5)

        assert reading.timestamp == ts
        assert reading.temperature == 22.5
        assert reading.sensor_name is None

    def test_creation_with_sensor_name(self):
        """Test creating temperature reading with sensor name"""
        ts = datetime(2025, 1, 1, 12, 0, 0)
        reading = TemperatureReading(ts, 22.5, sensor_name='livingroom')

        assert reading.sensor_name == 'livingroom'

    def test_to_dict(self):
        """Test converting to dictionary"""
        ts = datetime(2025, 1, 1, 12, 0, 0)
        reading = TemperatureReading(ts, 22.5, sensor_name='room1')
        data = reading.to_dict()

        assert data['temperature'] == 22.5
        assert data['sensor_name'] == 'room1'
        assert 'timestamp' in data

    def test_repr(self):
        """Test string representation"""
        ts = datetime(2025, 1, 1, 12, 0, 0)
        reading = TemperatureReading(ts, 22.5)
        repr_str = repr(reading)

        assert 'TemperatureReading' in repr_str
        assert '22.5' in repr_str


class TestLogParser:
    """Test cases for LogParser"""

    @pytest.fixture
    def parser(self):
        """Create log parser instance"""
        return LogParser()

    def test_initialization(self, parser):
        """Test parser initialization"""
        assert parser is not None
        assert 'standard' in parser.compiled_patterns
        assert 'eu' in parser.compiled_patterns

    def test_parse_timestamp_iso_format(self, parser):
        """Test parsing ISO timestamp format"""
        ts = parser._parse_timestamp('2025-01-01 12:30:45')
        assert ts is not None
        assert ts.year == 2025
        assert ts.month == 1
        assert ts.day == 1
        assert ts.hour == 12

    def test_parse_timestamp_eu_format(self, parser):
        """Test parsing EU timestamp format"""
        ts = parser._parse_timestamp('01.01.2025 12:30:45')
        assert ts is not None
        assert ts.year == 2025
        assert ts.month == 1

    def test_parse_timestamp_invalid(self, parser):
        """Test parsing invalid timestamp"""
        ts = parser._parse_timestamp('invalid')
        assert ts is None

    def test_parse_temperature_float(self, parser):
        """Test parsing float temperature"""
        temp = parser._parse_temperature('22.5')
        assert temp == 22.5

    def test_parse_temperature_int(self, parser):
        """Test parsing integer temperature"""
        temp = parser._parse_temperature('22')
        assert temp == 22.0

    def test_parse_temperature_negative(self, parser):
        """Test parsing negative temperature"""
        temp = parser._parse_temperature('-5.3')
        assert temp == -5.3

    def test_parse_temperature_invalid(self, parser):
        """Test parsing invalid temperature"""
        temp = parser._parse_temperature('invalid')
        assert temp is None

    def test_parse_line_standard_format(self, parser):
        """Test parsing standard format line"""
        line = '2025-01-01 12:30:45, 22.5'
        reading = parser.parse_line_standard(line)

        assert reading is not None
        assert reading.temperature == 22.5
        assert reading.timestamp.year == 2025

    def test_parse_line_eu_format(self, parser):
        """Test parsing EU format line"""
        line = '01.01.2025 12:30:45, 22.5'
        reading = parser.parse_line_eu(line)

        assert reading is not None
        assert reading.temperature == 22.5

    def test_parse_line_csv_format(self, parser):
        """Test parsing CSV format line"""
        line = 'livingroom, 2025-01-01 12:30:45, 22.5'
        reading = parser.parse_line_csv(line)

        assert reading is not None
        assert reading.temperature == 22.5
        assert reading.sensor_name == 'livingroom'

    def test_parse_line_with_sensor_name(self, parser):
        """Test parse_line with explicit sensor name"""
        line = '2025-01-01 12:30:45, 22.5'
        reading = parser.parse_line(line, sensor_name='kitchen')

        assert reading is not None
        assert reading.sensor_name == 'kitchen'

    def test_parse_line_skips_comments(self, parser):
        """Test that comments are skipped"""
        line = '# This is a comment'
        reading = parser.parse_line(line)

        assert reading is None

    def test_parse_line_empty_line(self, parser):
        """Test that empty lines are skipped"""
        reading = parser.parse_line('')
        assert reading is None

    def test_parse_file(self, parser):
        """Test parsing complete log file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('# Temperature log\n')
            f.write('2025-01-01 12:00:00, 20.0\n')
            f.write('2025-01-01 13:00:00, 21.5\n')
            f.write('2025-01-01 14:00:00, 22.0\n')
            temp_file = f.name

        try:
            readings = parser.parse_file(temp_file)

            assert len(readings) == 3
            assert readings[0].temperature == 20.0
            assert readings[1].temperature == 21.5
            assert readings[2].temperature == 22.0
        finally:
            Path(temp_file).unlink()

    def test_parse_file_not_found(self, parser):
        """Test parsing non-existent file"""
        readings = parser.parse_file('/nonexistent/file.txt')
        assert len(readings) == 0

    def test_parse_file_empty(self, parser):
        """Test parsing empty file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_file = f.name

        try:
            readings = parser.parse_file(temp_file)
            assert len(readings) == 0
        finally:
            Path(temp_file).unlink()

    def test_parse_files(self, parser):
        """Test parsing multiple files"""
        files = []

        for i in range(2):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f'2025-01-01 12:00:00, {20.0 + i}\n')
                files.append(f.name)

        try:
            results = parser.parse_files(files)

            assert len(results) == 2
            for filename, readings in results.items():
                assert len(readings) == 1
        finally:
            for f in files:
                Path(f).unlink()

    def test_get_temperature_statistics(self):
        """Test temperature statistics calculation"""
        readings = [
            TemperatureReading(datetime.now(), 20.0),
            TemperatureReading(datetime.now(), 25.0),
            TemperatureReading(datetime.now(), 22.5),
        ]

        stats = LogParser.get_temperature_statistics(readings)

        assert stats['count'] == 3
        assert stats['min'] == 20.0
        assert stats['max'] == 25.0
        assert stats['average'] == pytest.approx(22.5)

    def test_get_temperature_statistics_empty(self):
        """Test statistics for empty list"""
        stats = LogParser.get_temperature_statistics([])

        assert stats['count'] == 0
        assert stats['min'] is None
        assert stats['max'] is None
        assert stats['average'] is None

    def test_parse_mixed_formats(self, parser):
        """Test parsing file with mixed formats"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('2025-01-01 12:00:00, 20.0\n')
            f.write('01.01.2025 13:00:00, 21.0\n')
            f.write('sensor1, 2025-01-01 14:00:00, 22.0\n')
            temp_file = f.name

        try:
            readings = parser.parse_file(temp_file)
            assert len(readings) == 3
        finally:
            Path(temp_file).unlink()
