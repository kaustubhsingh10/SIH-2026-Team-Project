"""Multi-Source Ingestion and Provenance Subsystem for CrimeGraph AI."""

from crimegraph.models.sources import (
    SourceType,
    SourceMetadata,
    ProvenanceRecord,
    SourceConflict,
    ConflictStatus,
    SourceCreateRequest,
    IngestionRecord,
    IngestionBatchRequest,
    IngestionBatchResponse,
    ConflictResolveRequest,
)
from crimegraph.sources.normalizer import DataNormalizer
from crimegraph.sources.resolver import SourceAwareEntityResolver
from crimegraph.sources.adapters import (
    BaseSourceAdapter,
    JsonImportAdapter,
    CaseRecordAdapter,
    IntelSourceAdapter,
)
from crimegraph.sources.social import (
    SocialSourceAdapter,
    SyntheticSocialPost,
)
from crimegraph.sources.engine import MultiSourceIngestionEngine

__all__ = [
    "SourceType",
    "SourceMetadata",
    "ProvenanceRecord",
    "SourceConflict",
    "ConflictStatus",
    "SourceCreateRequest",
    "IngestionRecord",
    "IngestionBatchRequest",
    "IngestionBatchResponse",
    "ConflictResolveRequest",
    "DataNormalizer",
    "SourceAwareEntityResolver",
    "BaseSourceAdapter",
    "JsonImportAdapter",
    "CaseRecordAdapter",
    "IntelSourceAdapter",
    "SocialSourceAdapter",
    "SyntheticSocialPost",
    "MultiSourceIngestionEngine",
]
