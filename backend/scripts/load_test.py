"""P95 latency load test for cache-hit Step API (Phase 2 P2-T18)."""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class LoadResult:
    latencies_ms: list[float]
    errors: int

    @property
    def p95_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_ms = sorted(self.latencies_ms)
        index = max(0, int(len(sorted_ms) * 0.95) - 1)
        return sorted_ms[index]


async def _warm_cache(client: httpx.AsyncClient, base_url: str) -> tuple[str, str]:
    create = await client.post(
        f"{base_url}/api/v1/session",
        json={"mode": "classic", "model": "qwen"},
    )
    create.raise_for_status()
    payload = create.json()
    session_id = payload["session_id"]
    token_id = payload["next_tokens_food"][0]["token_id"]
    await asyncio.sleep(0.1)
    return session_id, token_id


async def _single_step(
    client: httpx.AsyncClient,
    base_url: str,
    session_id: str,
    token_id: str,
) -> float | None:
    started = time.perf_counter()
    response = await client.post(
        f"{base_url}/api/v1/game/step",
        json={
            "session_id": session_id,
            "eaten_token_id": token_id,
            "current_snake_length": 2,
        },
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if response.status_code != 200:
        return None
    body = response.json()
    if not body.get("cache_hit"):
        return None
    return elapsed_ms


async def run_load(base_url: str, concurrency: int, requests_per_worker: int) -> LoadResult:
    latencies: list[float] = []
    errors = 0

    async with httpx.AsyncClient(timeout=10.0) as client:
        session_id, token_id = await _warm_cache(client, base_url)

        async def worker() -> None:
            nonlocal errors
            for _ in range(requests_per_worker):
                result = await _single_step(client, base_url, session_id, token_id)
                if result is None:
                    errors += 1
                else:
                    latencies.append(result)

        await asyncio.gather(*[worker() for _ in range(concurrency)])

    return LoadResult(latencies_ms=latencies, errors=errors)


def main() -> None:
    parser = argparse.ArgumentParser(description="Token Trail Step API load test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=100)
    parser.add_argument("--requests", type=int, default=10, help="requests per worker")
    args = parser.parse_args()

    result = asyncio.run(run_load(args.base_url, args.concurrency, args.requests))
    print(f"Samples: {len(result.latencies_ms)}")
    print(f"Errors: {result.errors}")
    if result.latencies_ms:
        print(f"P50: {statistics.median(result.latencies_ms):.2f} ms")
        print(f"P95: {result.p95_ms:.2f} ms")
        print(f"Max: {max(result.latencies_ms):.2f} ms")


if __name__ == "__main__":
    main()
