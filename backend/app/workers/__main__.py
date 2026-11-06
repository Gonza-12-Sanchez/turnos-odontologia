"""Entrypoint: python -m app.workers (o app.workers.whatsapp_worker)."""

import asyncio

from app.workers.whatsapp_worker import run_worker

if __name__ == "__main__":
    asyncio.run(run_worker())
