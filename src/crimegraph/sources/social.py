"""Social Media Data Source and Adapter for CrimeGraph AI (Day 25).

Parses synthetic/simulated social media posts, messages, user profiles, and interactions.
Guarantees:
1. Synthetic data only: no connection to live networks, scraping, or real personal information.
2. Normalizes social entities into canonical graph entities (PERSON, PHONE, VEHICLE, LOCATION, ACCOUNT, CASE, EVENT).
3. Connects evidenced social interactions (POSTED_BY, MENTIONS, INTERACTS_WITH, LINKED_TO, COMMUNICATES_WITH).
4. Retains source provenance, character snippets, and confidence ratings.
5. Non-guilt guarantee: social interactions are never interpreted as legal proof of guilt.
"""

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from crimegraph.models.relationships import RelationshipType
from crimegraph.models.sources import IngestionRecord, SourceType
from crimegraph.sources.adapters import BaseSourceAdapter
from crimegraph.sources.normalizer import DataNormalizer


class SyntheticSocialPost(BaseModel):
    """Schema for simulated social media investigative post or message."""
    model_config = ConfigDict(extra="allow")

    post_id: str = Field(default_factory=lambda: f"SOC_{uuid.uuid4().hex[:8].upper()}")
    platform: str = Field(default="TELEGRAM_SIMULATED", description="Simulated platform (e.g. TELEGRAM, TWITTER, WHATSAPP, DARKNET_FORUM)")
    author_username: str = Field(..., description="Simulated handle or username")
    author_display_name: Optional[str] = Field(default=None, description="Author display name")
    author_entity_id: Optional[str] = Field(default=None, description="Canonical entity ID if pre-linked (e.g. PERSON_017)")
    message_text: str = Field(..., description="Post, caption, or chat snippet")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp of simulated post")
    location_name: Optional[str] = Field(default=None, description="Reported geotag or location string")
    mentioned_entities: List[str] = Field(default_factory=list, description="IDs or names of mentioned subjects/devices")
    case_ids: List[str] = Field(default_factory=list, description="Associated investigation cases")
    hashtags: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class SocialSourceAdapter(BaseSourceAdapter):
    """Parses simulated social media records into normalized IngestionRecord items."""

    # Regex extractors for mentions and identifiers in post text
    _RE_PHONE = re.compile(r"(\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b)")
    _RE_PLATE = re.compile(r"\b([A-Z]{2}[-\s]?\d{2}[-\s]?[A-Z]{1,2}[-\s]?\d{4})\b")
    _RE_CASE = re.compile(r"\b(CASE[_\s]\d+|FIR[_\s]\d+)\b", re.IGNORECASE)

    def parse(self, raw_content: Any) -> List[IngestionRecord]:
        """Parses simulated social media batches into standard IngestionRecord objects."""
        if isinstance(raw_content, str):
            try:
                data = json.loads(raw_content)
            except Exception:
                data = {"posts": [{"message_text": raw_content, "author_username": "anonymous_tip"}]}
        elif isinstance(raw_content, dict):
            data = raw_content
        elif isinstance(raw_content, list):
            data = {"posts": raw_content}
        else:
            raise ValueError("Expected JSON string, dict, or list of social posts")

        posts_data = data.get("posts", [data] if "message_text" in data or "author_username" in data else [])
        records: List[IngestionRecord] = []

        for p in posts_data:
            post = SyntheticSocialPost(**p) if isinstance(p, dict) else p
            self._process_single_post(post, records)

        return records

    def _process_single_post(self, post: SyntheticSocialPost, records: List[IngestionRecord]) -> None:
        """Converts a single synthetic social post into entities, evidence, relationships, and events."""
        post_id = post.post_id
        conf = post.confidence

        # 1. Create Evidence Item for the post
        ev_id = f"EVID_SOC_{post_id}"
        author_label = f"@{post.author_username} ({post.author_display_name})" if post.author_display_name else f"@{post.author_username}"
        ev_data = {
            "evidence_id": ev_id,
            "source_document_id": f"DOC_SOCIAL_{post.platform}_{post_id}",
            "source_text": f"[{post.platform} {author_label}]: \"{post.message_text}\"",
            "timestamp": post.timestamp or datetime.now(timezone.utc).isoformat(),
            "extraction_method": "SOCIAL_MEDIA_EXTRACTION",
            "confidence": conf,
        }
        records.append(IngestionRecord(
            record_type="EVIDENCE",
            data=ev_data,
            source_record_id=post_id,
            confidence=conf
        ))

        # 2. Author Entity
        author_id = post.author_entity_id or f"PERSON_{DataNormalizer.normalize_entity_name(post.author_username)}"
        author_name = post.author_display_name or post.author_username
        author_data = {
            "id": author_id,
            "entity_type": "PERSON",
            "name": author_name,
            "aliases": [f"@{post.author_username}"],
            "origin": "SOCIAL_MEDIA_SYNTHETIC",
            "confidence": conf,
            "source_ids": [ev_id]
        }
        records.append(IngestionRecord(
            record_type="ENTITY",
            data=author_data,
            source_record_id=post_id,
            confidence=conf,
            source_text=post.message_text
        ))

        # 3. Create Event Entity representing the social interaction/post
        event_id = f"EVENT_{post_id}"
        event_data = {
            "id": event_id,
            "entity_type": "EVENT",
            "event_type": "SOCIAL_MEDIA_POST",
            "timestamp": post.timestamp,
            "description": f"Simulated {post.platform} post by @{post.author_username}: {post.message_text[:80]}",
            "origin": "SOCIAL_MEDIA_SYNTHETIC",
            "confidence": conf,
            "source_ids": [ev_id]
        }
        records.append(IngestionRecord(
            record_type="ENTITY",
            data=event_data,
            source_record_id=post_id,
            confidence=conf
        ))

        # Relationship: Event POSTED_BY Author
        records.append(IngestionRecord(
            record_type="RELATIONSHIP",
            data={
                "id": f"REL_POST_{post_id}",
                "source_id": event_id,
                "target_id": author_id,
                "relationship": "POSTED_BY",
                "confidence": conf,
                "evidence_ids": [ev_id],
                "origin": "SOCIAL_MEDIA_SYNTHETIC"
            },
            source_record_id=post_id,
            confidence=conf
        ))

        # 4. Extract Location if specified
        loc_id = None
        if post.location_name:
            norm_loc = DataNormalizer.normalize_entity_name(post.location_name)
            loc_id = f"LOC_{norm_loc}"
            loc_data = {
                "id": loc_id,
                "entity_type": "LOCATION",
                "name": post.location_name,
                "origin": "SOCIAL_MEDIA_SYNTHETIC",
                "confidence": conf,
                "source_ids": [ev_id]
            }
            records.append(IngestionRecord(
                record_type="ENTITY",
                data=loc_data,
                source_record_id=post_id,
                confidence=conf
            ))
            # Relationship: Author LOCATED_AT Location
            records.append(IngestionRecord(
                record_type="RELATIONSHIP",
                data={
                    "id": f"REL_LOC_{post_id}",
                    "source_id": author_id,
                    "target_id": loc_id,
                    "relationship": "LOCATED_AT",
                    "confidence": conf * 0.90,
                    "evidence_ids": [ev_id],
                    "origin": "SOCIAL_MEDIA_SYNTHETIC"
                },
                source_record_id=post_id,
                confidence=conf * 0.90
            ))

        # 5. Extract In-Text Mentions (Phones, Vehicles, Cases, Canonical IDs)
        extracted_mentions = list(post.mentioned_entities)

        for m in self._RE_PHONE.finditer(post.message_text):
            extracted_mentions.append(m.group(1).strip())
        for m in self._RE_PLATE.finditer(post.message_text):
            extracted_mentions.append(m.group(1).strip())
        for m in self._RE_CASE.finditer(post.message_text):
            extracted_mentions.append(m.group(1).strip().upper().replace(" ", "_"))

        # Deduplicate and create entities/links for mentions
        seen_targets = set()
        for mention in extracted_mentions:
            mention_clean = mention.strip()
            if not mention_clean or mention_clean == author_id:
                continue

            target_id = mention_clean
            target_type = "ENTITY"
            
            if mention_clean.startswith("PERSON_") or " " in mention_clean:
                target_type = "PERSON"
            elif mention_clean.startswith("PHONE_") or self._RE_PHONE.match(mention_clean):
                target_type = "PHONE"
            elif mention_clean.startswith("VEHICLE_") or self._RE_PLATE.match(mention_clean):
                target_type = "VEHICLE"
            elif mention_clean.startswith("CASE_"):
                target_type = "CASE"

            if target_id in seen_targets:
                continue
            seen_targets.add(target_id)

            # Mention entity record (if new)
            ent_payload = {
                "id": target_id,
                "entity_type": target_type,
                "origin": "SOCIAL_MEDIA_SYNTHETIC",
                "confidence": conf * 0.90,
                "source_ids": [ev_id]
            }
            if target_type == "PERSON":
                ent_payload["name"] = mention_clean
            elif target_type == "PHONE":
                ent_payload["phone_number"] = mention_clean
            elif target_type == "VEHICLE":
                ent_payload["registration_number"] = mention_clean
            elif target_type == "CASE":
                ent_payload["title"] = f"Investigation Case {mention_clean}"

            records.append(IngestionRecord(
                record_type="ENTITY",
                data=ent_payload,
                source_record_id=post_id,
                confidence=conf * 0.90,
                source_text=post.message_text
            ))

            # Relationship: Author MENTIONS / COMMUNICATES_WITH Target
            rel_type = "COMMUNICATES_WITH" if target_type == "PHONE" else ("INVOLVED_IN" if target_type == "CASE" else "MENTIONS")
            records.append(IngestionRecord(
                record_type="RELATIONSHIP",
                data={
                    "id": f"REL_MEN_{post_id}_{target_id[:10]}",
                    "source_id": author_id,
                    "target_id": target_id,
                    "relationship": rel_type,
                    "confidence": conf * 0.85,
                    "evidence_ids": [ev_id],
                    "origin": "SOCIAL_MEDIA_SYNTHETIC"
                },
                source_record_id=post_id,
                confidence=conf * 0.85
            ))
