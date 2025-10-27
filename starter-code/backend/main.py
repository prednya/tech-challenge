import os
import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select
from sqlalchemy import delete
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime, timezone

from database import init_db, get_session, session_factory, engine
from models import (
    ChatMessage,
    SSEEvent,
    SessionContext,
    ProductSearchRequest,
    ProductDetailsRequest,
    AddToCartRequest,
    RecommendationsRequest,
    Product,
    ProductCategory,
    CartItem,
)
# Use only the factory; the mock agent will handle plan+run internally
from ai_agent import create_ai_agent
from product_service import ProductService
from context_manager import ContextManager

logger = logging.getLogger("backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
    logger.info("🚀 Starting AI Product Discovery Assistant...")
    await init_db()
    logger.info("✅ Database initialized")

    if os.getenv("SEED_FROM_SQL", "true").lower() == "true":
        try:
            await seed_from_sql_if_empty()
        except Exception as e:
            logger.exception("Seeding from init.sql failed: %s", e)
    yield
    logger.info("🛑 Shutting down...")


app = FastAPI(
    title="AI Product Discovery Assistant",
    description="Real-time AI assistant with function calling and context validation",
    version="1.0.0",
    lifespan=lifespan
)

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Global services
product_service = ProductService()
context_manager = ContextManager()

# Create agent with dependencies so the mock agent can plan+run real tools
ai_agent = create_ai_agent(
    product_service=product_service,
    context_manager=context_manager,
    session_factory=session_factory
)

# Per-session SSE queues
session_message_queues: Dict[str, asyncio.Queue] = {}


@app.get("/health")
async def health_check():
    try:
        SessionLocal = session_factory()
        async with SessionLocal() as db:
            result = await db.execute(select(Product))
            any_product = result.scalars().first() is not None
            db_status = "healthy" if any_product is not None else "empty"
    except Exception as e:
        db_status = f"error: {e}"
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {"database": db_status},
        "version": "1.0.0"
    }


@app.post("/api/sessions")
async def create_session(session: AsyncSession = Depends(get_session)):
    session_id = str(uuid.uuid4())
    context = SessionContext(
        session_id=session_id,
        context_data={"created_at": datetime.now(timezone.utc).isoformat()}
    )
    session.add(context)
    await session.commit()

    session_message_queues[session_id] = asyncio.Queue()

    logger.info("create_session: %s", session_id)
    return {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None
    }


@app.post("/api/chat/{session_id}/message")
async def send_message(
    session_id: str,
    message: ChatMessage,
    session: AsyncSession = Depends(get_session)
):
    # Validate session defensively to avoid transient 500s on message send
    try:
        exists = await context_manager.session_exists(session_id, session)
    except Exception as e:
        logger.exception("send_message: session_exists failed: %s", e)
        # Fallback: if a queue exists, treat session as alive
        exists = session_id in session_message_queues
    if not exists:
        raise HTTPException(status_code=404, detail="Session not found")

    # be tolerant: message or content
    text = (message.message or message.content or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'message' text")

    queue = session_message_queues.setdefault(session_id, asyncio.Queue())
    await queue.put({
        "message": text,
        "context": (message.context or {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    logger.info("send_message: queued message for session %s: %s", session_id, text)
    return {"success": True, "message_id": str(uuid.uuid4()), "session_id": session_id}


@app.get("/api/stream/{session_id}")
async def stream_chat(
    session_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    try:
        exists = await context_manager.session_exists(session_id, session)
    except Exception as e:
        logger.exception("SSE: session_exists check failed: %s", e)
        exists = session_id in session_message_queues
    if not exists:
        raise HTTPException(status_code=404, detail="Session not found")

    def _json_default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, "model_dump"):
            try:
                return obj.model_dump(mode="json")
            except Exception:
                return str(obj)
        return str(obj)

    async def emit(event_type: str, data: Dict[str, Any]):
        event_id = str(uuid.uuid4())
        payload = json.dumps(data, default=_json_default)
        return f"event: {event_type}\ndata: {payload}\nid: {event_id}\n\n"

    async def event_stream():
        try:
            logger.info("SSE: connection opened for session %s", session_id)
            yield await emit("connection", {"status": "connected", "session_id": session_id})

            existing_ctx = await context_manager.get_context(session_id, session)
            already_welcomed = bool(getattr(existing_ctx, "context_data", {}).get("welcome_sent")) if existing_ctx else False

            if not already_welcomed:
                welcome_chunks = [
                    "Hello! I'm your AI shopping assistant. ",
                    "I can help you search for products, ",
                    "get detailed information, and manage your cart. ",
                    "What would you like to find today?",
                ]

                for chunk in welcome_chunks:
                    if await request.is_disconnected():
                        break
                    yield await emit("text_chunk", {"content": chunk, "partial": True})
                    await asyncio.sleep(0.1)

                yield await emit("completion", {"turn_id": str(uuid.uuid4()), "status": "complete"})
                await context_manager.update_context(session_id, {"welcome_sent": True}, session)

            queue = session_message_queues.setdefault(session_id, asyncio.Queue())

            idle_heartbeat = 0
            while not await request.is_disconnected():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                    idle_heartbeat = 0
                except asyncio.TimeoutError:
                    idle_heartbeat += 1
                    if idle_heartbeat % 1 == 0:
                        yield await emit("ping", {"ts": datetime.now(timezone.utc).isoformat()})
                    continue

                user_text = item.get("message", "")
                logger.info("SSE: processing message for session %s: %s", session_id, user_text)

                # 1) PLAN with the AI agent (mock agent will infer the tool)
                try:
                    plan = await ai_agent.execute_function(
                        "__infer__",
                        {"mode": "plan", "text": user_text},
                        session_id=session_id
                    )
                    # plan must be {"function": ..., "parameters": ...}
                    planned_function = (plan or {}).get("function")
                    planned_parameters = (plan or {}).get("parameters") or {}
                except Exception as e:
                    logger.exception("Planning failed: %s", e)
                    planned_function = None
                    planned_parameters = {}

                # Which tools should be silent (no extra bubble)
                silent_functions = {"update_cart", "remove_from_cart", "get_cart"}

                # 2) Stream assistant text first (unless silent)
                if not (planned_function in silent_functions):
                    async for chunk in ai_agent.stream_response(user_text, {}, session_id):
                        if await request.is_disconnected():
                            break
                        yield await emit("text_chunk", {"content": chunk, "partial": True})
                        await asyncio.sleep(0.05)

                # 3) RUN the tool (if we planned one), else fallback: do nothing
                fcall_payload = None
                if planned_function:
                    try:
                        exec_result = await ai_agent.execute_function(
                            planned_function,
                            planned_parameters,
                            session_id=session_id
                        )
                        # exec_result from mock returns {"function": ..., "parameters": ..., "result": {...}}
                        # Normalize just in case
                        if isinstance(exec_result, dict) and "result" in exec_result:
                            fcall_payload = {
                                "function": exec_result.get("function", planned_function),
                                "parameters": exec_result.get("parameters", planned_parameters),
                                "result": exec_result.get("result")
                            }
                        else:
                            # Some error shape fallback
                            fcall_payload = {
                                "function": planned_function,
                                "parameters": planned_parameters,
                                "result": exec_result
                            }
                    except Exception as e:
                        logger.exception("Tool execution failed: %s", e)
                        fcall_payload = {
                            "function": planned_function,
                            "parameters": planned_parameters,
                            "result": {"error": str(e)}
                        }

                    # Emit function_call event
                    yield await emit("function_call", fcall_payload or {
                        "function": planned_function,
                        "parameters": planned_parameters,
                        "result": None
                    })

                # 4) turn completion
                yield await emit("completion", {"turn_id": str(uuid.uuid4()), "status": "complete"})

        except Exception as e:
            logger.exception("SSE error for session %s: %s", session_id, e)
            yield await emit("error", {"error": str(e), "session_id": session_id})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@app.get("/api/sessions/{session_id}/context")
async def get_session_context(
    session_id: str,
    session: AsyncSession = Depends(get_session)
):
    context = await context_manager.get_context(session_id, session)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "context": context.context_data,
        "last_updated": context.updated_at.isoformat()
    }


async def seed_from_sql_if_empty(sql_path: str = "/app/init.sql"):
    SessionLocal = session_factory()
    async with SessionLocal() as db:
        existing = (await db.execute(select(Product.id).limit(1))).scalars().first()
        if existing:
            logger.info("Seed SQL: products already present; skipping init.sql")
            return

    try:
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_text = f.read()
    except Exception as e:
        logger.warning("Seed SQL: init.sql not found at %s (%s)", sql_path, e)
        return

    stmts = [s.strip() for s in sql_text.split(';') if s.strip()]
    async with engine.begin() as conn:
        for s in stmts:
            await conn.exec_driver_sql(s)
    logger.info("Seed SQL: executed %d statements from init.sql", len(stmts))

# Function Endpoints

@app.post("/api/functions/search_products")
async def api_search_products(req: ProductSearchRequest, session: AsyncSession = Depends(get_session)):
    products = await product_service.search_products(
        query=req.query,
        category=req.category,
        limit=req.limit,
        session=session,
        price_min=req.price_min,
        price_max=req.price_max,
    )
    await context_manager.track_search_results(
        session_id=req.session_id,
        query=req.query,
        results=[p.id for p in products],
        category=req.category,
        session_db=session,
    )
    return {
        "success": True,
        "data": {
            "products": [p.model_dump(mode="json") for p in products],
            "total_results": len(products),
            "search_context": {"query": req.query, "category": req.category},
        },
        "context_updated": True,
    }


@app.post("/api/functions/show_product_details")
async def api_show_product_details(req: ProductDetailsRequest, session: AsyncSession = Depends(get_session)):
    validation = await context_manager.validate_product_id(req.session_id, req.product_id, session)
    product = await product_service.get_product_by_id(req.product_id, session=session)
    recs = []
    if req.include_recommendations and product:
        recs = await product_service.get_recommendations(
            based_on_product_id=product.id, limit=5, session=session
        )
    return {
        "success": True,
        "data": {
            "product": product.model_dump(mode="json") if product else None,
            "recommendations": [r.model_dump(mode="json") for r in recs],
        },
        "validation": {
            "product_exists": product is not None,
            "in_recent_search": validation.get("valid", False),
            "context_valid": validation.get("valid", False),
        },
    }


@app.post("/api/functions/add_to_cart")
async def api_add_to_cart(req: AddToCartRequest, session: AsyncSession = Depends(get_session)):
    validation = await context_manager.validate_product_id(req.session_id, req.product_id, session)
    if not validation.get("valid", False):
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_PRODUCT_ID",
            "message": f"Product ID '{req.product_id}' not found in recent searches",
            "suggestions": validation.get("suggestions", []),
        })

    product = await product_service.get_product_by_id(req.product_id, session=session)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    qty = max(1, req.quantity)
    in_stock = product.in_stock and product.stock_quantity >= qty

    cart_item = CartItem(
        session_id=req.session_id,
        product_id=product.id,
        quantity=qty,
        unit_price=product.price,
        total_price=product.price * qty,
    )
    session.add(cart_item)
    await session.commit()
    await session.refresh(cart_item)

    items = (await session.execute(select(CartItem).where(CartItem.session_id == req.session_id))).scalars().all()
    total_items = sum(i.quantity for i in items)
    subtotal = sum(i.total_price for i in items)
    item = {
        "id": cart_item.id,
        "product_id": cart_item.product_id,
        "product_name": product.name,
        "quantity": cart_item.quantity,
        "unit_price": cart_item.unit_price,
        "total_price": cart_item.total_price,
        "added_at": cart_item.added_at.isoformat(),
    }
    summary = {
        "total_items": total_items,
        "total_products": len(items),
        "subtotal": subtotal,
        "estimated_tax": round(subtotal * 0.1, 2),
        "estimated_total": round(subtotal * 1.1, 2),
    }
    return {
        "success": True,
        "data": {"cart_item": item, "cart_summary": summary},
        "validation": {
            "product_exists": True,
            "sufficient_stock": in_stock,
            "valid_quantity": qty > 0,
        },
    }


@app.post("/api/functions/get_recommendations")
async def api_get_recommendations(req: RecommendationsRequest, session: AsyncSession = Depends(get_session)):
    base = req.based_on.strip()
    limit = req.max_results
    context = {"algorithm": "similar_by_category"}

    if base.lower().startswith("prod_"):
        recs = await product_service.get_recommendations(
            based_on_product_id=base, limit=limit, session=session
        )
        context["based_on_product_id"] = base
    else:
        cat_upper = base.upper()
        if cat_upper in [c.name for c in ProductCategory]:
            recs = await product_service.get_recommendations_by_category(
                category=ProductCategory[cat_upper], limit=limit, session=session
            )
            context["based_on_category"] = cat_upper
        else:
            found = await product_service.search_products(query=base, category=None, limit=1, session=session)
            if found:
                pid = found[0].id
                recs = await product_service.get_recommendations(
                    based_on_product_id=pid, limit=limit, session=session
                )
                context["based_on_product_id"] = pid
            else:
                recs = []

    return {
        "success": True,
        "data": {
            "recommendations": [r.model_dump(mode="json") for r in recs],
            "recommendation_context": context,
        },
    }


@app.post("/api/functions/get_cart")
async def api_get_cart(session_id: str, session: AsyncSession = Depends(get_session)):
    items = (await session.execute(select(CartItem).where(CartItem.session_id == session_id))).scalars().all()
    output_items = []
    for it in items:
        prod = await product_service.get_product_by_id(it.product_id, session=session)
        output_items.append({
            "id": it.id,
            "product_id": it.product_id,
            "product_name": prod.name if prod else it.product_id,
            "quantity": it.quantity,
            "unit_price": it.unit_price,
            "total_price": it.total_price,
            "added_at": it.added_at.isoformat(),
        })
    total_items = sum(i["quantity"] for i in output_items)
    subtotal = sum(i["total_price"] for i in output_items)
    return {
        "success": True,
        "data": {
            "items": output_items,
            "cart_summary": {
                "total_items": total_items,
                "total_products": len(output_items),
                "subtotal": subtotal,
                "estimated_tax": round(subtotal * 0.1, 2),
                "estimated_total": round(subtotal * 1.1, 2),
            },
        },
    }


@app.post("/api/functions/remove_from_cart")
async def api_remove_from_cart(body: dict, session: AsyncSession = Depends(get_session)):
    session_id = body.get("session_id")
    product_id = body.get("product_id")
    item_id = body.get("item_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # Prefer removal by item_id without context validation so users can always
    # remove items (including those added from recommendations).
    if item_id is not None:
        await session.execute(
            delete(CartItem).where(CartItem.session_id == session_id, CartItem.id == item_id)
        )
        await session.commit()
    elif product_id:
        # Only validate when removing by product_id (not when removing by item_id)
        validation = await context_manager.validate_product_id(session_id, product_id, session)
        if not validation.get("valid", False):
            raise HTTPException(status_code=400, detail={
                "code": "INVALID_PRODUCT_ID",
                "message": f"Product ID '{product_id}' not found in recent searches",
                "suggestions": validation.get("suggestions", []),
            })
        await session.execute(
            delete(CartItem).where(CartItem.session_id == session_id, CartItem.product_id == product_id)
        )
        await session.commit()

    items = (await session.execute(select(CartItem).where(CartItem.session_id == session_id))).scalars().all()
    output_items = []
    for it in items:
        prod = await product_service.get_product_by_id(it.product_id, session=session)
        output_items.append({
            "id": it.id,
            "product_id": it.product_id,
            "product_name": prod.name if prod else it.product_id,
            "quantity": it.quantity,
            "unit_price": it.unit_price,
            "total_price": it.total_price,
            "added_at": it.added_at.isoformat(),
        })
    total_items = sum(i["quantity"] for i in output_items)
    subtotal = sum(i["total_price"] for i in output_items)
    return {
        "success": True,
        "data": {
            "items": output_items,
            "cart_summary": {
                "total_items": total_items,
                "total_products": len(output_items),
                "subtotal": subtotal,
                "estimated_tax": round(subtotal * 0.1, 2),
                "estimated_total": round(subtotal * 1.1, 2),
            },
        },
    }


@app.post("/api/functions/update_cart")
async def api_update_cart(body: dict, session: AsyncSession = Depends(get_session)):
    session_id = body.get("session_id")
    product_id = body.get("product_id")
    delta = int(body.get("delta", 0))
    if not session_id or not product_id or delta == 0:
        raise HTTPException(status_code=400, detail="session_id, product_id and non-zero delta are required")

    res = await session.execute(select(CartItem).where(CartItem.session_id == session_id, CartItem.product_id == product_id))
    item = res.scalar_one_or_none()
    prod = await product_service.get_product_by_id(product_id, session=session)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    # Relax validation for updates of existing items so users can adjust quantities
    # of items added from recommendations (which might not be in recent search context).
    if item is None and delta > 0:
        # Only when creating a new cart row do we enforce recent-search validation
        validation = await context_manager.validate_product_id(session_id, product_id, session)
        if not validation.get("valid", False):
            raise HTTPException(status_code=400, detail={
                "code": "INVALID_PRODUCT_ID",
                "message": f"Product ID '{product_id}' not found in recent searches",
                "suggestions": validation.get("suggestions", []),
            })
        item = CartItem(session_id=session_id, product_id=product_id, quantity=delta, unit_price=prod.price, total_price=prod.price * delta)
        session.add(item)
        await session.commit()
    elif item is not None:
        new_qty = item.quantity + delta
        if new_qty <= 0:
            await session.execute(delete(CartItem).where(CartItem.id == item.id))
            await session.commit()
        else:
            item.quantity = new_qty
            item.total_price = item.unit_price * new_qty
            session.add(item)
            await session.commit()

    items = (await session.execute(select(CartItem).where(CartItem.session_id == session_id))).scalars().all()
    output_items = []
    for it in items:
        prod = await product_service.get_product_by_id(it.product_id, session=session)
        output_items.append({
            "id": it.id,
            "product_id": it.product_id,
            "product_name": prod.name if prod else it.product_id,
            "quantity": it.quantity,
            "unit_price": it.unit_price,
            "total_price": it.total_price,
            "added_at": it.added_at.isoformat(),
        })
    total_items = sum(i["quantity"] for i in output_items)
    subtotal = sum(i["total_price"] for i in output_items)
    return {
        "success": True,
        "data": {
            "items": output_items,
            "cart_summary": {
                "total_items": total_items,
                "total_products": len(output_items),
                "subtotal": subtotal,
                "estimated_tax": round(subtotal * 0.1, 2),
                "estimated_total": round(subtotal * 1.1, 2),
            },
        },
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )

# Optional global rate limiting
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.errors import RateLimitExceeded
    from fastapi.responses import PlainTextResponse

    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
    if not hasattr(app.state, "limiter"):
        app.state.limiter = limiter
        app.add_middleware(SlowAPIMiddleware)

        @app.exception_handler(RateLimitExceeded)
        async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
            return PlainTextResponse("Rate limit exceeded", status_code=429)
except Exception:
    pass
