# src/research/database/models.py
"""
Database models and data structures for research
"""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ResearchSession:
    """Container for research session data"""
    query: str
    timestamp: datetime
    source: str = "tavily"
    processed: bool = False