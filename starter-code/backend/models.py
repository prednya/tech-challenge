"""
Database models for the AI Product Discovery Assistant.

This module defines all the SQLModel classes used for database operations,
including products, sessions, cart management, and context tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlmodel import SQLModel, Field, Column, JSON
from pydantic import BaseModel
from pydantic import field_validator


# Enums
class EventType(str, Enum):
    # SSE event types
    TEXT_CHUNK = "text_chunk"
    FUNCTION_CALL = "function_call"
    COMPLETION = "completion"
    ERROR = "error"
    CONTEXT_UPDATE = "context"
    CONNECTION = "connection"


class ProductCategory(str, Enum):
    # Product categories (uppercase to match DB enum labels)
    ELECTRONICS = "ELECTRONICS"
    CLOTHING = "CLOTHING"
    HOME = "HOME"
    BOOKS = "BOOKS"
    SPORTS = "SPORTS"
    BEAUTY = "BEAUTY"
    OTHER = "OTHER"


# Database Models
class Product(SQLModel, table=True):
    # Product catalog model
    
    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    description: str
    long_description: Optional[str] = None
    price: float = Field(ge=0)
    category: ProductCategory = Field(index=True)
    image_url: str
    additional_images: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    in_stock: bool = Field(default=True, index=True)
    stock_quantity: int = Field(default=0, ge=0)
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    reviews_count: int = Field(default=0, ge=0)
    specifications: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    features: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SessionContext(SQLModel, table=True):
    # Session context for tracking user interactions
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True)
    context_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SearchContext(SQLModel, table=True):
    # Context for search operations to prevent AI hallucination
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    search_query: str
    results: List[str] = Field(sa_column=Column(JSON))  # Product IDs
    category: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CartItem(SQLModel, table=True):
    # Shopping cart items
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    product_id: str = Field(foreign_key="product.id")
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(ge=0)
    total_price: float = Field(ge=0)
    added_at: datetime = Field(default_factory=datetime.utcnow)


# Pydantic Models for API
class ChatMessage(BaseModel):
    # Chat message from user
    message: str
    context: Optional[Dict[str, Any]] = None


class SSEEvent(BaseModel):
    # Server-Sent Event structure
    event: EventType
    data: Dict[str, Any]
    id: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ProductSearchRequest(BaseModel):
    # Product search request
    query: str
    category: Optional[ProductCategory] = None
    limit: int = Field(default=10, ge=1, le=50)
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    session_id: str

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v):
        if v is None or isinstance(v, ProductCategory):
            return v
        if isinstance(v, str):
            s = v.strip().upper()
            # Try match by name
            if s in ProductCategory.__members__:
                return ProductCategory[s]
            # Try value match (case-insensitive)
            for cat in ProductCategory:
                if cat.value.upper() == s:
                    return cat
        # Unknown: ignore instead of raising
        return None


class ProductDetailsRequest(BaseModel):
    # Product details request
    product_id: str
    include_recommendations: bool = Field(default=True)
    session_id: str


class AddToCartRequest(BaseModel):
    # Add to cart request
    product_id: str
    quantity: int = Field(default=1, ge=1)
    session_id: str


class RecommendationsRequest(BaseModel):
    # Recommendations request
    based_on: str  # product_id or category
    recommendation_type: str = Field(default="similar")
    max_results: int = Field(default=5, ge=1, le=20)
    session_id: str


# Response Models
class ProductResponse(BaseModel):
    # Product information response
    id: str
    name: str
    description: str
    price: float
    category: str
    image_url: str
    in_stock: bool
    rating: Optional[float] = None
    reviews_count: int


class ProductDetailsResponse(BaseModel):
    # Detailed product information response
    product: Product
    recommendations: Optional[List[ProductResponse]] = None
    validation: Dict[str, bool]


class CartSummary(BaseModel):
    # Shopping cart summary
    total_items: int
    total_products: int
    subtotal: float
    estimated_tax: Optional[float] = None
    estimated_total: Optional[float] = None


class CartItemResponse(BaseModel):
    # Cart item response
    id: int
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    added_at: datetime


class AddToCartResponse(BaseModel):
    # Add to cart response
    cart_item: CartItemResponse
    cart_summary: CartSummary
    validation: Dict[str, bool]


class SearchResultsResponse(BaseModel):
    # Search results response
    products: List[ProductResponse]
    total_results: int
    search_context: Dict[str, Any]
    context_updated: bool


class RecommendationsResponse(BaseModel):
    # Recommendations response
    recommendations: List[ProductResponse]
    recommendation_context: Dict[str, Any]


# Function Call Models
class FunctionCall(BaseModel):
    # AI function call structure
    name: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationResult(BaseModel):
    # Validation result for function calls
    valid: bool
    errors: List[str] = Field(default_factory=list)
    suggestions: Optional[List[Dict[str, Any]]] = None
    context_updated: bool = False
