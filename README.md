# Loxone Temperature Log Retrieval

FTP client for connecting to Loxone MiniServer and retrieving temperature log files.

## Features

- FTP connection to Loxone server using credentials
- Download temperature log files
- Parse log files to extract timestamp and temperature readings
- Local storage of downloaded data for processing
- Connection error handling with retry logic
- Support for log rotation (retrieve only new logs)

## Project Structure

```
.
├── src/
│   └── loxone_ftp/
│       ├── __init__.py
│       ├── ftp_client.py          # FTP client implementation
│       ├── log_parser.py          # Log file parsing
│       └── data_handler.py        # Data storage and management
├── tests/
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.7+
- ftplib (standard library)

## Usage

```python
from loxone_ftp import LoxoneFTPClient

client = LoxoneFTPClient(
    host='192.168.1.1',
    username='admin',
    password='password',
    port=21
)

# Retrieve and parse logs
logs = client.retrieve_logs()
```
