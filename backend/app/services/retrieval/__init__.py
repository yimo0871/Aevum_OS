"""Retrieval & Inference Layer: matching, ranking, priority chain."""

from app.services.retrieval.embedder import EmbedderProtocol, HashEmbedder, OpenAIEmbedder, get_embedder
from app.services.retrieval.matcher import ExperienceMatcher, MatchResult
from app.services.retrieval.priority_chain import PriorityChain, PriorityChainResult, PriorityLevel
from app.services.retrieval.ranker import ExperienceRanker, RankedResult, ScoreFactors

__all__ = [
    # Embedder
    "EmbedderProtocol",
    "OpenAIEmbedder",
    "HashEmbedder",
    "get_embedder",
    # Matcher
    "ExperienceMatcher",
    "MatchResult",
    # Ranker
    "ExperienceRanker",
    "RankedResult",
    "ScoreFactors",
    # Priority Chain
    "PriorityChain",
    "PriorityChainResult",
    "PriorityLevel",
]
