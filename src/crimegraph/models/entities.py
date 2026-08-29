"""Entity models for CrimeGraph AI.

Strictly adheres to DATA_SCHEMA.md Section 1 (Entity Types) and API_CONTRACT.md.
"""

from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntityType(str, Enum):
    """Enumeration of all entity types from DATA_SCHEMA.md."""
    PERSON = "PERSON"
    PHONE = "PHONE"
    VEHICLE = "VEHICLE"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    ACCOUNT = "ACCOUNT"
    CASE = "CASE"
    EVENT = "EVENT"


class BaseEntity(BaseModel):
    """Base model for all graph entities with common ID and source validation."""
    model_config = ConfigDict(use_enum_values=True, extra="allow")

    id: str = Field(..., description="Unique entity ID (e.g. PERSON_017, CASE_101)")
    source_ids: List[str] = Field(default_factory=list, description="IDs of source documents / evidence")
    source: str = Field(default="Dataset", description="Data provenance (Dataset vs Manual)")
    is_manual: bool = Field(default=False, description="Flag indicating manually created entity")


class Person(BaseEntity):
    """Person entity model.
    
    Fields defined in DATA_SCHEMA.md:
    - id
    - name
    - aliases
    - age
    - gender
    - phone_ids
    - vehicle_ids
    - address_ids
    - source_ids
    - confidence
    """
    entity_type: EntityType = Field(default=EntityType.PERSON)
    name: str = Field(..., description="Full or observed name")
    aliases: List[str] = Field(default_factory=list, description="Known aliases or alternative names")
    age: Optional[int] = Field(default=None, ge=0, le=150, description="Age in years if known")
    gender: Optional[str] = Field(default=None, description="Gender if known")
    phone_ids: List[str] = Field(default_factory=list, description="Associated phone entity IDs")
    vehicle_ids: List[str] = Field(default_factory=list, description="Associated vehicle entity IDs")
    address_ids: List[str] = Field(default_factory=list, description="Associated location entity IDs")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)


class Phone(BaseEntity):
    """Phone entity model.
    
    Fields defined in DATA_SCHEMA.md:
    - id
    - phone_number
    - owner_ids
    - source_ids
    - confidence
    """
    entity_type: EntityType = Field(default=EntityType.PHONE)
    phone_number: str = Field(..., description="Phone number or MSISDN")
    owner_ids: List[str] = Field(default_factory=list, description="Associated owner person IDs")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)


class Vehicle(BaseEntity):
    """Vehicle entity model.
    
    Fields defined in DATA_SCHEMA.md:
    - id
    - registration_number
    - type
    - owner_id
    - source_ids
    - confidence
    """
    entity_type: EntityType = Field(default=EntityType.VEHICLE)
    registration_number: str = Field(..., description="License plate or registration number")
    type: Optional[str] = Field(default=None, description="Vehicle type / model (e.g. Sedan, SUV, Motorcycle, Truck)")
    owner_id: Optional[str] = Field(default=None, description="Owner person ID if known")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)


class Location(BaseEntity):
    """Location entity model.
    
    Fields defined in DATA_SCHEMA.md:
    - id
    - name
    - latitude
    - longitude
    - address
    - source_ids
    """
    entity_type: EntityType = Field(default=EntityType.LOCATION)
    name: str = Field(..., description="Location name or place descriptor")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Geographic latitude")
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Geographic longitude")
    address: Optional[str] = Field(default=None, description="Physical address string")


class Organization(BaseEntity):
    """Organization entity model.
    
    Fields defined in DATA_SCHEMA.md:
    - id
    - name
    - aliases
    - address
    - source_ids
    """
    entity_type: EntityType = Field(default=EntityType.ORGANIZATION)
    name: str = Field(..., description="Organization or company name")
    aliases: List[str] = Field(default_factory=list, description="Alternative names or abbreviations")
    address: Optional[str] = Field(default=None, description="Headquarters or branch address")


class Account(BaseEntity):
    """Bank or digital Account entity model.
    
    Fields defined in DATA_SCHEMA.md:
    - id
    - account_type
    - identifier
    - owner_id
    - source_ids
    """
    entity_type: EntityType = Field(default=EntityType.ACCOUNT)
    account_type: str = Field(..., description="Type of account (e.g. BANK_ACCOUNT, UPI, CRYPTO_WALLET)")
    identifier: str = Field(..., description="Account number, IBAN, UPI ID, or wallet address")
    owner_id: Optional[str] = Field(default=None, description="Owner person/org ID if known")


class Case(BaseEntity):
    """Case entity model.
    
    Fields defined in DATA_SCHEMA.md:
    - id
    - case_number
    - title
    - description
    - status
    - incident_date
    - location_id
    - source_ids
    """
    entity_type: EntityType = Field(default=EntityType.CASE)
    case_number: str = Field(..., description="Official case number or FIR number")
    title: str = Field(..., description="Short case title")
    description: Optional[str] = Field(default=None, description="Detailed case overview")
    status: str = Field(default="ACTIVE", description="Case status (e.g. OPEN, ACTIVE, CLOSED)")
    incident_date: Optional[str] = Field(default=None, description="Date/time of the incident (ISO 8601)")
    location_id: Optional[str] = Field(default=None, description="Primary incident location ID")


class Event(BaseEntity):
    """Event entity model.
    
    Fields defined in DATA_SCHEMA.md:
    - id
    - event_type
    - timestamp
    - location_id
    - description
    - source_id (also aliased/unified into source_ids)
    """
    entity_type: EntityType = Field(default=EntityType.EVENT)
    event_type: str = Field(..., description="Type of event (e.g. VEHICLE_SIGHTING, CALL_LOG, TRANSACTION, RAID)")
    timestamp: Optional[str] = Field(default=None, description="ISO 8601 event timestamp")
    location_id: Optional[str] = Field(default=None, description="Location ID where event occurred")
    description: Optional[str] = Field(default=None, description="Event summary or detail")
    source_id: Optional[str] = Field(default=None, description="Direct source document / evidence ID")


Entity = Union[Person, Phone, Vehicle, Location, Organization, Account, Case, Event]
