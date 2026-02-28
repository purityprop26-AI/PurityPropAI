"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Pydantic Schemas — Request/Response Models
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum


# --- Enums ---
class PropertyTypeEnum(str, Enum):
    apartment = "apartment"
    villa = "villa"
    plot = "plot"
    house = "house"
    commercial = "commercial"
    office = "office"
    warehouse = "warehouse"
    penthouse = "penthouse"
    studio = "studio"
    farmhouse = "farmhouse"
    land = "land"


class ListingTypeEnum(str, Enum):
    sale = "sale"
    rent = "rent"
    lease = "lease"
    auction = "auction"


class PropertyStatusEnum(str, Enum):
    available = "available"
    sold = "sold"
    rented = "rented"
    under_construction = "under_construction"
    upcoming = "upcoming"
    reserved = "reserved"
    delisted = "delisted"


# --- Query Request ---
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="Natural language query")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters")
    city: str = Field(default="Chennai")
    property_type: Optional[PropertyTypeEnum] = None
    listing_type: Optional[ListingTypeEnum] = None
    min_price: Optional[float] = Field(default=None, ge=0)
    max_price: Optional[float] = Field(default=None, ge=0)
    bedrooms: Optional[int] = Field(default=None, ge=0, le=20)
    locality: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    radius_km: Optional[float] = Field(default=5.0, ge=0.1, le=100)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_analytics: bool = Field(default=False)
    stream: bool = Field(default=False, description="Enable streaming response")


# --- Property Response ---
class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    description: Optional[str] = None
    property_type: str
    listing_type: str
    status: str
    price: float
    price_per_sqft: Optional[float] = None
    currency: str = "INR"
    carpet_area_sqft: Optional[float] = None
    built_up_area_sqft: Optional[float] = None
    locality: str
    city: str
    pincode: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking_slots: Optional[int] = None
    furnishing: Optional[str] = None
    facing: Optional[str] = None
    attributes: Dict[str, Any] = {}
    amenities: List[Any] = []
    images: List[Any] = []
    builder_name: Optional[str] = None
    project_name: Optional[str] = None
    rera_id: Optional[str] = None
    is_verified: bool = False
    is_featured: bool = False
    listed_at: Optional[datetime] = None
    vector_score: Optional[float] = None
    text_score: Optional[float] = None
    distance_km: Optional[float] = None
    combined_score: Optional[float] = None


# --- Query Response ---
class QueryResponse(BaseModel):
    query: str
    properties: List[PropertyResponse]
    total_results: int
    analytics: Optional[Dict[str, Any]] = None
    ai_summary: Optional[str] = None
    retrieval_method: str = "hybrid"
    latency_ms: float
    metadata: Dict[str, Any] = {}


# --- Analytics Response ---
class AnalyticsResponse(BaseModel):
    locality: str
    city: str = "Chennai"
    cagr: Optional[float] = None
    liquidity_score: Optional[float] = None
    absorption_rate: Optional[float] = None
    avg_price_per_sqft: Optional[float] = None
    median_price: Optional[float] = None
    demand_supply_ratio: Optional[float] = None
    forecast: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    computed_at: Optional[datetime] = None
    confidence_score: Optional[float] = None


# --- Health Response ---
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    database: Dict[str, Any]
    groq: Dict[str, Any]
    uptime_seconds: float


# --- Metrics Response ---
class MetricsResponse(BaseModel):
    total_queries: int
    avg_latency_ms: float
    p95_latency_ms: float
    cache_hit_rate: float
    groq_metrics: Dict[str, Any]
    db_pool_stats: Dict[str, Any]
    vector_index_health: Dict[str, Any]


# --- Error Response ---
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
