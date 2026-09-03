"""Compatibility module for Community Detection Engine.

Re-exports CommunityDetectionEngine and CommunityDetector alias from `crimegraph.communities.engine`.
"""

from crimegraph.communities.engine import CommunityDetectionEngine

CommunityDetector = CommunityDetectionEngine

__all__ = ["CommunityDetectionEngine", "CommunityDetector"]
