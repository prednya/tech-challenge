# product_service.py

from typing import List, Optional, Tuple
import re
import difflib
import time
import logging

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy import or_, cast, String, delete

from models import Product, ProductCategory, CartItem

logger = logging.getLogger("product_service")

# ---- Tiny TTL cache (per-process) -------------------------------------------

_CACHE: dict[str, Tuple[float, object]] = {}

def _ck(name: str, **kw) -> str:
    return name + "|" + "|".join(f"{k}={kw[k]}" for k in sorted(kw))

def _cache_get(key: str):
    item = _CACHE.get(key)
    if not item:
        return None
    if item[0] < time.time():
        _CACHE.pop(key, None)
        return None
    return item[1]

def _cache_set(key: str, value: object, ttl: int = 60):
    _CACHE[key] = (time.time() + ttl, value)

# Optional: cache for the small token corpus used by fuzzy correction
_TOKENS_CACHE_KEY = "name_tokens"
def _get_tokens_cached(tokens_builder, ttl: int = 60):
    cached = _cache_get(_TOKENS_CACHE_KEY)
    if cached is not None:
        return cached
    tokens = tokens_builder()
    _cache_set(_TOKENS_CACHE_KEY, tokens, ttl=ttl)
    return tokens

# ---- Service ----------------------------------------------------------------

class ProductService:
    """Service for product operations (DB session required)."""

    async def search_products(
        self,
        query: str,
        *,
        session: AsyncSession,                       # REQUIRED (keyword-only)
        category: Optional[ProductCategory] = None,
        limit: int = 10,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
    ) -> List[Product]:
        """Search products by query and optional filters.

        Best practices:
        - Require a DB session (no mock fallback).
        - Guard price range.
        - Keep light fallbacks (plural→singular, typo fix) if initial search is empty.
        """
        # Guardrails
        if limit <= 0:
            return []
        if price_min is not None and price_max is not None and price_min > price_max:
            price_min, price_max = price_max, price_min

        # Normalize category
        if isinstance(category, str):
            try:
                category = ProductCategory[category.strip().upper()]
            except KeyError:
                category = None

        # Cache key
        cat_str = category.value if isinstance(category, ProductCategory) else (
            category.strip().upper() if isinstance(category, str) and category else None
        )
        ck = _ck(
            "search",
            query=(query or "").strip().lower(),
            category=cat_str,
            limit=limit,
            pmin=price_min,
            pmax=price_max,
        )
        cached = _cache_get(ck)
        if cached is not None:
            return cached  # type: ignore

        # Base statement
        statement = select(Product).where(Product.in_stock)

        # Inline helper to apply filters
        def apply_filters(stmt, qtext: Optional[str]):

            # text filter
            if qtext:
                qlocal = qtext.strip()
                if qlocal:
                    pat = f"%{qlocal}%"
                    stmt = stmt.where(
                        or_(
                            Product.name.ilike(pat),
                            Product.description.ilike(pat),
                        )
                    )

            # price filters
            if price_min is not None:
                stmt = stmt.where(Product.price >= float(price_min))
            if price_max is not None:
                stmt = stmt.where(Product.price <= float(price_max))

            # category filter (works for enum or text columns)
            if category:
                cstr = category.value if isinstance(category, ProductCategory) else str(category).strip().upper()
                stmt = stmt.where(cast(Product.category, String) == cstr)

            return stmt

        # Primary attempt
        stmt = apply_filters(statement, query).limit(limit)
        items = (await session.execute(stmt)).scalars().all()

        # Fallback 1: plural → singular (e.g., "laptops" → "laptop")
        if not items and query:
            q_strip = query.strip().lower()
            if q_strip.endswith("s"):
                singular = q_strip[:-1]
                stmt2 = apply_filters(select(Product).where(Product.in_stock), singular).limit(limit)
                items = (await session.execute(stmt2)).scalars().all()

        # Fallback 2: token-level typo correction using a small name corpus
        if not items and query:
            # Build/Reuse a token set from up to 500 product names (cached briefly)
            async def _build_tokens() -> set[str]:
                names = (await session.execute(select(Product.name).limit(500))).scalars().all()
                toks: set[str] = set()
                for name in names:
                    for tok in re.findall(r"[a-zA-Z0-9]+", (name or "").lower()):
                        if len(tok) >= 4:
                            toks.add(tok)
                return toks

            tokens_cache = _cache_get(_TOKENS_CACHE_KEY)
            if tokens_cache is None:
                tokens_cache = await _build_tokens()
                _cache_set(_TOKENS_CACHE_KEY, tokens_cache, ttl=60)
            corpus_tokens: set[str] = tokens_cache  # type: ignore

            q_tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
            corrected_tokens: List[str] = []
            for t in q_tokens:
                if t in corpus_tokens:
                    corrected_tokens.append(t)
                else:
                    match = difflib.get_close_matches(t, list(corpus_tokens), n=1, cutoff=0.8)
                    corrected_tokens.append(match[0] if match else t)

            corrected = " ".join(corrected_tokens).strip()
            if corrected and corrected != query.lower():
                stmt3 = apply_filters(select(Product).where(Product.in_stock), corrected).limit(limit)
                items = (await session.execute(stmt3)).scalars().all()

        logger.info("search_products -> %d results", len(items))
        _cache_set(ck, items, ttl=60)
        return items

    async def get_product_by_id(
        self,
        product_id: str,
        *,
        session: AsyncSession,                      # REQUIRED (keyword-only)
    ) -> Optional[Product]:
        """Fetch a single product by ID."""
        stmt = select(Product).where(Product.id == product_id)
        item = (await session.execute(stmt)).scalar_one_or_none()
        logger.info("get_product_by_id: %s -> %s", product_id, bool(item))
        return item

    async def get_recommendations(
        self,
        based_on_product_id: str,
        *,
        session: AsyncSession,                      # REQUIRED (keyword-only)
        limit: int = 5,
    ) -> List[Product]:
        """Simple 'similar by category' recommendations (excludes the base)."""
        base_product = await self.get_product_by_id(based_on_product_id, session=session)
        if not base_product:
            return []

        if isinstance(base_product.category, ProductCategory):
            bcat = base_product.category.value
        else:
            bcat = str(base_product.category).strip().upper()

        ck = _ck("recs", based_on=based_on_product_id, limit=limit)
        cached = _cache_get(ck)
        if cached is not None:
            return cached  # type: ignore

        stmt = (
            select(Product)
            .where(
                cast(Product.category, String) == bcat,
                Product.id != base_product.id,
                Product.in_stock,
            )
            .limit(limit)
        )
        items = (await session.execute(stmt)).scalars().all()
        logger.info("get_recommendations based_on=%s -> %d results", based_on_product_id, len(items))
        _cache_set(ck, items, ttl=60)
        return items

    async def get_recommendations_by_category(
        self,
        category: ProductCategory | str,
        *,
        session: AsyncSession,                      # REQUIRED (keyword-only)
        limit: int = 5,
    ) -> List[Product]:
        """Recommended products by category (in stock)."""
        cat_str = category.value if isinstance(category, ProductCategory) else str(category).strip().upper()
        stmt = (
            select(Product)
            .where(cast(Product.category, String) == cat_str, Product.in_stock)
            .limit(limit)
        )
        items = (await session.execute(stmt)).scalars().all()
        logger.info("get_recommendations_by_category category=%s -> %d results", cat_str, len(items))
        return items

    async def list_cart(self, session_id: str, session: AsyncSession) -> dict:
        """Return current cart (items + computed summary)."""
        rows = (await session.execute(select(CartItem).where(CartItem.session_id == session_id))).scalars().all()

        # (Small N+1 here—fine for small carts. For larger carts, batch load Products by IDs.)
        output = []
        for it in rows:
            prod = await self.get_product_by_id(it.product_id, session=session)
            output.append({
                "id": it.id,
                "product_id": it.product_id,
                "product_name": (prod.name if prod else it.product_id),
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "total_price": it.total_price,
                "added_at": it.added_at.isoformat(),
            })

        total_items = sum(i["quantity"] for i in output)
        subtotal = sum(i["total_price"] for i in output)
        return {
            "items": output,
            "cart_summary": {
                "total_items": total_items,
                "total_products": len(output),
                "subtotal": subtotal,
                "estimated_tax": round(subtotal * 0.1, 2) if subtotal else 0.0,
                "estimated_total": round(subtotal * 1.1, 2) if subtotal else 0.0,
            },
        }

    async def remove_from_cart(
        self,
        session_id: str,
        session: AsyncSession,
        *,
        product_id: Optional[str] = None,
        item_id: Optional[int] = None,
    ) -> dict:
        """Remove by item_id or product_id and return the updated cart."""
        if item_id is not None:
            await session.execute(
                delete(CartItem).where(CartItem.session_id == session_id, CartItem.id == item_id)
            )
            await session.commit()
            logger.info("remove_from_cart: removed item_id=%s for session=%s", item_id, session_id)
            return await self.list_cart(session_id, session)

        if product_id:
            await session.execute(
                delete(CartItem).where(CartItem.session_id == session_id, CartItem.product_id == product_id)
            )
            await session.commit()
            logger.info("remove_from_cart: removed product_id=%s for session=%s", product_id, session_id)
            return await self.list_cart(session_id, session)

        logger.info("remove_from_cart: no selector; returning current cart (session=%s)", session_id)
        return await self.list_cart(session_id, session)