"""UnitOfWork sobre AsyncSession (async context manager)."""

from __future__ import annotations

from typing import Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._committed = False
        self._rolled_back = False

    async def __aenter__(self) -> "UnitOfWork":
        self._session = self._session_factory()
        self._committed = False
        self._rolled_back = False
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None:
                if not self._rolled_back:
                    await self._session.rollback()
            else:
                if not self._committed and not self._rolled_back:
                    await self._session.commit()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        if self._session is not None:
            await self._session.commit()
            self._committed = True

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()
            self._rolled_back = True

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork no ha sido abierto (use 'async with')")
        return self._session