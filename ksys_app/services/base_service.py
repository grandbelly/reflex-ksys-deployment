"""
Base Service Layer
- Provides common database query patterns
- All services inherit from this
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from reflex.utils import console
import logging

logger = logging.getLogger(__name__)


class BaseService:
    """Base service with common database operations"""

    def __init__(self, session: AsyncSession):
        """
        Initialize service with database session

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def execute_query(
        self,
        query: text,
        params: Optional[Dict[str, Any]] = None,
        timeout: str = "10s"
    ) -> List[Dict]:
        """
        Execute SQL query and return results as dict list

        Args:
            query: SQLAlchemy text query
            params: Query parameters
            timeout: Statement timeout (default: 10s)

        Returns:
            List of dict rows
        """
        try:
            # Set statement timeout
            await self.session.execute(text(f"SET LOCAL statement_timeout = '{timeout}'"))

            # Execute query
            result = await self.session.execute(query, params or {})

            # Convert to dict list
            rows = result.mappings().all()
            data = [dict(row) for row in rows]

            logger.debug(f"Query returned {len(data)} rows")
            return data

        except Exception as e:
            console.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            logger.error(f"Error: {e}", exc_info=True)
            return []

    async def execute_scalar(
        self,
        query: text,
        params: Optional[Dict[str, Any]] = None,
        timeout: str = "10s"
    ) -> Any:
        """
        Execute query and return single scalar value

        Args:
            query: SQLAlchemy text query
            params: Query parameters
            timeout: Statement timeout

        Returns:
            Single value or None
        """
        try:
            await self.session.execute(text(f"SET LOCAL statement_timeout = '{timeout}'"))

            result = await self.session.execute(query, params or {})
            value = result.scalar()

            logger.debug(f"Scalar query returned: {value}")
            return value

        except Exception as e:
            console.error(f"Scalar query failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Error: {e}", exc_info=True)
            return None

    async def execute_insert(
        self,
        query: text,
        params: Optional[Dict[str, Any]] = None,
        timeout: str = "10s"
    ) -> bool:
        """
        Execute INSERT/UPDATE/DELETE query

        Args:
            query: SQLAlchemy text query
            params: Query parameters
            timeout: Statement timeout

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.session.execute(text(f"SET LOCAL statement_timeout = '{timeout}'"))

            await self.session.execute(query, params or {})
            await self.session.commit()

            logger.debug("Insert/Update/Delete successful")
            return True

        except Exception as e:
            await self.session.rollback()
            console.error(f"Insert/Update/Delete failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Error: {e}", exc_info=True)
            return False

    def __repr__(self):
        return f"<{self.__class__.__name__}(session={self.session})>"