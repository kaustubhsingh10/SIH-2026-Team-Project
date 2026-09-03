"""Data normalizer for Multi-Source Ingestion in CrimeGraph AI.

Provides deterministic cleaning, identifier formatting, and property standardization
across disparate source feeds.
"""

import re
from typing import Any, Dict, Optional


class DataNormalizer:
    """Normalizes raw attribute values into canonical graph format."""

    @staticmethod
    def normalize_phone_number(raw_phone: str) -> str:
        """Standardizes phone numbers into canonical +91-XXXXXXXXXX or international format."""
        if not raw_phone:
            return ""
        
        cleaned = re.sub(r"[\s\-\(\)\.]", "", raw_phone.strip())
        # Handle 10-digit Indian numbers without country code
        if len(cleaned) == 10 and cleaned.isdigit():
            return f"+91-{cleaned}"
        # Handle 91XXXXXXXXXX
        if len(cleaned) == 12 and cleaned.startswith("91") and cleaned[2:].isdigit():
            return f"+91-{cleaned[2:]}"
        # Handle +91XXXXXXXXXX
        if cleaned.startswith("+91") and len(cleaned) == 13 and cleaned[3:].isdigit():
            return f"+91-{cleaned[3:]}"
        # Fallback to general cleaned format
        return raw_phone.strip()

    @staticmethod
    def normalize_vehicle_registration(raw_reg: str) -> str:
        """Standardizes vehicle registration plate numbers (e.g. DL-01-AB-1234)."""
        if not raw_reg:
            return ""
        
        cleaned = re.sub(r"[\s\.\-]", "", raw_reg.strip().upper())
        # Format standard Indian plates: DL01AB1234 -> DL-01-AB-1234
        m = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{1,4})$", cleaned)
        if m:
            state, district, series, number = m.groups()
            return f"{state}-{district.zfill(2)}-{series}-{number.zfill(4)}"
        return raw_reg.strip().upper()

    @staticmethod
    def normalize_entity_name(raw_name: str) -> str:
        """Standardizes names (strips excess whitespace, title-cases)."""
        if not raw_name:
            return ""
        return " ".join(raw_name.strip().split())

    @staticmethod
    def normalize_account_number(raw_acc: str) -> str:
        """Standardizes bank account numbers."""
        if not raw_acc:
            return ""
        return re.sub(r"[\s\-]", "", raw_acc.strip().upper())

    @classmethod
    def normalize_record_data(cls, record_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes an entire record payload before resolution."""
        norm = dict(data)
        
        if "phone_number" in norm:
            norm["phone_number"] = cls.normalize_phone_number(str(norm["phone_number"]))
        
        if "registration_number" in norm:
            norm["registration_number"] = cls.normalize_vehicle_registration(str(norm["registration_number"]))
            
        if "name" in norm and record_type == "PERSON":
            norm["name"] = cls.normalize_entity_name(str(norm["name"]))
            
        if "account_number" in norm:
            norm["account_number"] = cls.normalize_account_number(str(norm["account_number"]))

        return norm
