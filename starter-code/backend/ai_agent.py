"""
AI Agent implementation for the Product Discovery Assistant.

This module provides both real AI integration (OpenAI/Anthropic) and mock
implementations for development and testing.
"""

import os
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Optional

import httpx

# Base Agent Interface

class AIAgent(ABC):
    """Abstract base class for AI agents."""

    @abstractmethod
    async def stream_response(
        self,
        message: str,
        context: Dict[str, Any],
        session_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream AI response chunks."""
        pass

    @abstractmethod
    async def execute_function(
        self,
        function_name: Optional[str],
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Execute a function call.

        Implementations may support a planning mode where function_name is None
        (or "__infer__") and the agent decides which tool to call based on text.
        """
        pass

# OpenAI Agent (placeholder)

class OpenAIAgent(AIAgent):
    """OpenAI-based AI agent implementation."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("AI_MODEL", "gpt-3.5-turbo")
        self.base_url = "https://api.openai.com/v1"

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")

    async def stream_response(
        self,
        message: str,
        context: Dict[str, Any],
        session_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI (placeholder)."""

        # TODO: Implement OpenAI streaming with function calling.
        # This is a placeholder - implement actual OpenAI integration.
        _ = (self.base_url, context)  # silence unused for now
        async with httpx.AsyncClient():
            response_text = "I'm a placeholder OpenAI response. Please implement actual OpenAI integration."
            for word in response_text.split():
                yield word + " "
                await asyncio.sleep(0.1)

    async def execute_function(
        self,
        function_name: Optional[str],
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Execute function call (placeholder)."""
        _ = (parameters, session_id)
        return {"status": "not_implemented", "function": function_name}

    def _get_function_definitions(self) -> list:
        """Get OpenAI function definitions."""
        return [
            {
                "name": "search_products",
                "description": "Search for products based on user query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "category": {"type": "string"},
                        "limit": {"type": "integer"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "show_product_details",
                "description": "Show detailed information about a product",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "include_recommendations": {"type": "boolean"}
                    },
                    "required": ["product_id"]
                }
            }
        ]

    def _get_system_prompt(self) -> str:
        """Get system prompt for the AI agent."""
        return """
        You are a helpful AI shopping assistant. You can help users:
        - Search for products
        - Get detailed product information
        - Add items to their cart
        - Get product recommendations

        Always use function calls when appropriate and be helpful and friendly.
        """

# Mock Agent (plan + run real tools)

class MockAIAgent(AIAgent):
    """
    Mock AI agent for development/testing.

    - Streams friendly "AI-like" text via stream_response
    - Can PLAN which tool to run from free text (if function_name is None/"__infer__")
    - RUNS the chosen tool against the REAL DB via ProductService/ContextManager
    """

    def __init__(self, *, product_service, context_manager, session_factory):
        self.product_service = product_service
        self.context_manager = context_manager
        self.session_factory = session_factory

        # Small, friendly canned text chunks to simulate AI streaming
        self.responses = {
            "search": [
                "I'll help you search for products! Let me look that up for you.",
                " I found some great options that match your query.",
                " Here are the search results I found."
            ],
            "details": [
                "Let me get the detailed information for that product.",
                " Here are all the details and specifications you requested.",
                " I've also included some related recommendations you might like."
            ],
            "cart": [
                "Great choice! I'll add that item to your cart.",
                " The item has been successfully added.",
                " Your cart has been updated with the new item."
            ],
            "recommendations": [
                "Based on your interests, I have some great recommendations!",
                " These products are similar to what you're looking for.",
                " You might also be interested in these related items."
            ]
        }

    # Streaming text

    async def stream_response(
        self,
        message: str,
        context: Dict[str, Any],
        session_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream mock AI response text chunks."""
        _ = (context, session_id)

        # naive type classification for nicer-feeling text
        response_type = "search"  # default
        m = message.lower()
        if "detail" in m:
            response_type = "details"
        elif "cart" in m or "add" in m:
            response_type = "cart"
        elif "recommend" in m:
            response_type = "recommendations"

        for chunk in self.responses.get(response_type, self.responses["search"]):
            yield chunk
            await asyncio.sleep(0.2)  # simulate delay

    # Execute function

    async def execute_function(
        self,
        function_name: Optional[str],
        parameters: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        PLAN/RUN execution.

        Modes:
          - PLAN:  parameters["mode"] == "plan" and function_name is None/"__infer__".
                   Returns {"function": ..., "parameters": ...}
          - RUN:   parameters["mode"] == "run" (default).
                   Executes the chosen tool against the real DB and returns:
                   {"function": ..., "parameters": ..., "result": {...}}
        """
        mode = parameters.get("mode") or "run"

        # PLAN: if asked, or if function_name is not provided
        if function_name in (None, "__infer__", "infer"):
            text = parameters.get("text", "") or ""
            plan = self._infer_function_call_from_text(text)
            if not plan:
                plan = {"function": "search_products",
                        "parameters": {"query": text, "limit": 10}}
            if mode == "plan":
                return plan
            # RUN the planned tool
            return await self._run_tool(plan["function"], plan["parameters"], session_id)

        # If a tool name was provided explicitly:
        if mode == "plan":
            return {"function": function_name, "parameters": parameters}
        return await self._run_tool(function_name, parameters, session_id)


    def _infer_function_call_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        import re

        def extract_product_id(txt: str) -> Optional[str]:
            for token in txt.replace("\n", " ").split():
                if token.lower().startswith("prod_"):
                    return token
            return None

        def parse_search_text(t: str) -> Dict[str, Any]:
            t0 = t.lower()
            price_min = None
            price_max = None
            m_between = re.search(r"between\s*\$?(\d+\.?\d*)\s*(?:and|-)\s*\$?(\d+\.?\d*)", t0)
            if m_between:
                price_min = float(m_between.group(1))
                price_max = float(m_between.group(2))
                t0 = t0.replace(m_between.group(0), " ")
            m_under = re.search(r"(under|below|less than)\s*\$?(\d+\.?\d*)", t0)
            if m_under and price_max is None:
                price_max = float(m_under.group(2))
                t0 = t0.replace(m_under.group(0), " ")
            m_over = re.search(r"(over|above|more than|greater than)\s*\$?(\d+\.?\d*)", t0)
            if m_over and price_min is None:
                price_min = float(m_over.group(2))
                t0 = t0.replace(m_over.group(0), " ")
            category = None
            for cat in ["electronics", "clothing", "home", "books", "sports", "beauty", "other"]:
                if re.search(rf"\b{cat}\b", t0):
                    category = cat.upper()
                    t0 = re.sub(rf"\b{cat}\b", " ", t0)
            # Drop common filler words that don't convey product meaning
            STOPWORDS = {"show", "me", "find", "please", "the", "for"}
            tokens = [tok for tok in re.findall(r"[a-z0-9]+", t0) if tok and tok not in STOPWORDS]
            cleaned_query = re.sub(r"\s+", " ", " ".join(tokens)).strip()
            return {"query": cleaned_query, "price_min": price_min, "price_max": price_max, "category": category}

        lower = text.lower()
        if "search" in lower:
            q = text.lower().split("search", 1)[1].strip() if "search" in lower else text
            parsed = parse_search_text(q)
            return {"function": "search_products",
                    "parameters": {"query": parsed["query"] or text, "limit": 10,
                                   "price_min": parsed["price_min"], "price_max": parsed["price_max"],
                                   "category": parsed.get("category")}}
        if "detail" in lower:
            pid = extract_product_id(text)
            q = None
            for marker in ["details of", "detail of", "details for", "detail for", "details", "detail"]:
                if marker in lower:
                    q = lower.split(marker, 1)[1].strip()
                    break
            params: Dict[str, Any] = {"include_recommendations": True}
            if pid:
                params["product_id"] = pid
            elif q:
                params["query"] = q
            return {"function": "show_product_details", "parameters": params}
        if "add" in lower and ("cart" in lower or "to cart" in lower):
            pid = extract_product_id(text) or "prod_001"
            return {"function": "add_to_cart", "parameters": {"product_id": pid, "quantity": 1}}
        if "recommend" in lower:
            pid = extract_product_id(text) or "prod_001"
            return {"function": "get_recommendations", "parameters": {"based_on": pid, "max_results": 5}}
        if any(k in lower for k in ["show cart", "list cart", "show all items in cart", "items in cart", "view cart", "my cart"]) or lower.strip() == "cart":
            return {"function": "get_cart", "parameters": {}}
        if ("remove from cart" in lower) or ("delete from cart" in lower) or lower.startswith("remove ") or lower.startswith("delete "):
            pid = extract_product_id(text)
            q = None
            if not pid:
                parts = lower.split()
                if len(parts) >= 2:
                    q = parts[-1]
            params: Dict[str, Any] = {}
            if pid:
                params["product_id"] = pid
            elif q:
                params["query"] = q
            return {"function": "remove_from_cart", "parameters": params}
        if "update cart" in lower:
            tokens = lower.replace("+", " +").replace("-", " -").split()
            pid = extract_product_id(text)
            delta = None
            for t in tokens:
                if t.startswith("+") or t.startswith("-"):
                    try:
                        delta = int(t)
                        break
                    except Exception:
                        pass
            params: Dict[str, Any] = {}
            if pid:
                params["product_id"] = pid
            if delta is not None:
                params["delta"] = delta
            return {"function": "update_cart", "parameters": params}
        if text.strip():
            parsed = parse_search_text(text)
            return {"function": "search_products",
                    "parameters": {"query": parsed["query"], "limit": 10,
                                   "price_min": parsed["price_min"], "price_max": parsed["price_max"],
                                   "category": parsed.get("category")}}
        return None

    async def _run_tool(self, name: str, params: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Executes the chosen tool using the real DB via ProductService."""
        from sqlmodel import select
        from sqlalchemy import delete
        from models import CartItem, ProductCategory

        SessionLocal = self.session_factory()
        async with SessionLocal() as db:
            # search_products
            if name == "search_products":
                products = await self.product_service.search_products(
                    query=params.get("query", ""),
                    category=params.get("category"),
                    limit=params.get("limit", 10),
                    session=db,
                    price_min=params.get("price_min"),
                    price_max=params.get("price_max"),
                )
                await self.context_manager.track_search_results(
                    session_id=session_id,
                    query=params.get("query", ""),
                    results=[p.id for p in products],
                    category=params.get("category"),
                    session_db=db,
                )
                return {"function": name, "parameters": params, "result": {
                    "products": [p.model_dump(mode="json") for p in products],
                    "total_results": len(products),
                    "search_context": {"query": params.get("query", ""), "category": params.get("category")},
                }}

            # show_product_details (supports product_id or free-text)
            if name == "show_product_details":
                prod_id = params.get("product_id")
                q = params.get("query")
                if not prod_id and q:
                    candidates = await self.product_service.search_products(query=q, category=None, limit=5, session=db)
                    if not candidates:
                        return {"function": "search_products", "parameters": {"query": q, "limit": 5},
                                "result": {"products": [], "total_results": 0,
                                           "search_context": {"query": q, "category": None}}}
                    if len(candidates) == 1:
                        prod_id = candidates[0].id
                    else:
                        return {"function": "search_products", "parameters": {"query": q, "limit": 5},
                                "result": {"products": [p.model_dump(mode="json") for p in candidates],
                                           "total_results": len(candidates),
                                           "search_context": {"query": q, "category": None}}}
                if prod_id:
                    validation = await self.context_manager.validate_product_id(session_id=session_id, product_id=prod_id, session=db)
                    product = await self.product_service.get_product_by_id(prod_id, session=db)
                    recs = await self.product_service.get_recommendations(based_on_product_id=prod_id, limit=4, session=db)
                    # Allow viewing details for known products even if not in recent search context.
                    # Keep context signal for UI but do not block rendering.
                    validation_out = dict(validation or {})
                    validation_out["in_recent_search"] = bool(validation_out.get("valid", False))
                    validation_out["context_valid"] = bool(validation_out.get("valid", False))
                    validation_out["product_exists"] = bool(product)
                    validation_out["valid"] = bool(product)
                    return {"function": name, "parameters": params, "result": {
                        "product": product.model_dump(mode="json") if product else None,
                        "recommendations": [r.model_dump(mode="json") for r in recs],
                        "validation": validation_out,
                    }}

            # get_recommendations
            if name == "get_recommendations":
                base = (params.get("based_on") or "").strip()
                limit = params.get("max_results", 5)
                recs = []
                ctx = {"algorithm": "similar_by_category"}

                if base.lower().startswith("prod_"):
                    recs = await self.product_service.get_recommendations(based_on_product_id=base, limit=limit, session=db)
                    ctx["based_on_product_id"] = base
                else:
                    cat_upper = base.upper()
                    if cat_upper in [c.name for c in ProductCategory]:
                        recs = await self.product_service.get_recommendations_by_category(ProductCategory[cat_upper], limit=limit, session=db)
                        ctx["based_on_category"] = cat_upper
                    else:
                        found = await self.product_service.search_products(query=base, category=None, limit=1, session=db)
                        if not found and base.endswith("s"):
                            found = await self.product_service.search_products(query=base[:-1], category=None, limit=1, session=db)
                        if found:
                            pid = found[0].id
                            recs = await self.product_service.get_recommendations(based_on_product_id=pid, limit=limit, session=db)
                            ctx["based_on_product_id"] = pid
                return {"function": name, "parameters": params, "result": {
                    "recommendations": [r.model_dump(mode="json") for r in recs],
                    "recommendation_context": ctx,
                }}

            # cart tools
            if name == "get_cart":
                items = (await db.execute(select(CartItem).where(CartItem.session_id == session_id))).scalars().all()
                out = []
                for it in items:
                    prod = await self.product_service.get_product_by_id(it.product_id, session=db)
                    out.append({
                        "id": it.id, "product_id": it.product_id,
                        "product_name": prod.name if prod else it.product_id,
                        "quantity": it.quantity, "unit_price": it.unit_price,
                        "total_price": it.total_price, "added_at": it.added_at.isoformat(),
                    })
                total_items = sum(i["quantity"] for i in out)
                subtotal = sum(i["total_price"] for i in out)
                return {"function": name, "parameters": params, "result": {
                    "items": out,
                    "cart_summary": {
                        "total_items": total_items,
                        "total_products": len(out),
                        "subtotal": subtotal,
                        "estimated_tax": round(subtotal * 0.1, 2),
                        "estimated_total": round(subtotal * 1.1, 2),
                    },
                }}

            if name == "remove_from_cart":
                from sqlalchemy import delete as _delete
                prod_id = params.get("product_id")
                if not prod_id and params.get("query"):
                    candidates = await self.product_service.search_products(params["query"], None, 1, db)
                    if candidates:
                        prod_id = candidates[0].id
                if prod_id:
                    await db.execute(_delete(CartItem).where(CartItem.session_id == session_id, CartItem.product_id == prod_id))
                    await db.commit()
                return await self._run_tool("get_cart", {}, session_id)

            if name == "update_cart":
                from sqlmodel import select as _select
                pid = params.get("product_id")
                delta = int(params.get("delta", 0))
                if pid and delta != 0:
                    res = await db.execute(_select(CartItem).where(CartItem.session_id == session_id, CartItem.product_id == pid))
                    item = res.scalar_one_or_none()
                    prod = await self.product_service.get_product_by_id(pid, session=db)
                    if prod:
                        if item is None and delta > 0:
                            item = CartItem(session_id=session_id, product_id=pid, quantity=delta, unit_price=prod.price, total_price=prod.price * delta)
                            db.add(item)
                            await db.commit()
                        elif item is not None:
                            new_qty = item.quantity + delta
                            if new_qty <= 0:
                                await db.execute(delete(CartItem).where(CartItem.id == item.id))
                                await db.commit()
                            else:
                                item.quantity = new_qty
                                item.total_price = item.unit_price * new_qty
                                db.add(item)
                                await db.commit()
                return await self._run_tool("get_cart", {}, session_id)

            if name == "add_to_cart":
                pid = params.get("product_id", "")
                qty = max(1, int(params.get("quantity", 1)))
                product = await self.product_service.get_product_by_id(pid, session=db)
                if not product:
                    return {"function": name, "parameters": params, "result": {"error": "Product not found", "parameters": params}}
                item = CartItem(session_id=session_id, product_id=product.id, quantity=qty, unit_price=product.price, total_price=product.price * qty)
                db.add(item)
                await db.commit()
                await db.refresh(item)
                return await self._run_tool("get_cart", {}, session_id)

            return {"function": name, "parameters": params, "result": {"error": "Unknown function"}}


def create_ai_agent(
    *,
    product_service=None,
    context_manager=None,
    session_factory=None
) -> AIAgent:
    """
    Create AI agent based on configuration.

    For the mock agent that actually runs your DB tools, pass:
      - product_service: ProductService instance
      - context_manager: ContextManager instance
      - session_factory: sessionmaker from your DB module

    In main.py:
        ai_agent = create_ai_agent(
            product_service=product_service,
            context_manager=context_manager,
            session_factory=session_factory
        )
    """
    provider = os.getenv("AI_PROVIDER", "simulate").lower()

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        return OpenAIAgent()
    elif provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        # TODO: Implement AnthropicAgent
        raise NotImplementedError("Anthropic agent not yet implemented")
    else:
        # default to mock that plans + runs real tools
        return MockAIAgent(
            product_service=product_service,
            context_manager=context_manager,
            session_factory=session_factory
        )


# (Optional) Standalone heuristics if you need them elsewhere


import re

def parse_search_text(text: str) -> Dict[str, Any]:
    """Parse free text for price filters and possible category tokens.

    Extracts price_min/price_max from phrases like:
    - under/below/less than $X
    - over/above/more than $X
    - between X and Y
    Also returns the cleaned residual query.
    """
    t = text.lower()
    price_min = None
    price_max = None
    # between X and Y
    m_between = re.search(r"between\s*\$?(\d+\.?\d*)\s*(?:and|-)\s*\$?(\d+\.?\d*)", t)
    if m_between:
        price_min = float(m_between.group(1))
        price_max = float(m_between.group(2))
        t = t.replace(m_between.group(0), " ")
    m_under = re.search(r"(under|below|less than)\s*\$?(\d+\.?\d*)", t)
    if m_under and price_max is None:
        price_max = float(m_under.group(2))
        t = t.replace(m_under.group(0), " ")
    m_over = re.search(r"(over|above|more than|greater than)\s*\$?(\d+\.?\d*)", t)
    if m_over and price_min is None:
        price_min = float(m_over.group(2))
        t = t.replace(m_over.group(0), " ")
    # Detect category tokens and strip them from the query
    category = None
    categories = [
        "electronics", "clothing", "home", "books", "sports", "beauty", "other",
    ]
    for cat in categories:
        if re.search(rf"\b{cat}\b", t):
            category = cat.upper()
            t = re.sub(rf"\b{cat}\b", " ", t)
    # Remove common filler words to improve matching
    STOPWORDS = {"show", "me", "find", "please", "the", "for"}
    tokens = [tok for tok in re.findall(r"[a-z0-9]+", t) if tok and tok not in STOPWORDS]
    cleaned_query = re.sub(r"\s+", " ", " ".join(tokens)).strip()
    return {"query": cleaned_query, "price_min": price_min, "price_max": price_max, "category": category}

def infer_function_call_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Heuristic inference of the next tool to call from a user message.

    This mirrors the server behavior so we can optionally centralize logic
    inside the ai_agent module.
    """
    def extract_product_id(txt: str) -> Optional[str]:
        for token in txt.replace("\n", " ").split():
            if token.lower().startswith("prod_"):
                return token
        return None

    lower = text.lower()
    if "search" in lower:
        try:
            q = text.lower().split("search", 1)[1].strip()
        except Exception:
            q = text
        parsed = parse_search_text(q)
        return {"name": "search_products", "parameters": {"query": parsed["query"] or text, "limit": 10, "price_min": parsed["price_min"], "price_max": parsed["price_max"], "category": parsed.get("category")}}
    if "detail" in lower:
        pid = extract_product_id(text)
        q = None
        for marker in ["details of", "detail of", "details for", "detail for", "details", "detail"]:
            if marker in lower:
                q = lower.split(marker, 1)[1].strip()
                break
        params: Dict[str, Any] = {"include_recommendations": True}
        if pid:
            params["product_id"] = pid
        elif q:
            params["query"] = q
        return {"name": "show_product_details", "parameters": params}
    if "add" in lower and ("cart" in lower or "to cart" in lower):
        pid = extract_product_id(text) or "prod_001"
        return {"name": "add_to_cart", "parameters": {"product_id": pid, "quantity": 1}}
    if "recommend" in lower:
        pid = extract_product_id(text) or "prod_001"
        return {"name": "get_recommendations", "parameters": {"based_on": pid, "max_results": 5}}
    if ("show cart" in lower) or ("list cart" in lower) or ("show all items in cart" in lower) or ("items in cart" in lower) or (lower.strip() == "cart") or ("view cart" in lower) or ("my cart" in lower):
        return {"name": "get_cart", "parameters": {}}
    if ("remove from cart" in lower) or ("delete from cart" in lower) or lower.startswith("remove ") or lower.startswith("delete "):
        pid = extract_product_id(text)
        q = None
        if not pid:
            parts = lower.split()
            if len(parts) >= 2:
                q = parts[-1]
        params: Dict[str, Any] = {}
        if pid:
            params["product_id"] = pid
        elif q:
            params["query"] = q
        return {"name": "remove_from_cart", "parameters": params}
    if ("update cart" in lower):
        tokens = lower.replace("+", " +").replace("-", " -").split()
        pid = extract_product_id(text)
        delta = None
        for t in tokens:
            if t.startswith("+") or t.startswith("-"):
                try:
                    delta = int(t)
                    break
                except Exception:
                    pass
        params: Dict[str, Any] = {}
        if pid:
            params["product_id"] = pid
        if delta is not None:
            params["delta"] = delta
        return {"name": "update_cart", "parameters": params}
    # Default: treat as search
    if text.strip():
        parsed = parse_search_text(text)
        return {"name": "search_products", "parameters": {"query": parsed["query"], "limit": 10, "price_min": parsed["price_min"], "price_max": parsed["price_max"], "category": parsed.get("category")}}
    return None
