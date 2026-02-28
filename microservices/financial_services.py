"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Deterministic Microservices — Stateless Financial Computations

ALL numeric logic is deterministic and tool-based.
The LLM MUST NOT compute any of these values directly.
"""
from __future__ import annotations
import math
import json
import time
import structlog
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

logger = structlog.get_logger(__name__)


# ============================================
# INPUT / OUTPUT SCHEMAS
# ============================================

class CAGRInput(BaseModel):
    """Input for CAGR calculation."""
    beginning_value: float = Field(..., gt=0, description="Starting value")
    ending_value: float = Field(..., gt=0, description="Ending value")
    years: float = Field(..., gt=0, le=100, description="Number of years")

    @field_validator("years")
    @classmethod
    def validate_years(cls, v):
        if v <= 0:
            raise ValueError("years must be positive")
        return v


class CAGROutput(BaseModel):
    cagr: float = Field(..., description="CAGR as decimal (e.g. 0.12 = 12%)")
    cagr_percent: float = Field(..., description="CAGR as percentage")
    beginning_value: float
    ending_value: float
    years: float
    computed_at: str
    service: str = "cagr_microservice"


class LiquidityInput(BaseModel):
    """Input for liquidity score calculation."""
    total_listings: int = Field(..., ge=0)
    total_sold: int = Field(..., ge=0)
    avg_days_on_market: float = Field(..., ge=0)
    price_volatility: float = Field(..., ge=0, le=1)
    market_benchmark_days: float = Field(default=90.0, gt=0)


class LiquidityOutput(BaseModel):
    liquidity_score: float = Field(..., ge=0, le=1)
    sale_ratio: float
    time_factor: float
    volatility_penalty: float
    rating: str
    computed_at: str
    service: str = "liquidity_microservice"


class AbsorptionInput(BaseModel):
    """Input for absorption rate calculation."""
    total_sold: int = Field(..., ge=0)
    period_months: float = Field(..., gt=0, le=120)
    active_inventory: int = Field(..., ge=0)


class AbsorptionOutput(BaseModel):
    absorption_rate: float
    monthly_sales: float
    months_of_supply: Optional[float]
    market_condition: str
    computed_at: str
    service: str = "absorption_microservice"


class DistanceDecayInput(BaseModel):
    """Input for distance-decay premium calculation."""
    base_price_per_sqft: float = Field(..., gt=0)
    distances_km: List[Dict[str, Any]] = Field(
        ...,
        description="List of {name, distance_km, weight} for key landmarks"
    )
    decay_rate: float = Field(default=0.15, gt=0, lt=1)


class DistanceDecayOutput(BaseModel):
    adjusted_price_per_sqft: float
    premium_percent: float
    distance_scores: List[Dict[str, Any]]
    computed_at: str
    service: str = "distance_decay_microservice"


class ForecastInput(BaseModel):
    """Input for forecast ensemble."""
    historical_prices: List[float] = Field(..., min_length=4)
    periods: int = Field(default=12, ge=1, le=60)
    method: str = Field(default="ensemble")


class ForecastOutput(BaseModel):
    forecast_values: List[float]
    trend: str
    avg_growth_rate: float
    confidence_interval: Dict[str, List[float]]
    methods_used: List[str]
    mape: Optional[float]
    computed_at: str
    service: str = "forecast_microservice"


class RiskInput(BaseModel):
    """Input for risk synthesis."""
    cagr: Optional[float] = None
    liquidity_score: Optional[float] = None
    absorption_rate: Optional[float] = None
    price_volatility: Optional[float] = None
    distance_premium: Optional[float] = None
    market_age_years: Optional[float] = None


class RiskOutput(BaseModel):
    overall_risk_score: float = Field(..., ge=0, le=1)
    risk_level: str
    risk_factors: List[Dict[str, Any]]
    recommendations: List[str]
    computed_at: str
    service: str = "risk_microservice"


# ============================================
# MICROSERVICE IMPLEMENTATIONS
# ============================================

def compute_cagr(input_data: CAGRInput) -> CAGROutput:
    """Compute Compound Annual Growth Rate — deterministic."""
    start = time.perf_counter()

    cagr = (input_data.ending_value / input_data.beginning_value) ** (1.0 / input_data.years) - 1.0

    logger.info(
        "cagr_computed",
        beginning=input_data.beginning_value,
        ending=input_data.ending_value,
        years=input_data.years,
        cagr=round(cagr, 6),
        elapsed_ms=round((time.perf_counter() - start) * 1000, 3),
    )

    return CAGROutput(
        cagr=round(cagr, 6),
        cagr_percent=round(cagr * 100, 4),
        beginning_value=input_data.beginning_value,
        ending_value=input_data.ending_value,
        years=input_data.years,
        computed_at=datetime.utcnow().isoformat(),
    )


def compute_liquidity_score(input_data: LiquidityInput) -> LiquidityOutput:
    """Compute liquidity score (0-1) — deterministic."""
    start = time.perf_counter()

    # Sale ratio: sold / listed
    sale_ratio = (
        input_data.total_sold / input_data.total_listings
        if input_data.total_listings > 0
        else 0.0
    )

    # Time factor: benchmark / actual (higher = more liquid)
    time_factor = (
        min(input_data.market_benchmark_days / input_data.avg_days_on_market, 1.0)
        if input_data.avg_days_on_market > 0
        else 0.0
    )

    # Volatility penalty
    volatility_penalty = 1.0 - input_data.price_volatility

    # Weighted composite
    liquidity = (
        sale_ratio * 0.40
        + time_factor * 0.35
        + volatility_penalty * 0.25
    )
    liquidity = round(max(0.0, min(1.0, liquidity)), 4)

    # Rating
    if liquidity >= 0.75:
        rating = "highly_liquid"
    elif liquidity >= 0.50:
        rating = "moderately_liquid"
    elif liquidity >= 0.25:
        rating = "illiquid"
    else:
        rating = "frozen"

    logger.info(
        "liquidity_computed",
        score=liquidity,
        rating=rating,
        elapsed_ms=round((time.perf_counter() - start) * 1000, 3),
    )

    return LiquidityOutput(
        liquidity_score=liquidity,
        sale_ratio=round(sale_ratio, 4),
        time_factor=round(time_factor, 4),
        volatility_penalty=round(volatility_penalty, 4),
        rating=rating,
        computed_at=datetime.utcnow().isoformat(),
    )


def compute_absorption_rate(input_data: AbsorptionInput) -> AbsorptionOutput:
    """Compute absorption rate — deterministic."""
    start = time.perf_counter()

    monthly_sales = input_data.total_sold / input_data.period_months
    absorption_rate = (
        monthly_sales / input_data.active_inventory
        if input_data.active_inventory > 0
        else 0.0
    )
    months_of_supply = (
        input_data.active_inventory / monthly_sales
        if monthly_sales > 0
        else None
    )

    # Market condition
    if months_of_supply is None:
        market_condition = "no_data"
    elif months_of_supply < 4:
        market_condition = "seller_market"
    elif months_of_supply < 7:
        market_condition = "balanced"
    else:
        market_condition = "buyer_market"

    logger.info(
        "absorption_computed",
        rate=round(absorption_rate, 4),
        months_of_supply=round(months_of_supply, 2) if months_of_supply else None,
        condition=market_condition,
        elapsed_ms=round((time.perf_counter() - start) * 1000, 3),
    )

    return AbsorptionOutput(
        absorption_rate=round(absorption_rate, 4),
        monthly_sales=round(monthly_sales, 2),
        months_of_supply=round(months_of_supply, 2) if months_of_supply else None,
        market_condition=market_condition,
        computed_at=datetime.utcnow().isoformat(),
    )


def compute_distance_decay_premium(input_data: DistanceDecayInput) -> DistanceDecayOutput:
    """Compute distance-decay location premium — deterministic."""
    start = time.perf_counter()

    distance_scores = []
    total_weighted_score = 0.0
    total_weight = 0.0

    for item in input_data.distances_km:
        name = item.get("name", "unknown")
        distance = item.get("distance_km", 0)
        weight = item.get("weight", 1.0)

        # Exponential decay: score = e^(-decay * distance)
        score = math.exp(-input_data.decay_rate * distance)

        distance_scores.append({
            "name": name,
            "distance_km": round(distance, 2),
            "weight": weight,
            "decay_score": round(score, 4),
            "weighted_score": round(score * weight, 4),
        })

        total_weighted_score += score * weight
        total_weight += weight

    # Average weighted score
    avg_score = total_weighted_score / total_weight if total_weight > 0 else 0

    # Premium: max 40% boost for perfect proximity
    premium_percent = round(avg_score * 40.0, 2)
    adjusted_price = round(
        input_data.base_price_per_sqft * (1 + premium_percent / 100),
        2
    )

    logger.info(
        "distance_decay_computed",
        premium_pct=premium_percent,
        adjusted_price=adjusted_price,
        landmarks=len(input_data.distances_km),
        elapsed_ms=round((time.perf_counter() - start) * 1000, 3),
    )

    return DistanceDecayOutput(
        adjusted_price_per_sqft=adjusted_price,
        premium_percent=premium_percent,
        distance_scores=distance_scores,
        computed_at=datetime.utcnow().isoformat(),
    )


def compute_forecast_ensemble(input_data: ForecastInput) -> ForecastOutput:
    """Compute price forecast using simple ensemble — deterministic."""
    start = time.perf_counter()
    prices = input_data.historical_prices
    n = len(prices)

    # Method 1: Simple Moving Average Trend
    if n >= 3:
        sma_3 = sum(prices[-3:]) / 3
    else:
        sma_3 = prices[-1]

    # Method 2: Linear regression forecast
    x_mean = (n - 1) / 2
    y_mean = sum(prices) / n
    numerator = sum((i - x_mean) * (prices[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0
    intercept = y_mean - slope * x_mean

    linear_forecasts = [round(slope * (n + i) + intercept, 2) for i in range(input_data.periods)]

    # Method 3: Exponential smoothing
    alpha = 0.3
    smoothed = [prices[0]]
    for i in range(1, n):
        smoothed.append(alpha * prices[i] + (1 - alpha) * smoothed[-1])
    exp_forecasts = []
    last_smoothed = smoothed[-1]
    for i in range(input_data.periods):
        forecast_val = last_smoothed + slope * (i + 1)
        exp_forecasts.append(round(forecast_val, 2))

    # Ensemble: weighted average
    ensemble = []
    for i in range(input_data.periods):
        val = (
            linear_forecasts[i] * 0.4
            + exp_forecasts[i] * 0.4
            + sma_3 * 0.2
        )
        ensemble.append(round(val, 2))

    # Confidence interval (±1 std dev of historical)
    std_dev = (sum((p - y_mean) ** 2 for p in prices) / n) ** 0.5
    lower = [round(v - 1.96 * std_dev, 2) for v in ensemble]
    upper = [round(v + 1.96 * std_dev, 2) for v in ensemble]

    # Growth rate
    if prices[0] > 0:
        total_growth = (ensemble[-1] / prices[0]) - 1
        avg_growth = total_growth / max(input_data.periods, 1)
    else:
        avg_growth = 0.0

    # Trend
    if slope > 0.01 * y_mean:
        trend = "upward"
    elif slope < -0.01 * y_mean:
        trend = "downward"
    else:
        trend = "stable"

    # MAPE (on last 20% of historical as test)
    test_size = max(1, n // 5)
    train = prices[:n - test_size]
    test = prices[n - test_size:]
    if train and test:
        train_mean = sum(train) / len(train)
        mape = sum(abs((actual - train_mean) / actual) for actual in test if actual != 0) / len(test) * 100
    else:
        mape = None

    logger.info(
        "forecast_computed",
        periods=input_data.periods,
        trend=trend,
        avg_growth=round(avg_growth, 4),
        elapsed_ms=round((time.perf_counter() - start) * 1000, 3),
    )

    return ForecastOutput(
        forecast_values=ensemble,
        trend=trend,
        avg_growth_rate=round(avg_growth, 6),
        confidence_interval={"lower": lower, "upper": upper},
        methods_used=["linear_regression", "exponential_smoothing", "sma"],
        mape=round(mape, 4) if mape is not None else None,
        computed_at=datetime.utcnow().isoformat(),
    )


def compute_risk_synthesis(input_data: RiskInput) -> RiskOutput:
    """Synthesize risk from multiple indicators — deterministic."""
    start = time.perf_counter()

    factors = []
    scores = []

    # CAGR risk
    if input_data.cagr is not None:
        if input_data.cagr < 0:
            score = 0.8
            desc = "Negative growth indicates high risk"
        elif input_data.cagr < 0.05:
            score = 0.5
            desc = "Below-inflation growth"
        elif input_data.cagr < 0.15:
            score = 0.2
            desc = "Healthy growth rate"
        else:
            score = 0.3
            desc = "High growth may indicate bubble risk"
        factors.append({"factor": "cagr", "value": input_data.cagr, "risk_score": score, "description": desc})
        scores.append(score)

    # Liquidity risk
    if input_data.liquidity_score is not None:
        score = max(0, 1.0 - input_data.liquidity_score)
        factors.append({
            "factor": "liquidity",
            "value": input_data.liquidity_score,
            "risk_score": round(score, 4),
            "description": "Lower liquidity = higher risk"
        })
        scores.append(score)

    # Absorption risk
    if input_data.absorption_rate is not None:
        if input_data.absorption_rate < 0.05:
            score = 0.8
        elif input_data.absorption_rate < 0.15:
            score = 0.4
        else:
            score = 0.15
        factors.append({
            "factor": "absorption",
            "value": input_data.absorption_rate,
            "risk_score": score,
            "description": "Low absorption = oversupply risk"
        })
        scores.append(score)

    # Volatility risk
    if input_data.price_volatility is not None:
        score = min(1.0, input_data.price_volatility * 2)
        factors.append({
            "factor": "volatility",
            "value": input_data.price_volatility,
            "risk_score": round(score, 4),
            "description": "Higher volatility = higher risk"
        })
        scores.append(score)

    # Overall risk
    overall = sum(scores) / len(scores) if scores else 0.5
    overall = round(max(0.0, min(1.0, overall)), 4)

    # Risk level
    if overall >= 0.7:
        level = "high"
    elif overall >= 0.4:
        level = "moderate"
    else:
        level = "low"

    # Recommendations
    recommendations = []
    if overall >= 0.7:
        recommendations.append("Exercise extreme caution — high risk detected")
        recommendations.append("Diversify investments across locations")
    elif overall >= 0.4:
        recommendations.append("Moderate risk — conduct thorough due diligence")
        recommendations.append("Monitor market indicators quarterly")
    else:
        recommendations.append("Low risk — favorable market conditions")
        recommendations.append("Consider long-term investment strategy")

    if input_data.liquidity_score and input_data.liquidity_score < 0.3:
        recommendations.append("Low liquidity — expect longer exit timelines")
    if input_data.cagr and input_data.cagr > 0.15:
        recommendations.append("High growth may be unsustainable — verify fundamentals")

    logger.info(
        "risk_computed",
        overall=overall,
        level=level,
        factors_count=len(factors),
        elapsed_ms=round((time.perf_counter() - start) * 1000, 3),
    )

    return RiskOutput(
        overall_risk_score=overall,
        risk_level=level,
        risk_factors=factors,
        recommendations=recommendations,
        computed_at=datetime.utcnow().isoformat(),
    )


# ============================================
# SERVICE REGISTRY
# ============================================
SERVICES = {
    "cagr": {"function": compute_cagr, "input_schema": CAGRInput, "output_schema": CAGROutput},
    "liquidity": {"function": compute_liquidity_score, "input_schema": LiquidityInput, "output_schema": LiquidityOutput},
    "absorption": {"function": compute_absorption_rate, "input_schema": AbsorptionInput, "output_schema": AbsorptionOutput},
    "distance_decay": {"function": compute_distance_decay_premium, "input_schema": DistanceDecayInput, "output_schema": DistanceDecayOutput},
    "forecast": {"function": compute_forecast_ensemble, "input_schema": ForecastInput, "output_schema": ForecastOutput},
    "risk": {"function": compute_risk_synthesis, "input_schema": RiskInput, "output_schema": RiskOutput},
}


def execute_service(service_name: str, input_data: dict) -> dict:
    """Execute a microservice by name with validated input."""
    if service_name not in SERVICES:
        raise ValueError(f"Unknown service: {service_name}. Available: {list(SERVICES.keys())}")

    svc = SERVICES[service_name]
    validated_input = svc["input_schema"](**input_data)
    result = svc["function"](validated_input)
    return result.model_dump()
