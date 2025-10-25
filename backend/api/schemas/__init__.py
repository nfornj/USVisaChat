"""
API Schemas for Visa Platform
All Pydantic models for request/response validation
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


# Search schemas
class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 10


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_found: int
    processing_time_ms: int


class StatsResponse(BaseModel):
    collection_name: str
    total_vectors: int
    status: str
    vector_dimensions: int
    embedding_model: str


class HealthResponse(BaseModel):
    status: str
    message: str
    version: str


# Authentication schemas
class AuthRequestCodeRequest(BaseModel):
    email: str
    display_name: str


class AuthRequestCodeResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[str] = None


class AuthVerifyCodeRequest(BaseModel):
    email: str
    code: str


class AuthVerifyCodeResponse(BaseModel):
    success: bool
    message: str
    session_token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class UpdateProfileRequest(BaseModel):
    session_token: str
    display_name: str


class UpdateProfileResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None


# Chat schemas
class EditMessageRequest(BaseModel):
    message_id: str
    new_content: str
    user_email: str
