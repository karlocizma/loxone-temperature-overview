import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from .log_parser import LogParser, TemperatureReading

logger = logging.getLogger(__name__)


class DataHandler:
    """Handler for managing downloaded and processed temperature data"""

    METADATA_FILE = '.metadata.json'
    PROCESSED_EXTENSION = '.processed.json'

    def __init__(self, storage_path: str = "./data/logs", processed_path: str = "./data/processed"):
        """
        Initialize data handler.

        Args:
            storage_path: Path to directory with downloaded log files
            processed_path: Path to directory for processed data
        """
        self.storage_path = Path(storage_path)
        self.processed_path = Path(processed_path)
        self.parser = LogParser()

        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.storage_path / self.METADATA_FILE

    def _load_metadata(self) -> Dict:
        """
        Load processing metadata.

        Returns:
            Dictionary with metadata about processed files
        """
        if not self.metadata_file.exists():
            return {
                'last_processed': None,
                'processed_files': {},
            }

        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            return {
                'last_processed': None,
                'processed_files': {},
            }

    def _save_metadata(self, metadata: Dict) -> None:
        """
        Save processing metadata.

        Args:
            metadata: Dictionary with metadata to save
        """
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            logger.info("Metadata saved")
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def get_processed_files(self) -> Dict[str, Dict]:
        """
        Get list of already processed files with their metadata.

        Returns:
            Dictionary mapping filenames to processing metadata
        """
        metadata = self._load_metadata()
        return metadata.get('processed_files', {})

    def get_new_files(self, log_files: List[str]) -> List[str]:
        """
        Filter list of log files to return only those not yet processed.

        Args:
            log_files: List of log file paths

        Returns:
            List of paths for files not yet processed
        """
        processed = self.get_processed_files()
        new_files = []

        for log_file in log_files:
            filename = Path(log_file).name
            if filename not in processed:
                new_files.append(log_file)

        logger.info(f"Found {len(new_files)} unprocessed files out of {len(log_files)}")
        return new_files

    def process_log_file(self, log_file_path: str) -> Dict[str, List[dict]]:
        """
        Process a single log file and extract temperature data.

        Args:
            log_file_path: Path to log file to process

        Returns:
            Dictionary with processed temperature data
        """
        file_path = Path(log_file_path)
        filename = file_path.name

        logger.info(f"Processing log file: {filename}")

        # Parse log file
        readings = self.parser.parse_file(log_file_path)

        if not readings:
            logger.warning(f"No temperature readings found in {filename}")
            return {'readings': [], 'file': filename, 'count': 0}

        # Convert readings to dictionaries
        data = {
            'file': filename,
            'processed_at': datetime.now().isoformat(),
            'count': len(readings),
            'readings': [r.to_dict() for r in readings],
        }

        # Update metadata
        metadata = self._load_metadata()
        metadata['processed_files'][filename] = {
            'processed_at': datetime.now().isoformat(),
            'count': len(readings),
            'file_path': str(log_file_path),
        }
        metadata['last_processed'] = datetime.now().isoformat()
        self._save_metadata(metadata)

        return data

    def process_log_files(self, log_files: List[str]) -> Dict[str, Dict]:
        """
        Process multiple log files.

        Args:
            log_files: List of paths to log files

        Returns:
            Dictionary mapping filenames to processed data
        """
        results = {}

        for log_file in log_files:
            try:
                data = self.process_log_file(log_file)
                filename = Path(log_file).name
                results[filename] = data
            except Exception as e:
                logger.error(f"Error processing {log_file}: {e}")
                continue

        return results

    def save_processed_data(
        self,
        data: Dict,
        output_filename: str = None
    ) -> str:
        """
        Save processed temperature data to file.

        Args:
            data: Dictionary with processed data
            output_filename: Name of output file (default: auto-generated)

        Returns:
            Path to saved file
        """
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"temperature_data_{timestamp}.json"

        output_path = self.processed_path / output_filename

        try:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Processed data saved to {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error saving processed data: {e}")
            raise

    def load_processed_data(self, filename: str) -> Dict:
        """
        Load previously processed temperature data.

        Args:
            filename: Name of file to load

        Returns:
            Dictionary with processed data
        """
        file_path = self.processed_path / filename

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return {}

        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading processed data: {e}")
            return {}

    def get_combined_temperature_data(self, log_files: List[str]) -> Dict:
        """
        Process multiple log files and combine all temperature data.

        Args:
            log_files: List of paths to log files

        Returns:
            Dictionary with combined temperature readings from all files
        """
        combined_data = {
            'generated_at': datetime.now().isoformat(),
            'files_processed': {},
            'all_readings': [],
        }

        for log_file in log_files:
            try:
                filename = Path(log_file).name
                readings = self.parser.parse_file(log_file)

                if readings:
                    reading_dicts = [r.to_dict() for r in readings]
                    combined_data['files_processed'][filename] = {
                        'count': len(reading_dicts),
                    }
                    combined_data['all_readings'].extend(reading_dicts)

            except Exception as e:
                logger.error(f"Error processing {log_file}: {e}")
                continue

        # Sort all readings by timestamp
        try:
            combined_data['all_readings'].sort(
                key=lambda x: x['timestamp']
            )
        except Exception as e:
            logger.warning(f"Could not sort readings: {e}")

        combined_data['total_readings'] = len(combined_data['all_readings'])

        return combined_data

    def cleanup_old_logs(self, keep_days: int = 30) -> int:
        """
        Remove log files older than specified number of days.

        Args:
            keep_days: Number of days to keep (default: 30)

        Returns:
            Number of files removed
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=keep_days)
        removed_count = 0

        for log_file in self.storage_path.glob('*.log'):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed old log file: {log_file.name}")
            except Exception as e:
                logger.error(f"Error removing {log_file}: {e}")

        logger.info(f"Cleaned up {removed_count} old log files")
        return removed_count

    def get_storage_info(self) -> Dict:
        """
        Get information about stored data.

        Returns:
            Dictionary with storage information
        """
        log_files = list(self.storage_path.glob('*'))
        log_files = [f for f in log_files if f.is_file() and f.name != self.METADATA_FILE]

        processed_files = list(self.processed_path.glob('*.json'))

        return {
            'storage_path': str(self.storage_path),
            'processed_path': str(self.processed_path),
            'log_files_count': len(log_files),
            'processed_files_count': len(processed_files),
            'metadata_available': self.metadata_file.exists(),
        }
