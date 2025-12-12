# Loxone Temperature Overview

This project combines FTP client functionality for retrieving Loxone MiniServer temperature logs with utilities for aggregating and processing temperature data.

## Features

### Loxone FTP Integration
- FTP connection to Loxone server using credentials
- Download temperature log files
- Parse log files to extract timestamp and temperature readings
- Local storage of downloaded data for processing
- Connection error handling with retry logic
- Support for log rotation (retrieve only new logs)

### Temperature Processing
- Aggregates raw temperature logs into 3-hour interval summaries by day of week
- Generates weekly overview and Excel-ready output

## Project Structure

```
.
├── temperature_processing/
│   ├── __init__.py
│   └── processing.py          # Core temperature processing logic
├── temperature_data_processing.py     # Compatibility module
├── tests/
├── README.md
└── pyproject.toml
```

## Requirements

- Python 3.7+
- ftplib (standard library)
- Standard library utilities

## Usage

### Loxone FTP Client

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

### Temperature Processing

```python
from temperature_processing import process_temperature_data

raw = """\
2025-01-01T00:10:00, 21.5
2025-01-01T02:55:00, 20.1
2025-01-01T03:05:00, 19.8
"""

result = process_temperature_data(raw)
rows = result["excel_rows"]
```

The returned structure is designed to be easy to export to Excel (e.g. `excel_rows` as a list of dicts).
