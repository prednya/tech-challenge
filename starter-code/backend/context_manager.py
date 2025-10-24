"""
Context manager for tracking user sessions and preventing AI hallucination.

This module manages search context, validates function call parameters,
and provides suggestions when validation fails.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, delete

from models import SessionContext, SearchContext


class ContextManager:
    # Manages session context and validation.
    
    def __init__(self):
        self.context_window_minutes = 30  # How long to keep search context
    
    async def session_exists(
        self,
        session_id: str,
        session: AsyncSession
    ) -> bool:
        # Check if session exists
        statement = select(SessionContext).where(
            SessionContext.session_id == session_id
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none() is not None
    
    async def get_context(
        self,
        session_id: str,
        session: AsyncSession
    ) -> Optional[SessionContext]:
        # Get session context
        statement = select(SessionContext).where(
            SessionContext.session_id == session_id
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()
    
    async def update_context(
        self,
        session_id: str,
        context_data: Dict[str, Any],
        session: AsyncSession
    ) -> None:
        # Update session context
        
        # Get existing context
        existing = await self.get_context(session_id, session)
        
        if existing:
            # Update existing context
            existing.context_data.update(context_data)
            existing.updated_at = datetime.utcnow()
            session.add(existing)
        else:
            # Create new context
            context = SessionContext(
                session_id=session_id,
                context_data=context_data
            )
            session.add(context)
        
        await session.commit()
    
    async def track_search_results(
        self,
        session_id: str,
        query: str,
        results: List[str],  # List of product IDs
        category: Optional[str] = None,
        session_db: AsyncSession = None
    ) -> None:
        # Track search results for validation
        
        if not session_db:
            return
        
        # Clean old search context
        await self._cleanup_old_search_context(session_id, session_db)
        
        # Add new search context
        search_context = SearchContext(
            session_id=session_id,
            search_query=query,
            results=results,
            category=category
        )
        session_db.add(search_context)
        await session_db.commit()
    
    async def validate_product_id(
        self,
        session_id: str,
        product_id: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Validate that a product ID was recently seen in search results.
        This helps prevent AI hallucination.
        """
        
        # Get recent search contexts
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.context_window_minutes)
        
        statement = select(SearchContext).where(
            SearchContext.session_id == session_id,
            SearchContext.timestamp >= cutoff_time
        )
        result = await session.execute(statement)
        search_contexts = result.scalars().all()
        
        # Check if product ID appears in any recent search
        for context in search_contexts:
            if product_id in context.results:
                return {
                    "valid": True,
                    "found_in_search": context.search_query,
                    "search_timestamp": context.timestamp
                }
        
        # Product ID not found - generate suggestions
        all_product_ids = []
        for context in search_contexts:
            all_product_ids.extend(context.results)
        
        suggestions = self._generate_product_suggestions(product_id, all_product_ids)
        
        return {
            "valid": False,
            "error": f"Product ID '{product_id}' not found in recent searches",
            "suggestions": suggestions,
            "recent_searches": [ctx.search_query for ctx in search_contexts]
        }
    
    async def get_recent_products(
        self,
        session_id: str,
        limit: int = 20,
        session: AsyncSession = None
    ) -> List[str]:
        # Get recently searched product IDs
        
        if not session:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.context_window_minutes)
        
        statement = select(SearchContext).where(
            SearchContext.session_id == session_id,
            SearchContext.timestamp >= cutoff_time
        ).order_by(SearchContext.timestamp.desc())
        
        result = await session.execute(statement)
        search_contexts = result.scalars().all()
        
        # Collect unique product IDs
        product_ids = []
        for context in search_contexts:
            for pid in context.results:
                if pid not in product_ids:
                    product_ids.append(pid)
        
        return product_ids[:limit]
    
    async def _cleanup_old_search_context(
        self,
        session_id: str,
        session: AsyncSession
    ) -> None:
        # Clean up old search context to prevent memory bloat
        
        cutoff_time = datetime.utcnow() - timedelta(hours=2)  # Keep 2 hours of context
        
        statement = delete(SearchContext).where(
            SearchContext.session_id == session_id,
            SearchContext.timestamp < cutoff_time
        )
        await session.execute(statement)
        await session.commit()
    
    def _generate_product_suggestions(
        self,
        invalid_product_id: str,
        valid_product_ids: List[str]
    ) -> List[Dict[str, Any]]:
        # Generate suggestions for invalid product IDs
        
        suggestions = []
        
        # Simple similarity matching (in production, use fuzzy matching)
        for pid in valid_product_ids[:5]:  # Limit suggestions
            similarity = self._calculate_similarity(invalid_product_id, pid)
            if similarity > 0.5:  # Threshold for suggestions
                suggestions.append({
                    "product_id": pid,
                    "similarity": similarity,
                    "reason": "Similar product ID format"
                })
        
        return sorted(suggestions, key=lambda x: x["similarity"], reverse=True)
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        # Calculate simple string similarity (Levenshtein-based)
        
        if str1 == str2:
            return 1.0
        
        # Simple character overlap calculation
        common_chars = set(str1) & set(str2)
        total_chars = set(str1) | set(str2)
        
        if not total_chars:
            return 0.0
        
        return len(common_chars) / len(total_chars)