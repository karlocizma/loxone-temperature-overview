from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import datetime
from statistics import fmean
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class TemperatureReading:
    timestamp: datetime
    temperature: float


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if value is None:
        return None

    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _parse_temperature(value: Any) -> float | None:
    if value is None:
        return None

    try:
        f = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(f):
        return None

    return f


def parse_temperature_logs(raw: str | Iterable[str]) -> tuple[list[TemperatureReading], int]:
    lines: Iterable[str]
    if isinstance(raw, str):
        lines = raw.splitlines()
    else:
        lines = raw

    readings: list[TemperatureReading] = []
    skipped = 0

    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue

        if "," in s:
            parts = [p.strip() for p in s.split(",") if p.strip()]
        else:
            parts = [p.strip() for p in s.split() if p.strip()]

        if len(parts) < 2:
            skipped += 1
            continue

        ts = _parse_datetime(parts[0])
        temp = _parse_temperature(parts[1])

        if ts is None or temp is None:
            skipped += 1
            continue

        readings.append(TemperatureReading(timestamp=ts, temperature=temp))

    return readings, skipped


def _iter_readings(data: Any) -> tuple[list[TemperatureReading], int]:
    if isinstance(data, str):
        return parse_temperature_logs(data)

    if isinstance(data, (list, tuple)) and data and isinstance(data[0], str):
        return parse_temperature_logs(data)  # type: ignore[arg-type]

    readings: list[TemperatureReading] = []
    skipped = 0

    if isinstance(data, Iterable):
        for item in data:
            if isinstance(item, TemperatureReading):
                readings.append(item)
                continue

            if isinstance(item, Mapping):
                ts = _parse_datetime(item.get("timestamp") or item.get("time") or item.get("datetime"))
                temp = _parse_temperature(item.get("temperature") or item.get("temp"))
                if ts is None or temp is None:
                    skipped += 1
                    continue
                readings.append(TemperatureReading(timestamp=ts, temperature=temp))
                continue

            if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 2:
                ts = _parse_datetime(item[0])
                temp = _parse_temperature(item[1])
                if ts is None or temp is None:
                    skipped += 1
                    continue
                readings.append(TemperatureReading(timestamp=ts, temperature=temp))
                continue

            skipped += 1

        return readings, skipped

    return [], 1


def _format_hhmm(hour: int) -> str:
    return f"{hour:02d}:00"


def _stats(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "max": None, "avg": None}
    return {"min": min(values), "max": max(values), "avg": fmean(values)}


def aggregate_temperature_readings(
    readings: Iterable[TemperatureReading],
    *,
    bucket_hours: int = 3,
    include_empty_days: bool = True,
    include_empty_intervals: bool = True,
) -> dict[str, Any]:
    if bucket_hours <= 0 or 24 % bucket_hours != 0:
        raise ValueError("bucket_hours must be a positive divisor of 24")

    readings_list = list(readings)

    buckets_per_day = 24 // bucket_hours
    day_names = list(calendar.day_name)

    by_day_hour: dict[tuple[int, int], list[float]] = {}
    by_day_values: dict[int, list[float]] = {}
    all_values: list[float] = []

    for r in readings_list:
        temp = _parse_temperature(r.temperature)
        if temp is None:
            continue

        ts = r.timestamp
        weekday = ts.weekday()
        start_hour = (ts.hour // bucket_hours) * bucket_hours

        by_day_hour.setdefault((weekday, start_hour), []).append(temp)
        by_day_values.setdefault(weekday, []).append(temp)
        all_values.append(temp)

    days: list[dict[str, Any]] = []

    weekday_range = range(7) if include_empty_days else sorted(set(wd for wd, _ in by_day_hour.keys()))

    for weekday in weekday_range:
        intervals: list[dict[str, Any]] = []

        for i in range(buckets_per_day):
            start_hour = i * bucket_hours
            temps = by_day_hour.get((weekday, start_hour), [])

            if not temps and not include_empty_intervals:
                continue

            stat = _stats(temps)
            interval = {
                "interval_start": _format_hhmm(start_hour),
                "interval_end": _format_hhmm((start_hour + bucket_hours) % 24),
                "min": stat["min"],
                "max": stat["max"],
                "avg": stat["avg"],
                "count": len(temps),
            }
            intervals.append(interval)

        day_stat = _stats(by_day_values.get(weekday, []))
        days.append(
            {
                "day": day_names[weekday],
                "intervals": intervals,
                "summary": {
                    "min": day_stat["min"],
                    "max": day_stat["max"],
                    "avg": day_stat["avg"],
                    "count": len(by_day_values.get(weekday, [])),
                },
            }
        )

    weekly_stat = _stats(all_values)

    return {
        "bucket_hours": bucket_hours,
        "days": days,
        "weekly_summary": {
            "min": weekly_stat["min"],
            "max": weekly_stat["max"],
            "avg": weekly_stat["avg"],
            "count": len(all_values),
        },
    }


def build_excel_rows(aggregated: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for day in aggregated.get("days", []):
        day_name = day.get("day")
        for interval in day.get("intervals", []):
            rows.append(
                {
                    "scope": "interval",
                    "day": day_name,
                    "interval_start": interval.get("interval_start"),
                    "interval_end": interval.get("interval_end"),
                    "min": interval.get("min"),
                    "max": interval.get("max"),
                    "avg": interval.get("avg"),
                    "count": interval.get("count"),
                }
            )

        summary = day.get("summary") or {}
        rows.append(
            {
                "scope": "day",
                "day": day_name,
                "interval_start": None,
                "interval_end": None,
                "min": summary.get("min"),
                "max": summary.get("max"),
                "avg": summary.get("avg"),
                "count": summary.get("count"),
            }
        )

    weekly = aggregated.get("weekly_summary") or {}
    rows.append(
        {
            "scope": "week",
            "day": None,
            "interval_start": None,
            "interval_end": None,
            "min": weekly.get("min"),
            "max": weekly.get("max"),
            "avg": weekly.get("avg"),
            "count": weekly.get("count"),
        }
    )

    return rows


def process_temperature_data(
    data: Any,
    *,
    bucket_hours: int = 3,
    include_empty_days: bool = True,
    include_empty_intervals: bool = True,
) -> dict[str, Any]:
    readings, skipped = _iter_readings(data)

    aggregated = aggregate_temperature_readings(
        readings,
        bucket_hours=bucket_hours,
        include_empty_days=include_empty_days,
        include_empty_intervals=include_empty_intervals,
    )

    aggregated["skipped_records"] = skipped
    aggregated["excel_rows"] = build_excel_rows(aggregated)
    aggregated["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")

    return aggregated


process_temperature_logs = process_temperature_data
process_raw_temperature_logs = process_temperature_data
aggregate_temperature_data = aggregate_temperature_readings
