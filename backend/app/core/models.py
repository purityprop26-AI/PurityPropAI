"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
SQLAlchemy Async Models
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Numeric, SmallInteger, Integer, Boolean,
    DateTime, Enum as SAEnum, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from geoalchemy2 import Geometry

from app.core.database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    property_type = Column(String(20), nullable=False, default="apartment")
    listing_type = Column(String(10), nullable=False, default="sale")
    status = Column(String(20), nullable=False, default="available")

    # Pricing
    price = Column(Numeric(15, 2), nullable=False)
    price_per_sqft = Column(Numeric(10, 2))
    currency = Column(String(3), default="INR")

    # Area
    carpet_area_sqft = Column(Numeric(10, 2))
    built_up_area_sqft = Column(Numeric(10, 2))
    super_built_up_area_sqft = Column(Numeric(10, 2))
    plot_area_sqft = Column(Numeric(10, 2))

    # Location
    address_line1 = Column(Text)
    address_line2 = Column(Text)
    locality = Column(Text, nullable=False)
    sub_locality = Column(Text)
    city = Column(Text, nullable=False, default="Chennai")
    state = Column(Text, default="Tamil Nadu")
    pincode = Column(String(10))
    country = Column(String(3), default="IND")

    # Spatial
    location = Column(Geometry("POINT", srid=4326))
    boundary = Column(Geometry("POLYGON", srid=4326))

    # Details
    bedrooms = Column(SmallInteger)
    bathrooms = Column(SmallInteger)
    balconies = Column(SmallInteger)
    floor_number = Column(SmallInteger)
    total_floors = Column(SmallInteger)
    parking_slots = Column(SmallInteger, default=0)
    furnishing = Column(String(20))
    facing = Column(String(20))
    age_of_property = Column(SmallInteger)

    # JSONB
    attributes = Column(JSONB, default={})
    amenities = Column(JSONB, default=[])
    nearby_places = Column(JSONB, default=[])
    price_history = Column(JSONB, default=[])
    images = Column(JSONB, default=[])

    # Vector embedding
    embedding = Column(Vector(384))

    # Metadata
    data_source = Column(String(20), default="manual")
    source_url = Column(Text)
    builder_name = Column(Text)
    project_name = Column(Text)
    rera_id = Column(String(50))
    is_verified = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    inquiry_count = Column(Integer, default=0)

    # Timestamps
    listed_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    sold_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    deleted_at = Column(DateTime(timezone=True))


class MarketAnalytics(Base):
    __tablename__ = "market_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locality = Column(Text, nullable=False)
    city = Column(Text, nullable=False, default="Chennai")
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    avg_price_per_sqft = Column(Numeric(10, 2))
    median_price = Column(Numeric(15, 2))
    total_listings = Column(Integer)
    total_sold = Column(Integer)
    absorption_rate = Column(Numeric(5, 4))
    liquidity_score = Column(Numeric(5, 4))
    cagr = Column(Numeric(8, 6))
    price_volatility = Column(Numeric(8, 6))
    demand_supply_ratio = Column(Numeric(8, 4))
    inventory_months = Column(Numeric(6, 2))

    forecast_data = Column(JSONB, default={})
    risk_assessment = Column(JSONB, default={})
    centroid = Column(Geometry("POINT", srid=4326))

    computed_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    model_version = Column(String(20))
    confidence_score = Column(Numeric(5, 4))


class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True))
    query_text = Column(Text, nullable=False)
    query_embedding = Column(Vector(384))
    filters = Column(JSONB, default={})
    result_count = Column(Integer)
    latency_ms = Column(Numeric(10, 2))
    retrieval_method = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))


class ForecastAudit(Base):
    __tablename__ = "forecast_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locality = Column(Text, nullable=False)
    forecast_type = Column(String(30), nullable=False)
    input_params = Column(JSONB, nullable=False)
    output_result = Column(JSONB, nullable=False)
    model_version = Column(String(20))
    mape = Column(Numeric(8, 6))
    execution_time_ms = Column(Numeric(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))


class HallucinationLog(Base):
    __tablename__ = "hallucination_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), nullable=False)
    narrative_output = Column(Text)
    tool_outputs = Column(JSONB)
    retrieved_data = Column(JSONB)
    mismatch_detected = Column(Boolean, default=False)
    mismatch_details = Column(JSONB)
    judge_verdict = Column(String(20))
    action_taken = Column(String(30))
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
