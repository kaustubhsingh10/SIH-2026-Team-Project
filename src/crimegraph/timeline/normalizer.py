"""Temporal Normalizer for CrimeGraph AI (Day 23).

Parses raw dates, datetimes, time ranges, and approximate strings into
canonical ISO 8601 representation and assigns deterministic TemporalPrecision.
"""

from datetime import datetime, timezone
import re
from typing import Optional, Tuple

from crimegraph.timeline.models import TemporalPrecision


class TemporalNormalizer:
    """Normalizes raw timestamp strings into standardized timestamps and precision tiers."""

    # Exact ISO 8601 with time: e.g. 2026-08-11T14:30:00Z, 2026-08-11T14:30:00+05:30, 2026-08-11 14:30:00
    _ISO_DATETIME_PATTERN = re.compile(
        r"^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
    )

    # Date only: YYYY-MM-DD or DD/MM/YYYY or DD-MM-YYYY
    _DATE_ISO_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
    _DATE_DMY_PATTERN = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$")

    # Time range: e.g. "2026-08-11 10:00 to 2026-08-11 12:00" or "10:00 - 12:00 on 2026-08-11" or "between 2026-08-11 and 2026-08-15"
    _RANGE_BETWEEN_DATES = re.compile(r"(?:between|from)\s+(\d{4}-\d{2}-\d{2})\s+(?:to|and)\s+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)

    # Approximate keywords: "mid-August 2026", "early 2026", "around 2026-08-11", "approx 2026-08-11"
    _APPROX_PATTERN = re.compile(r"\b(around|approx|approximately|circa|c\.|early|mid|late|about)\b", re.IGNORECASE)

    @classmethod
    def normalize_timestamp(
        cls,
        raw_val: Optional[str]
    ) -> Tuple[Optional[str], TemporalPrecision, Optional[str], Optional[str]]:
        """Parses a raw timestamp string into (normalized_timestamp, precision, range_start, range_end).

        Guarantees:
        - Unknown remains UNKNOWN (no invented fake dates).
        - DATE_ONLY does not invent hours/minutes.
        - Preserves unparseable text as APPROXIMATE or UNKNOWN without crashing.
        """
        if not raw_val or not str(raw_val).strip():
            return None, TemporalPrecision.UNKNOWN, None, None

        cleaned = str(raw_val).strip()

        # Check for range expressions first
        m_range = cls._RANGE_BETWEEN_DATES.search(cleaned)
        if m_range:
            start_d, end_d = m_range.group(1), m_range.group(2)
            return f"{start_d} / {end_d}", TemporalPrecision.TIME_RANGE, start_d, end_d

        # Check for explicit approximation markers
        is_approx = bool(cls._APPROX_PATTERN.search(cleaned))

        # Check for ISO Datetime with time
        m_iso_dt = cls._ISO_DATETIME_PATTERN.match(cleaned)
        if m_iso_dt:
            # Standardize format to YYYY-MM-DDTHH:MM:SSZ
            y, m, d, hh, mm, ss = m_iso_dt.groups()
            ss = ss or "00"
            norm = f"{y}-{m}-{d}T{hh}:{mm}:{ss}Z"
            prec = TemporalPrecision.APPROXIMATE if is_approx else TemporalPrecision.EXACT_TIMESTAMP
            return norm, prec, None, None

        # Check for Date only YYYY-MM-DD
        m_date_iso = cls._DATE_ISO_PATTERN.match(cleaned)
        if m_date_iso:
            y, m, d = m_date_iso.groups()
            norm = f"{y}-{m}-{d}"
            prec = TemporalPrecision.APPROXIMATE if is_approx else TemporalPrecision.DATE_ONLY
            return norm, prec, None, None

        # Check for Date only DD/MM/YYYY or DD-MM-YYYY
        m_date_dmy = cls._DATE_DMY_PATTERN.match(cleaned)
        if m_date_dmy:
            d, m, y = m_date_dmy.groups()
            norm = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
            prec = TemporalPrecision.APPROXIMATE if is_approx else TemporalPrecision.DATE_ONLY
            return norm, prec, None, None

        # Try standard Python datetime parsing fallbacks
        for fmt in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%b %d, %Y %H:%M",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m",
            "%Y"
        ):
            try:
                dt = datetime.strptime(cleaned, fmt)
                if "%H" in fmt:
                    norm = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    prec = TemporalPrecision.APPROXIMATE if is_approx else TemporalPrecision.EXACT_TIMESTAMP
                elif "%d" in fmt:
                    norm = dt.strftime("%Y-%m-%d")
                    prec = TemporalPrecision.APPROXIMATE if is_approx else TemporalPrecision.DATE_ONLY
                else:
                    norm = dt.strftime("%Y-%m-%d")
                    prec = TemporalPrecision.APPROXIMATE
                return norm, prec, None, None
            except ValueError:
                continue

        # If approximation keyword present but unparsed format
        if is_approx:
            return cleaned, TemporalPrecision.APPROXIMATE, None, None

        # Unrecognized format
        return cleaned, TemporalPrecision.UNKNOWN, None, None

    @classmethod
    def calculate_time_delta_seconds(cls, ts1: Optional[str], ts2: Optional[str]) -> Optional[float]:
        """Calculates absolute difference in seconds between two ISO timestamps if comparable."""
        if not ts1 or not ts2:
            return None

        # Try parsing ISO datetimes
        def _parse(ts):
            ts = ts.replace("Z", "")
            if "T" in ts:
                return datetime.fromisoformat(ts)
            elif len(ts) == 10:  # YYYY-MM-DD
                return datetime.strptime(ts, "%Y-%m-%d")
            return None

        try:
            dt1 = _parse(ts1)
            dt2 = _parse(ts2)
            if dt1 and dt2:
                return abs((dt1 - dt2).total_seconds())
        except Exception:
            return None

        return None
