# Loxone Temperature Report System

A comprehensive Python solution for retrieving, processing, and analyzing temperature logs from Loxone MiniServer via FTP connection.

## 📋 Table of Contents

1. [Prerequisites & Installation](#prerequisites--installation)
2. [Configuration Guide](#configuration-guide)
3. [Running the Program](#running-the-program)
4. [Windows Task Scheduler Setup](#windows-task-scheduler-setup)
5. [Logs & Monitoring](#logs--monitoring)
6. [Troubleshooting](#troubleshooting)
7. [API Reference](#api-reference)
8. [Examples](#examples)

## Prerequisites & Installation

### System Requirements

- **Python**: Version 3.7 or higher
- **Operating System**: Windows 10/11, Linux (Ubuntu 18.04+), macOS 10.14+
- **Network**: Access to Loxone MiniServer via FTP (typically port 21)
- **Storage**: At least 100MB free disk space for logs and data

### Installation Steps

#### 1. Install Python 3.7+

**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- During installation, check "Add Python to PATH"
- Verify installation:
  ```cmd
  python --version
  ```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 --version
```

**macOS:**
```bash
# Using Homebrew
brew install python3
python3 --version
```

#### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv loxone_env

# Activate virtual environment
# Windows:
loxone_env\Scripts\activate
# Linux/macOS:
source loxone_env/bin/activate
```

#### 3. Install Dependencies

```bash
# Navigate to project directory
cd /path/to/loxone-temperature-report

# Install required packages
pip install -r requirements.txt

# For development/testing (optional)
pip install -r requirements-dev.txt
```

#### 4. Verify Installation

```bash
python -c "from src.loxone_ftp import LoxoneFTPClient; print('Installation successful!')"
```

## Configuration Guide

### Configuration File Setup

Create a `config.json` file in the project root directory. Use the provided example:

```bash
cp config.example.json config.json
```

### Configuration Parameters

#### FTP Configuration

```json
{
  "ftp": {
    "host": "192.168.1.100",
    "port": 21,
    "username": "admin",
    "password": "your_ftp_password",
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 2,
    "remote_log_directory": "/logs"
  }
}
```

**Parameter Descriptions:**
- `host`: Loxone MiniServer IP address or hostname
- `port`: FTP port (usually 21)
- `username`: FTP username for Loxone server
- `password`: FTP password
- `timeout`: Connection timeout in seconds
- `retry_attempts`: Number of retry attempts on connection failure
- `retry_delay`: Delay between retries in seconds
- `remote_log_directory`: Directory containing temperature logs (default: `/logs`)

#### Storage Configuration

```json
{
  "storage": {
    "local_logs_path": "./data/logs",
    "processed_data_path": "./data/processed",
    "keep_old_logs_days": 30
  }
}
```

**Parameter Descriptions:**
- `local_logs_path`: Directory for storing downloaded log files
- `processed_data_path`: Directory for processed data output
- `keep_old_logs_days`: Number of days to retain old log files

#### Logging Configuration

```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

**Log Levels:**
- `DEBUG`: Detailed information for debugging
- `INFO`: General information about program execution
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures

### SMTP/Email Configuration (Optional)

To enable email notifications, add SMTP configuration to your `config.json`:

```json
{
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your_email@gmail.com",
    "password": "your_app_password",
    "recipients": ["recipient1@example.com", "recipient2@example.com"],
    "use_tls": true
  }
}
```

**Gmail Setup:**
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password: [Google Account Settings](https://myaccount.google.com/apppasswords)
3. Use the app password in the configuration

**Office365 Setup:**
```json
{
  "email": {
    "smtp_server": "smtp.office365.com",
    "smtp_port": 587,
    "username": "your_email@yourcompany.com",
    "password": "your_email_password",
    "use_tls": true
  }
}
```

## Running the Program

### Manual Execution

#### Basic Usage

```bash
# Create necessary directories
mkdir -p data/logs data/processed

# Run the example script
python examples/example_usage.py
```

#### Custom Script Example

Create a custom script `run_temperature_report.py`:

```python
import json
import logging
from pathlib import Path
from src.loxone_ftp import LoxoneFTPClient, DataHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Load configuration
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Setup FTP client
    ftp_config = config['ftp']
    ftp_client = LoxoneFTPClient(
        host=ftp_config['host'],
        username=ftp_config['username'],
        password=ftp_config['password'],
        port=ftp_config['port'],
        local_storage_path=config['storage']['local_logs_path']
    )

    # Setup data handler
    data_handler = DataHandler(
        storage_path=config['storage']['local_logs_path'],
        processed_path=config['storage']['processed_data_path'],
    )

    try:
        # Retrieve logs
        log_files = ftp_client.retrieve_logs(only_new=True)
        
        if log_files:
            # Process data
            combined_data = data_handler.get_combined_temperature_data(log_files)
            
            # Save processed data
            output_file = data_handler.save_processed_data(combined_data)
            print(f"Data processed and saved to: {output_file}")
        else:
            print("No new log files found.")

    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
    finally:
        ftp_client.disconnect()

if __name__ == '__main__':
    main()
```

### Testing with Sample Data

#### Create Test Configuration

```bash
# Create test config
cat > test_config.json << EOF
{
  "ftp": {
    "host": "127.0.0.1",
    "port": 21,
    "username": "test",
    "password": "test",
    "timeout": 5,
    "retry_attempts": 1,
    "local_logs_path": "./test_data/logs",
    "remote_log_directory": "/test_logs"
  },
  "storage": {
    "local_logs_path": "./test_data/logs",
    "processed_data_path": "./test_data/processed"
  }
}
EOF
```

#### Test with Local Data

```python
# test_local_data.py
import tempfile
import os
from src.loxone_ftp.log_parser import TemperatureLogParser

# Create sample temperature data
sample_data = """2025-01-01 12:00:00, 21.5
2025-01-01 12:15:00, 21.8
2025-01-01 12:30:00, 22.1
DD.MM.YYYY 01.01.2025 13:00:00, 22.3
2025-01-01 13:15:00, 22.0
"""

# Parse the data
parser = TemperatureLogParser()
readings = parser.parse_string(sample_data)

print(f"Parsed {len(readings)} temperature readings:")
for reading in readings[:3]:  # Show first 3
    print(f"  {reading.timestamp}: {reading.temperature}°C")
```

### Monitoring and Output

#### Output Files

After running the program, check these directories:

- `data/logs/`: Downloaded raw log files
- `data/processed/`: Processed JSON data files
- `logs/` (if created): Log files

#### Process Output

```python
# Check processed data
import json

with open('data/processed/latest_data.json', 'r') as f:
    data = json.load(f)

print(f"Total readings: {data['total_readings']}")
print(f"Files processed: {len(data['files_processed'])}")
print(f"Temperature range: {data['statistics']['min']} - {data['statistics']['max']}°C")
```

## Windows Task Scheduler Setup

### Creating a Scheduled Task

#### Method 1: Using Task Scheduler GUI

1. **Open Task Scheduler**
   - Press `Win + R`, type `taskschd.msc`, press Enter
   - Or search "Task Scheduler" in Start Menu

2. **Create Basic Task**
   - Click "Create Basic Task..."
   - Enter name: "Loxone Temperature Report"
   - Click "Next"

3. **Set Trigger**
   - Select "Weekly"
   - Set start time (e.g., every Monday at 8:00 AM)
   - Select days of week
   - Click "Next"

4. **Set Action**
   - Select "Start a program"
   - Program: `C:\Path\To\loxone_env\Scripts\python.exe`
   - Arguments: `C:\Path\To\Project\run_temperature_report.py`
   - Start in: `C:\Path\To\Project`
   - Click "Next"

5. **Complete Setup**
   - Review settings
   - Check "Open the Properties dialog"
   - Click "Finish"

#### Method 2: Using Command Line

```cmd
# Create scheduled task
schtasks /create /tn "Loxone Temperature Report" /tr "C:\loxone_env\Scripts\python.exe C:\Project\run_temperature_report.py" /sc weekly /mo 1 /d MON /st 08:00 /ru "SYSTEM" /f
```

### Task Properties Configuration

#### General Tab
- **Name**: Loxone Temperature Report
- **Security options**: Run whether user is logged on or not
- **Configure for**: Windows 10/11 (or appropriate version)

#### Actions Tab
- **Action**: Start a program
- **Program/script**: `C:\loxone_env\Scripts\python.exe`
- **Arguments**: `C:\Project\run_temperature_report.py`
- **Start in**: `C:\Project`

#### Triggers Tab
- **Begin the task**: On a schedule
- **Settings**: Weekly
- **Start**: [Date] 08:00:00
- **Recur every**: 1 week(s) on: Monday

#### Conditions Tab
- **Start the task only if the computer is idle for**: 5 minutes
- **Stop if the computer ceases to be idle**: Enabled
- **Restart if the idle state resumes**: Enabled

#### Settings Tab
- **Allow task to be run on demand**: Enabled
- **Run task as soon as possible after a scheduled start is missed**: Enabled
- **If the task fails, restart every**: 10 minutes
- **Attempt to restart up to**: 3 time(s)

### Testing the Scheduled Task

#### Manual Test
1. Right-click the task in Task Scheduler
2. Select "Run"
3. Check "Last Run Result" and task history

#### Check Task History
1. Select your task in Task Scheduler
2. Click "History" tab
3. Review task execution details

### Common Scheduling Issues

#### Task Doesn't Run
- **Check user permissions**: Ensure task runs with appropriate user
- **Verify paths**: Ensure Python executable and script paths are correct
- **Check working directory**: Set correct "Start in" directory

#### Task Fails with Exit Code 1
- **Check Python environment**: Ensure virtual environment is activated
- **Verify dependencies**: Ensure all required packages are installed
- **Check file permissions**: Ensure read/write access to data directories

#### Network Connection Issues
- **Test FTP connectivity**: Manually test connection to Loxone server
- **Check firewall settings**: Ensure FTP traffic is allowed
- **Verify credentials**: Ensure FTP username/password are correct

## Logs & Monitoring

### Log File Locations

#### Application Logs
- Console output (when running manually)
- Log files in `logs/` directory (if configured)

#### Data Files
- Raw logs: `data/logs/`
- Processed data: `data/processed/`
- Metadata: `data/logs/.metadata.json`

### Log Levels and Format

#### Configure Logging

```python
import logging

# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/temperature_report.log'),
        logging.StreamHandler()  # Also show in console
    ]
)
```

#### Log File Example

```
2025-01-01 08:00:15,123 - src.loxone_ftp.ftp_client - INFO - Connecting to Loxone server: 192.168.1.100
2025-01-01 08:00:16,456 - src.loxone_ftp.ftp_client - INFO - Successfully connected to FTP server
2025-01-01 08:00:17,789 - src.loxone_ftp.ftp_client - INFO - Found 2 temperature log files
2025-01-01 08:00:18,234 - src.loxone_ftp.ftp_client - INFO - Downloaded: temperature_01.txt
2025-01-01 08:00:19,567 - src.loxone_ftp.ftp_client - INFO - Downloaded: temperature_02.txt
2025-01-01 08:00:20,890 - src.loxone_ftp.data_handler - INFO - Processed 150 temperature readings
2025-01-01 08:00:21,123 - src.loxone_ftp.data_handler - INFO - Saved processed data to: data/processed/data_20250101.json
```

### Monitoring Performance

#### Check Disk Space
```bash
# Linux/macOS
du -sh data/
ls -la data/logs/

# Windows
dir data\ /s
```

#### Monitor Log Growth
```bash
# Watch log file size
watch -n 5 ls -lh logs/temperature_report.log

# Check last few log entries
tail -f logs/temperature_report.log
```

### Error Analysis

#### Common Log Messages

**INFO Messages:**
- `Successfully connected to FTP server`: Normal connection
- `Downloaded: temperature_01.txt`: File downloaded successfully
- `Processed 150 temperature readings`: Data processed correctly

**WARNING Messages:**
- `Connection timeout, retrying...`: Temporary connection issue
- `File not found, skipping`: Missing log file
- `Invalid temperature format, skipping line`: Data parsing issue

**ERROR Messages:**
- `Failed to connect to FTP server`: Authentication or network issue
- `Permission denied`: File access problem
- `Invalid configuration`: Setup problem

## Troubleshooting

### FTP Connection Issues

#### Problem: "Connection refused" or "Connection timeout"

**Symptoms:**
```
ftplib.error_perm: 421 Service not available
```

**Solutions:**
1. **Check network connectivity:**
   ```bash
   ping 192.168.1.100
   telnet 192.168.1.100 21
   ```

2. **Verify Loxone FTP settings:**
   - Ensure FTP service is enabled in Loxone config
   - Check if firewall is blocking port 21
   - Verify correct IP address/hostname

3. **Test with different timeout:**
   ```python
   ftp_client = LoxoneFTPClient(
       host='192.168.1.100',
       username='admin',
       password='password',
       timeout=60  # Increase timeout
   )
   ```

#### Problem: "Authentication failed"

**Symptoms:**
```
ftplib.error_perm: 530 Login incorrect
```

**Solutions:**
1. **Verify credentials:**
   - Check username and password in Loxone interface
   - Ensure account has FTP access permissions

2. **Check Loxone FTP configuration:**
   - Ensure FTP service is enabled
   - Verify user permissions in Loxone config

3. **Test with FTP client:**
   ```bash
   ftp 192.168.1.100
   # Manual login test
   ```

### SMTP/Email Delivery Problems

#### Problem: "SMTP Authentication Error"

**Symptoms:**
```
smtplib.SMTPAuthenticationError: 535, b'5.7.8 Authentication credentials invalid'
```

**Solutions:**
1. **Gmail App Password:**
   - Ensure 2FA is enabled
   - Use generated app password, not regular password
   - Check [App Passwords](https://myaccount.google.com/apppasswords)

2. **Office365:**
   - Check modern authentication settings
   - Ensure account has SMTP permissions

3. **Test email configuration:**
   ```python
   import smtplib
   from email.mime.text import MIMEText
   
   # Test connection
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('your_email@gmail.com', 'your_app_password')
   ```

#### Problem: "Connection timeout"

**Symptoms:**
```
smtplib.SMTPConnectError: Error connecting to SMTP server
```

**Solutions:**
1. **Check internet connection:**
   ```bash
   telnet smtp.gmail.com 587
   ```

2. **Verify firewall settings:**
   - Ensure outbound SMTP traffic is allowed
   - Check corporate firewall restrictions

3. **Try alternative SMTP server:**
   ```python
   # Gmail alternative
   smtp_server: "smtp.gmail.com"
   smtp_port: 587
   # Office365 alternative
   smtp_server: "smtp.office365.com"
   smtp_port: 587
   ```

### File Permission Issues

#### Problem: "Permission denied" when writing files

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: 'data/logs/temperature_01.txt'
```

**Solutions:**

**Linux/macOS:**
```bash
# Create directories with proper permissions
mkdir -p data/logs data/processed
chmod 755 data/logs data/processed
chmod 666 data/logs/.metadata.json 2>/dev/null || true

# Check current user
whoami
ls -la data/
```

**Windows:**
```cmd
# Run as Administrator or adjust permissions
icacls data\ /grant Users:(OI)(CI)F
# Or create directories manually in Windows Explorer
```

#### Problem: "No such file or directory"

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'data/processed/latest_data.json'
```

**Solutions:**
1. **Ensure directories exist:**
   ```python
   from pathlib import Path
   
   Path('data/logs').mkdir(parents=True, exist_ok=True)
   Path('data/processed').mkdir(parents=True, exist_ok=True)
   ```

2. **Use absolute paths:**
   ```python
   base_path = Path(__file__).parent
   logs_path = base_path / 'data' / 'logs'
   processed_path = base_path / 'data' / 'processed'
   ```

### Data Parsing Errors

#### Problem: "Invalid temperature format"

**Symptoms:**
```
ValueError: could not convert string to float: 'invalid_temp'
```

**Solutions:**
1. **Check log file format:**
   - Standard: `2025-01-01 12:00:00, 21.5`
   - EU format: `01.01.2025 12:00:00, 21.5`
   - Unix timestamp: `1672574400, 21.5`

2. **Enable debug logging:**
   ```python
   logging.getLogger('src.loxone_ftp.log_parser').setLevel(logging.DEBUG)
   ```

3. **Filter invalid lines:**
   - Check if log files contain non-temperature data
   - Remove comment lines or invalid entries

#### Problem: "No temperature data found"

**Symptoms:**
```
INFO - No temperature readings found in temperature_01.txt
```

**Solutions:**
1. **Check file patterns:**
   ```python
   # Verify temperature file patterns
   TEMP_LOG_PATTERNS = ["Temp", "Temperature", "temp"]
   
   # Add custom patterns if needed
   client.TEMP_LOG_PATTERNS.append("CustomPattern")
   ```

2. **Verify directory contents:**
   ```python
   with LoxoneFTPClient(**config) as client:
       files = client.list_files('/logs')
       print(f"Files in /logs: {files}")
   ```

### Performance Issues

#### Problem: "Slow processing" or "High memory usage"

**Solutions:**
1. **Reduce retry attempts:**
   ```python
   ftp_client = LoxoneFTPClient(
       host='192.168.1.100',
       username='admin',
       password='password',
       retry_attempts=1,  # Reduce from default 3
       retry_delay=1      # Reduce from default 2
   )
   ```

2. **Process logs incrementally:**
   ```python
   # Use only_new=True for subsequent runs
   log_files = ftp_client.retrieve_logs(only_new=True)
   ```

3. **Clean old logs:**
   ```python
   # Configure log retention
   "keep_old_logs_days": 7  # Reduce from default 30
   ```

### Getting Help

#### Check Documentation
- Review this README.md for common solutions
- Check `FEATURES.md` for implementation details
- Examine `examples/` directory for usage patterns

#### Run Tests
```bash
# Run the test suite
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_ftp_client.py -v
python -m pytest tests/test_log_parser.py -v
python -m pytest tests/test_data_handler.py -v
```

#### Enable Debug Mode
```python
# Enable all debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Create Debug Script
```python
# debug_connection.py
from src.loxone_ftp import LoxoneFTPClient

# Test connection with verbose output
try:
    with LoxoneFTPClient(
        host='192.168.1.100',
        username='admin',
        password='password'
    ) as client:
        files = client.list_files('/logs')
        print(f"Successfully connected. Found files: {files}")
except Exception as e:
    print(f"Connection failed: {e}")
    import traceback
    traceback.print_exc()
```

## API Reference

### LoxoneFTPClient

#### Constructor
```python
LoxoneFTPClient(
    host: str,
    username: str, 
    password: str,
    port: int = 21,
    timeout: int = 30,
    local_storage_path: str = "./data/logs",
    retry_attempts: int = 3,
    retry_delay: int = 2
)
```

#### Methods

**connect()** - Establish FTP connection
- Returns: `None`
- Raises: `FTPConnectionError` on failure

**disconnect()** - Close FTP connection
- Returns: `None`

**retrieve_logs(only_new: bool = False)**
- `only_new`: Retrieve only files not yet processed
- Returns: `List[str]` - List of downloaded file paths

**list_files(directory: str = "/logs")**
- `directory`: Remote directory to list
- Returns: `List[str]` - List of file names

**download_file(remote_path: str)**
- `remote_path`: Full path to remote file
- Returns: `str` - Local file path

**get_temperature_logs()**
- Returns: `List[str]` - Temperature log file names

#### Context Manager Usage
```python
with LoxoneFTPClient(host='192.168.1.100', username='admin', password='pass') as client:
    logs = client.retrieve_logs()
    # Connection automatically closed
```

### TemperatureLogParser

#### Methods

**parse_file(file_path: str)**
- `file_path`: Path to log file
- Returns: `List[TemperatureReading]` - Parsed temperature readings

**parse_string(data: str)**
- `data`: String containing log data
- Returns: `List[TemperatureReading]` - Parsed temperature readings

**parse_lines(lines: List[str])**
- `lines`: List of log lines
- Returns: `List[TemperatureReading]` - Parsed temperature readings

#### Supported Formats

1. **Standard Format**: `2025-01-01 12:00:00, 21.5`
2. **EU Format**: `01.01.2025 12:00:00, 21.5`
3. **Unix Timestamp**: `1672574400, 21.5`
4. **CSV Format**: `sensor_name, 2025-01-01 12:00:00, 21.5`

### DataHandler

#### Constructor
```python
DataHandler(
    storage_path: str = "./data/logs",
    processed_path: str = "./data/processed"
)
```

#### Methods

**get_combined_temperature_data(file_paths: List[str])**
- `file_paths`: List of log file paths to process
- Returns: `Dict` - Combined data with statistics

**save_processed_data(data: Dict)**
- `data`: Processed temperature data
- Returns: `str` - Path to saved JSON file

### TemperatureReading

#### Properties

- `timestamp`: `datetime` - Reading timestamp
- `temperature`: `float` - Temperature value
- `sensor_name`: `str` - Sensor identifier

#### Methods

**to_dict()**
- Returns: `Dict` - Dictionary representation

## Examples

### Basic Usage
```python
from src.loxone_ftp import LoxoneFTPClient, DataHandler

# Setup
client = LoxoneFTPClient(host='192.168.1.100', username='admin', password='pass')
handler = DataHandler()

# Retrieve and process logs
log_files = client.retrieve_logs(only_new=True)
if log_files:
    data = handler.get_combined_temperature_data(log_files)
    handler.save_processed_data(data)
    print(f"Processed {len(log_files)} files")
```

### Error Handling
```python
from src.loxone_ftp.ftp_client import FTPConnectionError
import logging

try:
    with LoxoneFTPClient(host='192.168.1.100', username='admin', password='pass') as client:
        logs = client.retrieve_logs()
except FTPConnectionError as e:
    logging.error(f"FTP connection failed: {e}")
except Exception as e:
    logging.error(f"Unexpected error: {e}")
```

### Custom Processing
```python
from src.loxone_ftp.log_parser import TemperatureLogParser
from datetime import datetime, timedelta

# Parse specific file
parser = TemperatureLogParser()
readings = parser.parse_file('data/logs/temperature_01.txt')

# Filter recent readings (last 24 hours)
recent_cutoff = datetime.now() - timedelta(hours=24)
recent_readings = [r for r in readings if r.timestamp > recent_cutoff]

# Calculate statistics
if recent_readings:
    temps = [r.temperature for r in recent_readings]
    print(f"Last 24h: {len(recent_readings)} readings")
    print(f"Range: {min(temps):.1f} - {max(temps):.1f}°C")
```

---

## License

This project is provided as-is for educational and personal use. Please ensure compliance with Loxone's terms of service when using this software.

## Support

For issues, questions, or contributions, please refer to the project repository documentation and examples.