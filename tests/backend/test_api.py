"""
Comprehensive API tests for the AI Product Discovery Assistant.

Tests cover:
- Session management and health checks
- Product search with multiple filter combinations
- Product details with context validation
- Shopping cart operations with inventory validation
- Context validation for AI hallucination prevention
- Product recommendations
"""

import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import from backend
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'starter-code' / 'backend'))

# Set test database URL BEFORE importing database module
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import database  # type: ignore
from main import app
from models import Product, ProductCategory, SQLModel


# ============================================
# TEST FIXTURES
# ============================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def test_db_setup(event_loop):
    """Setup in-memory test database with sample products"""
    # Create in-memory SQLite database
    test_db_url = "sqlite+aiosqlite:///:memory:"
    test_engine = create_async_engine(test_db_url, future=True, echo=False)
    
    # Override database engine
    database.engine = test_engine
    database.AsyncSessionLocal = sessionmaker(
        test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )

    # Create tables
    async with test_engine.begin() as conn:
        # Import all models to register with SQLModel
        from models import Product, SessionContext, SearchContext, CartItem  # noqa: F401
        await conn.run_sync(SQLModel.metadata.create_all)

    # Seed test data
    async with database.AsyncSessionLocal() as session:
        await seed_products(session)

    yield

    # Cleanup
    await test_engine.dispose()


async def seed_products(session: AsyncSession):
    """Seed database with test products"""
    products = [
        Product(
            id="prod_001",
            name="Wireless Bluetooth Headphones",
            description="Premium noise-cancelling wireless headphones",
            price=199.99,
            category=ProductCategory.ELECTRONICS,
            image_url="https://example.com/headphones.jpg",
            in_stock=True,
            stock_quantity=25,
            rating=4.5,
            reviews_count=100,
        ),
        Product(
            id="prod_002",
            name="Smartphone Protective Case",
            description="Ultra-slim protective case",
            price=29.99,
            category=ProductCategory.ELECTRONICS,
            image_url="https://example.com/case.jpg",
            in_stock=True,
            stock_quantity=50,
            rating=4.2,
            reviews_count=50,
        ),
        Product(
            id="prod_003",
            name="Organic Cotton T-Shirt",
            description="100% organic cotton t-shirt",
            price=24.99,
            category=ProductCategory.CLOTHING,
            image_url="https://example.com/tshirt.jpg",
            in_stock=True,
            stock_quantity=100,
            rating=4.0,
            reviews_count=200,
        ),
        Product(
            id="prod_004",
            name="Smart Security Camera",
            description="AI-powered security camera",
            price=149.99,
            category=ProductCategory.ELECTRONICS,
            image_url="https://example.com/camera.jpg",
            in_stock=True,
            stock_quantity=15,
            rating=4.7,
            reviews_count=80,
        ),
        Product(
            id="prod_005",
            name="Ergonomic Office Chair",
            description="Premium ergonomic chair",
            price=299.99,
            category=ProductCategory.HOME,
            image_url="https://example.com/chair.jpg",
            in_stock=True,
            stock_quantity=10,
            rating=4.6,
            reviews_count=45,
        ),
        Product(
            id="prod_006",
            name="Running Shoes",
            description="Lightweight running shoes",
            price=89.99,
            category=ProductCategory.SPORTS,
            image_url="https://example.com/shoes.jpg",
            in_stock=True,
            stock_quantity=30,
            rating=4.3,
            reviews_count=120,
        ),
        Product(
            id="prod_007",
            name="Mystery Novel",
            description="Bestselling mystery novel",
            price=14.99,
            category=ProductCategory.BOOKS,
            image_url="https://example.com/book.jpg",
            in_stock=True,
            stock_quantity=50,
            rating=4.4,
            reviews_count=300,
        ),
    ]
    
    for product in products:
        session.add(product)
    await session.commit()


# ============================================
# SESSION & HEALTH TESTS
# ============================================

@pytest.mark.asyncio
async def test_create_session():
    """Test session creation returns valid session ID"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/sessions", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]


# ============================================
# PRODUCT SEARCH TESTS
# ============================================

@pytest.mark.asyncio
async def test_search_basic():
    """Test basic product search by keyword"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        response = await client.post(
            "/api/functions/search_products",
            json={
                "query": "headphones",
                "limit": 10,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        products = data["data"]["products"]
        assert len(products) > 0
        assert any(p["id"] == "prod_001" for p in products)


@pytest.mark.asyncio
async def test_search_with_category():
    """Test product search filtered by category"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        response = await client.post(
            "/api/functions/search_products",
            json={
                "query": "",
                "category": "ELECTRONICS",
                "limit": 10,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        products = data["data"]["products"]
        
        # All results should be electronics
        for product in products:
            assert product["category"] == "ELECTRONICS"


@pytest.mark.asyncio
async def test_search_with_price_range():
    """Test product search with price filters"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        response = await client.post(
            "/api/functions/search_products",
            json={
                "query": "",
                "price_min": 20.0,
                "price_max": 150.0,
                "limit": 10,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        products = data["data"]["products"]
        
        # All results should be within price range
        for product in products:
            assert 20.0 <= product["price"] <= 150.0


@pytest.mark.asyncio
async def test_search_multiple_filters():
    """Test product search with multiple filters combined"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        response = await client.post(
            "/api/functions/search_products",
            json={
                "query": "",
                "category": "ELECTRONICS",
                "price_min": 25.0,
                "price_max": 200.0,
                "limit": 10,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        products = data["data"]["products"]
        
        # Verify all filters applied
        for product in products:
            assert product["category"] == "ELECTRONICS"
            assert 25.0 <= product["price"] <= 200.0


# ============================================
# PRODUCT DETAILS TESTS
# ============================================

@pytest.mark.asyncio
async def test_show_product_details():
    """Test retrieving detailed product information"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        # Search first to establish context
        await client.post(
            "/api/functions/search_products",
            json={
                "query": "headphones",
                "limit": 10,
                "session_id": session_id,
            },
        )

        # Get product details
        response = await client.post(
            "/api/functions/show_product_details",
            json={
                "product_id": "prod_001",
                "include_recommendations": True,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["product"]["id"] == "prod_001"
        assert data["validation"]["product_exists"] is True


@pytest.mark.asyncio
async def test_product_details_with_recommendations():
    """Test product details includes recommendations"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        # Search and get details
        await client.post(
            "/api/functions/search_products",
            json={"query": "camera", "limit": 10, "session_id": session_id},
        )

        response = await client.post(
            "/api/functions/show_product_details",
            json={
                "product_id": "prod_004",
                "include_recommendations": True,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data["data"]
        recommendations = data["data"]["recommendations"]
        assert isinstance(recommendations, list)


# ============================================
# SHOPPING CART TESTS
# ============================================

@pytest.mark.asyncio
async def test_add_to_cart():
    """Test adding product to shopping cart"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        # Search to establish context
        await client.post(
            "/api/functions/search_products",
            json={"query": "case", "limit": 10, "session_id": session_id},
        )

        # Add to cart
        response = await client.post(
            "/api/functions/add_to_cart",
            json={
                "product_id": "prod_002",
                "quantity": 2,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["cart_item"]["product_id"] == "prod_002"
        assert data["data"]["cart_item"]["quantity"] == 2


@pytest.mark.asyncio
async def test_add_to_cart_validates_stock():
    """Test cart validates sufficient stock availability"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        # Search first
        await client.post(
            "/api/functions/search_products",
            json={"query": "chair", "limit": 10, "session_id": session_id},
        )

        # Try to add more than available stock
        response = await client.post(
            "/api/functions/add_to_cart",
            json={
                "product_id": "prod_005",
                "quantity": 1000,  # prod_005 has stock_quantity=10
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["validation"]["sufficient_stock"] is False


@pytest.mark.asyncio
async def test_add_to_cart_with_sufficient_stock():
    """Test cart accepts reasonable quantities"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        await client.post(
            "/api/functions/search_products",
            json={"query": "case", "limit": 10, "session_id": session_id},
        )

        response = await client.post(
            "/api/functions/add_to_cart",
            json={
                "product_id": "prod_002",
                "quantity": 5,  # prod_002 has stock_quantity=50
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["validation"]["sufficient_stock"] is True


# ============================================
# CONTEXT VALIDATION TESTS
# ============================================

@pytest.mark.asyncio
async def test_context_validation_without_search():
    """Test products not in search context are flagged"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        # Get details WITHOUT searching first
        response = await client.post(
            "/api/functions/show_product_details",
            json={
                "product_id": "prod_001",
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["validation"]["product_exists"] is True
        assert data["validation"]["in_recent_search"] is False


@pytest.mark.asyncio
async def test_context_validation_with_search():
    """Test products in recent search are validated"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        # Search first to establish context
        await client.post(
            "/api/functions/search_products",
            json={"query": "headphones", "limit": 10, "session_id": session_id},
        )

        # Get details (should be in context)
        response = await client.post(
            "/api/functions/show_product_details",
            json={
                "product_id": "prod_001",
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["validation"]["in_recent_search"] is True


# ============================================
# RECOMMENDATIONS TESTS
# ============================================

@pytest.mark.asyncio
async def test_get_recommendations():
    """Test product recommendations by product ID"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        response = await client.post(
            "/api/functions/get_recommendations",
            json={
                "based_on": "prod_001",
                "max_results": 5,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        recommendations = data["data"]["recommendations"]
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0


@pytest.mark.asyncio
async def test_recommendations_same_category():
    """Test recommendations match product category"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        response = await client.post(
            "/api/functions/get_recommendations",
            json={
                "based_on": "prod_001",  # Electronics
                "max_results": 5,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        recommendations = data["data"]["recommendations"]
        
        # All recommendations should be same category
        for rec in recommendations:
            assert rec["category"] == "ELECTRONICS"


@pytest.mark.asyncio
async def test_recommendations_by_category():
    """Test recommendations can be based on category"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        response = await client.post(
            "/api/functions/get_recommendations",
            json={
                "based_on": "BOOKS",
                "max_results": 5,
                "session_id": session_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        recommendations = data["data"]["recommendations"]
        assert isinstance(recommendations, list)


# ============================================
# INTEGRATION TESTS
# ============================================

@pytest.mark.asyncio
async def test_complete_shopping_flow():
    """Test complete user flow: search → details → add to cart"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        # Step 1: Search
        search_res = await client.post(
            "/api/functions/search_products",
            json={
                "query": "headphones",
                "category": "ELECTRONICS",
                "limit": 10,
                "session_id": session_id,
            },
        )
        assert search_res.status_code == 200
        products = search_res.json()["data"]["products"]
        assert len(products) > 0

        # Step 2: View details
        details_res = await client.post(
            "/api/functions/show_product_details",
            json={
                "product_id": "prod_001",
                "include_recommendations": True,
                "session_id": session_id,
            },
        )
        assert details_res.status_code == 200
        assert details_res.json()["validation"]["in_recent_search"] is True

        # Step 3: Add to cart
        cart_res = await client.post(
            "/api/functions/add_to_cart",
            json={
                "product_id": "prod_001",
                "quantity": 1,
                "session_id": session_id,
            },
        )
        assert cart_res.status_code == 200
        assert cart_res.json()["success"] is True


@pytest.mark.asyncio
async def test_multiple_category_search():
    """Test searching across different categories"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/sessions", json={})
        session_id = res.json()["session_id"]

        categories = ["ELECTRONICS", "CLOTHING", "HOME", "BOOKS"]
        
        for category in categories:
            response = await client.post(
                "/api/functions/search_products",
                json={
                    "query": "",
                    "category": category,
                    "limit": 5,
                    "session_id": session_id,
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True