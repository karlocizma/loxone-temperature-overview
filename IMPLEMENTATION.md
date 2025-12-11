# Loxone FTP Client Implementation

## Overview

This project implements a comprehensive FTP client for connecting to Loxone MiniServer and retrieving temperature log files. The implementation includes FTP connection management, log file parsing, and data processing capabilities.

## Features Implemented

### 1. FTP Connection Management (`src/loxone_ftp/ftp_client.py`)

**LoxoneFTPClient Class**
- Establishes secure FTP connections to Loxone MiniServer
- Configurable host, username, password, and port (default: 21)
- Built-in timeout and retry logic
- Connection retry mechanism with configurable attempts and delay
- Context manager support for safe resource cleanup
- Automatic local storage directory management

**Key Methods:**
- `connect()`: Establishes FTP connection with automatic retry
- `disconnect()`: Safely closes FTP connection
- `list_files(directory)`: Lists files in remote directory
- `get_temperature_logs(remote_directory)`: Retrieves temperature log filenames
- `download_file(remote_path, local_path)`: Downloads individual files
- `download_temperature_logs()`: Downloads all temperature logs
- `get_new_logs_only()`: Retrieves only new/updated logs (supports log rotation)
- `retrieve_logs(only_new)`: Main entry point for log retrieval

**Error Handling:**
- Custom `FTPConnectionError` exception for connection failures
- Automatic retry on connection failures
- Graceful error handling during file operations
- Comprehensive logging at each step

### 2. Log File Parsing (`src/loxone_ftp/log_parser.py`)

**TemperatureReading Class**
- Data structure for temperature readings
- Stores: timestamp, temperature value, sensor name
- Includes conversion to dictionary format for serialization

**LogParser Class**
- Supports multiple log file formats:
  - Standard format: `YYYY-MM-DD HH:MM:SS, temperature`
  - EU format: `DD.MM.YYYY HH:MM:SS, temperature`
  - Unix timestamp: `1234567890, temperature` (seconds or milliseconds)
  - CSV format: `sensor_name, YYYY-MM-DD HH:MM:SS, temperature`

**Key Methods:**
- `parse_file(file_path)`: Parses complete log file
- `parse_files(file_paths)`: Parses multiple files
- `parse_line(line, sensor_name)`: Parses individual lines
- `get_temperature_statistics(readings)`: Calculates min, max, average temperature

**Features:**
- Flexible timestamp parsing (multiple formats)
- Temperature value extraction and validation
- Comment line skipping (lines starting with #)
- Automatic sensor naming from filename
- Error resilience - skips unparseable lines

### 3. Data Handler (`src/loxone_ftp/data_handler.py`)

**DataHandler Class**
- Manages downloaded and processed temperature data
- Tracks processing metadata (which files have been processed)
- Supports log rotation (retrieve only new logs)

**Key Methods:**
- `get_new_files(log_files)`: Filters unprocessed files
- `process_log_file(file_path)`: Processes single log file
- `process_log_files(file_paths)`: Batch processing
- `save_processed_data(data, filename)`: Saves to JSON
- `load_processed_data(filename)`: Loads previously processed data
- `get_combined_temperature_data(files)`: Combines data from multiple files
- `cleanup_old_logs(keep_days)`: Removes old log files
- `get_storage_info()`: Retrieves storage statistics

**Features:**
- JSON metadata tracking for processed files
- Automatic timestamp tracking
- Temporary file management
- Configurable data retention policy

## Project Structure

```
.
├── src/
│   ├── __init__.py
│   └── loxone_ftp/
│       ├── __init__.py           # Package exports
│       ├── ftp_client.py         # FTP connection & download (298 lines)
│       ├── log_parser.py         # Log parsing (303 lines)
│       └── data_handler.py       # Data management (278 lines)
├── tests/
│   ├── __init__.py
│   ├── test_ftp_client.py        # FTP client tests (213 lines)
│   ├── test_log_parser.py        # Log parser tests (240 lines)
│   └── test_data_handler.py      # Data handler tests (246 lines)
├── examples/
│   ├── __init__.py
│   └── example_usage.py          # Usage examples
├── .gitignore                    # Git ignore configuration
├── README.md                     # User guide
├── IMPLEMENTATION.md             # This file
├── config.example.json           # Configuration template
├── requirements.txt              # Python dependencies
├── requirements-dev.txt          # Development dependencies
├── setup.py                      # Package setup
└── pytest.ini                    # Pytest configuration
```

## Usage Examples

### Basic Usage

```python
from src.loxone_ftp import LoxoneFTPClient, DataHandler

# Create FTP client
client = LoxoneFTPClient(
    host='192.168.1.100',
    username='admin',
    password='password',
    port=21
)

# Retrieve logs
log_files = client.retrieve_logs(only_new=True)

# Process data
handler = DataHandler()
combined_data = handler.get_combined_temperature_data(log_files)

# Save results
output_file = handler.save_processed_data(combined_data)
```

### Context Manager Usage

```python
with LoxoneFTPClient(host='192.168.1.100', username='admin', password='pass') as client:
    logs = client.get_temperature_logs()
    files = client.download_temperature_logs()
# Connection automatically closed
```

### Manual Connection Control

```python
client = LoxoneFTPClient(host='192.168.1.100', username='admin', password='pass')
try:
    client.connect()
    files = client.list_files('/logs')
    client.download_file('/logs/temp.txt')
finally:
    client.disconnect()
```

## Test Coverage

Comprehensive test suite with 57 passing tests:
- **FTP Client Tests**: 16 tests covering connection, retry logic, file operations
- **Log Parser Tests**: 28 tests covering multiple formats, parsing, statistics
- **Data Handler Tests**: 13 tests covering processing, storage, metadata

All tests use mocking to avoid external FTP dependencies.

## Configuration

Example configuration in `config.example.json`:

```json
{
  "ftp": {
    "host": "192.168.1.100",
    "port": 21,
    "username": "admin",
    "password": "password",
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 2
  },
  "storage": {
    "local_logs_path": "./data/logs",
    "processed_data_path": "./data/processed",
    "keep_old_logs_days": 30
  }
}
```

## Connection Error Handling

The implementation includes robust error handling:

1. **Connection Failures**: Automatic retry with configurable attempts and delays
2. **File Operations**: Graceful handling of download failures
3. **Parsing Errors**: Skips unparseable lines, continues processing
4. **Storage Issues**: Validates directory creation and file permissions
5. **Cleanup**: Ensures proper resource cleanup even on errors

## Log Rotation Support

The `get_new_logs_only()` method implements log rotation by:

1. Comparing remote file list with local storage
2. Identifying only new/updated files
3. Downloading only new files
4. Tracking processed files in metadata

This minimizes bandwidth usage and processing time.

## Temperature Data Processing

The parsed temperature data is structured as:

```python
{
    'generated_at': '2025-01-01T12:00:00',
    'total_readings': 100,
    'files_processed': {
        'temp_01.txt': {'count': 50},
        'temp_02.txt': {'count': 50}
    },
    'all_readings': [
        {
            'timestamp': '2025-01-01T12:00:00',
            'temperature': 22.5,
            'sensor_name': 'living_room'
        },
        ...
    ]
}
```

## Performance Characteristics

- **Memory Efficient**: Streams files during download
- **Batch Processing**: Processes multiple files efficiently
- **Retry Logic**: Prevents connection timeouts
- **Metadata Caching**: Avoids reprocessing files

## Requirements

- Python 3.7+
- Standard library modules: `ftplib`, `json`, `logging`, `pathlib`
- Optional: `python-dateutil` for enhanced date parsing

## Installation

```bash
# Install in development mode
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src
```

## Future Enhancements

Potential improvements:
1. SFTP/FTPS support for encrypted connections
2. Scheduling/cron integration
3. Database backend for log storage
4. Real-time temperature streaming
5. Web dashboard for visualization
6. Email/webhook notifications for temperature alerts
