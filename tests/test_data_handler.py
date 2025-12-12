import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from src.loxone_ftp.data_handler import DataHandler
from src.loxone_ftp.log_parser import TemperatureReading


class TestDataHandler:
    """Test cases for DataHandler"""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for tests"""
        with tempfile.TemporaryDirectory() as storage_dir:
            with tempfile.TemporaryDirectory() as processed_dir:
                yield storage_dir, processed_dir

    @pytest.fixture
    def handler(self, temp_dirs):
        """Create data handler instance"""
        storage_dir, processed_dir = temp_dirs
        return DataHandler(
            storage_path=storage_dir,
            processed_path=processed_dir,
        )

    def test_initialization(self, handler, temp_dirs):
        """Test handler initialization"""
        storage_dir, processed_dir = temp_dirs
        assert Path(storage_dir).exists()
        assert Path(processed_dir).exists()

    def test_load_metadata_no_file(self, handler):
        """Test loading metadata when file doesn't exist"""
        metadata = handler._load_metadata()

        assert 'last_processed' in metadata
        assert 'processed_files' in metadata
        assert metadata['last_processed'] is None
        assert metadata['processed_files'] == {}

    def test_save_and_load_metadata(self, handler):
        """Test saving and loading metadata"""
        metadata = {
            'last_processed': '2025-01-01T12:00:00',
            'processed_files': {
                'temp_01.txt': {
                    'processed_at': '2025-01-01T12:00:00',
                    'count': 100,
                }
            }
        }

        handler._save_metadata(metadata)
        loaded = handler._load_metadata()

        assert loaded['last_processed'] == metadata['last_processed']
        assert 'temp_01.txt' in loaded['processed_files']

    def test_get_processed_files(self, handler):
        """Test getting processed files list"""
        metadata = {
            'last_processed': None,
            'processed_files': {
                'temp_01.txt': {'count': 100},
                'temp_02.txt': {'count': 50},
            }
        }
        handler._save_metadata(metadata)

        processed = handler.get_processed_files()

        assert len(processed) == 2
        assert 'temp_01.txt' in processed

    def test_get_new_files(self, handler):
        """Test filtering new files"""
        metadata = {
            'last_processed': None,
            'processed_files': {
                'processed_01.txt': {'count': 100},
            }
        }
        handler._save_metadata(metadata)

        log_files = [
            '/data/processed_01.txt',
            '/data/new_01.txt',
            '/data/new_02.txt',
        ]

        new_files = handler.get_new_files(log_files)

        assert len(new_files) == 2
        assert '/data/processed_01.txt' not in new_files

    def test_process_log_file(self, handler):
        """Test processing single log file"""
        # Create test log file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('2025-01-01 12:00:00, 20.0\n')
            f.write('2025-01-01 13:00:00, 21.0\n')
            temp_file = f.name

        try:
            result = handler.process_log_file(temp_file)

            assert result['count'] == 2
            assert len(result['readings']) == 2
            assert result['readings'][0]['temperature'] == 20.0
        finally:
            Path(temp_file).unlink()

    def test_process_log_file_updates_metadata(self, handler):
        """Test that processing file updates metadata"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='temp_test.txt', delete=False) as f:
            f.write('2025-01-01 12:00:00, 20.0\n')
            temp_file = f.name

        try:
            handler.process_log_file(temp_file)
            processed = handler.get_processed_files()

            assert Path(temp_file).name in processed
        finally:
            Path(temp_file).unlink()

    def test_process_log_files(self, handler):
        """Test processing multiple log files"""
        files = []

        for i in range(2):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f'2025-01-01 12:00:00, {20.0 + i}\n')
                files.append(f.name)

        try:
            results = handler.process_log_files(files)

            assert len(results) == 2
            for filename, data in results.items():
                assert 'readings' in data
        finally:
            for f in files:
                Path(f).unlink()

    def test_save_processed_data(self, handler):
        """Test saving processed data"""
        data = {
            'files_processed': {'temp_01.txt': {'count': 10}},
            'all_readings': [
                {'timestamp': '2025-01-01T12:00:00', 'temperature': 20.0},
            ]
        }

        output_file = handler.save_processed_data(data, 'test_output.json')

        assert Path(output_file).exists()
        with open(output_file, 'r') as f:
            loaded = json.load(f)
        assert loaded == data

    def test_save_processed_data_auto_filename(self, handler):
        """Test saving with auto-generated filename"""
        data = {'readings': []}

        output_file = handler.save_processed_data(data)

        assert 'temperature_data_' in output_file
        assert output_file.endswith('.json')
        assert Path(output_file).exists()

    def test_load_processed_data(self, handler):
        """Test loading processed data"""
        data = {'test': 'data'}
        handler.save_processed_data(data, 'test_load.json')

        loaded = handler.load_processed_data('test_load.json')

        assert loaded == data

    def test_load_processed_data_not_found(self, handler):
        """Test loading non-existent file"""
        loaded = handler.load_processed_data('nonexistent.json')

        assert loaded == {}

    def test_get_combined_temperature_data(self, handler):
        """Test combining temperature data from multiple files"""
        files = []

        for i in range(2):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f'2025-01-01 12:0{i}:00, {20.0 + i}\n')
                f.write(f'2025-01-01 13:0{i}:00, {21.0 + i}\n')
                files.append(f.name)

        try:
            combined = handler.get_combined_temperature_data(files)

            assert 'all_readings' in combined
            assert len(combined['all_readings']) == 4
            assert combined['total_readings'] == 4
        finally:
            for f in files:
                Path(f).unlink()

    def test_cleanup_old_logs(self, handler):
        """Test cleanup of old log files"""
        # Create test files
        old_file = handler.storage_path / 'old.log'
        old_file.touch()

        # Mock file modification time to be old
        import os
        from datetime import timedelta
        old_time = (datetime.now() - timedelta(days=31)).timestamp()
        os.utime(old_file, (old_time, old_time))

        count = handler.cleanup_old_logs(keep_days=30)

        assert count == 1
        assert not old_file.exists()

    def test_cleanup_keeps_recent_logs(self, handler):
        """Test that recent logs are not cleaned up"""
        recent_file = handler.storage_path / 'recent.log'
        recent_file.touch()

        count = handler.cleanup_old_logs(keep_days=30)

        assert count == 0
        assert recent_file.exists()

    def test_get_storage_info(self, handler):
        """Test getting storage information"""
        # Create test files
        (handler.storage_path / 'test.log').touch()
        (handler.processed_path / 'test.json').touch()

        info = handler.get_storage_info()

        assert 'storage_path' in info
        assert 'processed_path' in info
        assert info['log_files_count'] >= 1
        assert info['processed_files_count'] >= 1
