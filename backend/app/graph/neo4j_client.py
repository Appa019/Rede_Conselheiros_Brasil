from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings


class Neo4jClient:
    """Async wrapper around the Neo4j Python driver."""

    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Initialize the async Neo4j driver."""
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def close(self) -> None:
        """Gracefully close the driver connection."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None

    async def __aenter__(self) -> "Neo4jClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def execute_read(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Run a read transaction and return a list of record dicts."""
        if self._driver is None:
            raise RuntimeError("Neo4j driver is not connected")

        async with self._driver.session() as session:
            result = await session.run(query, parameters=params or {})
            records = await result.data()
            return records

    async def execute_write(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Run a write transaction and return a list of record dicts."""
        if self._driver is None:
            raise RuntimeError("Neo4j driver is not connected")

        async with self._driver.session() as session:
            result = await session.run(query, parameters=params or {})
            records = await result.data()
            return records

    async def health_check(self) -> bool:
        """Verify connectivity by running a lightweight query."""
        try:
            await self.execute_read("RETURN 1 AS ok")
            return True
        except Exception:
            return False
