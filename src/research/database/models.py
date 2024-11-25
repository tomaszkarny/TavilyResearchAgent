# src/research/database/models.py

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ArticleSummary(BaseModel):
    """Basic summary of research article"""
    main_points: List[str]
    summary: str
    relevance: float = Field(ge=0.0, le=1.0)

class ResearchArticle(BaseModel):
    """Research article with structured data"""
    title: str
    url: str
    summary: ArticleSummary
    score: float = Field(ge=0.0, le=1.0)
    processed_at: datetime = Field(default_factory=datetime.utcnow)

class ResearchSummary(BaseModel):
    """Overall research summary"""
    topic: str
    key_findings: List[str]
    articles: List[ResearchArticle]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BlogSection(BaseModel):
    """Blog section structure"""
    heading: str
    content: str
    key_points: List[str]

class BlogPost(BaseModel):
    """Blog post structure"""
    title: str
    introduction: str
    key_sections: List[BlogSection]
    conclusion: str
    created_at: datetime = Field(default_factory=datetime.utcnow)