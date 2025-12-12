# Temperature Processing

Utilities for aggregating raw temperature logs into 3-hour interval summaries by day of week, plus a weekly overview.

## Basic usage

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
