"""P95 latency load test for cache-hit Step API (Phase 2 P2-T18)."""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass
from typing import Literal

import json

import httpx

SessionMode = Literal["shared", "isolated"]


@dataclass
class StepProfileSample:
    redis_get_ms: float
    business_ms: float
    redis_set_ms: float
    serialization_ms: float

    @classmethod
    def from_header(cls, value: str) -> "StepProfileSample":
        return cls(**json.loads(value))


@dataclass
class StepSample:
    client_ms: float
    server_ms: float | None
    profile: StepProfileSample | None


@dataclass
class LoadResult:
    samples: list[StepSample]
    errors: int
    session_mode: SessionMode

    @property
    def latencies_ms(self) -> list[float]:
        return [sample.client_ms for sample in self.samples]

    @property
    def server_latencies_ms(self) -> list[float]:
        return [sample.server_ms for sample in self.samples if sample.server_ms is not None]

    @property
    def profile_samples(self) -> list[StepProfileSample]:
        return [sample.profile for sample in self.samples if sample.profile is not None]

    @property
    def p95_ms(self) -> float:
        return _percentile(self.latencies_ms, 0.95)

    @property
    def server_p95_ms(self) -> float:
        return _percentile(self.server_latencies_ms, 0.95)


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    sorted_ms = sorted(values)
    index = max(0, int(len(sorted_ms) * ratio) - 1)
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
) -> StepSample | None:
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
    server_header = response.headers.get("X-Process-Time-Ms")
    server_ms = float(server_header) if server_header else None
    profile_header = response.headers.get("X-Step-Profile")
    profile = StepProfileSample.from_header(profile_header) if profile_header else None
    return StepSample(client_ms=elapsed_ms, server_ms=server_ms, profile=profile)


async def run_load(
    base_url: str,
    concurrency: int,
    requests_per_worker: int,
    session_mode: SessionMode,
) -> LoadResult:
    samples: list[StepSample] = []
    errors = 0
    lock = asyncio.Lock()

    async with httpx.AsyncClient(timeout=30.0) as client:
        if session_mode == "shared":
            session_id, token_id = await _warm_cache(client, base_url)

            async def shared_worker() -> None:
                nonlocal errors
                for _ in range(requests_per_worker):
                    result = await _single_step(client, base_url, session_id, token_id)
                    async with lock:
                        if result is None:
                            errors += 1
                        else:
                            samples.append(result)

            await asyncio.gather(*[shared_worker() for _ in range(concurrency)])
            return LoadResult(samples=samples, errors=errors, session_mode=session_mode)

        async def isolated_worker() -> None:
            nonlocal errors
            worker_session_id, worker_token_id = await _warm_cache(client, base_url)
            for _ in range(requests_per_worker):
                result = await _single_step(
                    client,
                    base_url,
                    worker_session_id,
                    worker_token_id,
                )
                async with lock:
                    if result is None:
                        errors += 1
                    else:
                        samples.append(result)

        await asyncio.gather(*[isolated_worker() for _ in range(concurrency)])
        return LoadResult(samples=samples, errors=errors, session_mode=session_mode)


def _profile_p95(samples: list[StepProfileSample], field: str) -> float:
    values = [getattr(sample, field) for sample in samples]
    return _percentile(values, 0.95)


def _print_profile_breakdown(samples: list[StepProfileSample]) -> None:
    if not samples:
        return
    print("Server profile P95 breakdown:")
    print(f"  redis_get_ms:      {_profile_p95(samples, 'redis_get_ms'):.2f} ms")
    print(f"  business_ms:       {_profile_p95(samples, 'business_ms'):.2f} ms")
    print(f"  redis_set_ms:      {_profile_p95(samples, 'redis_set_ms'):.2f} ms")
    print(f"  serialization_ms:  {_profile_p95(samples, 'serialization_ms'):.2f} ms")
    accounted = [
        sample.redis_get_ms + sample.business_ms + sample.redis_set_ms + sample.serialization_ms
        for sample in samples
    ]
    print(f"  accounted_p95:     {_percentile(accounted, 0.95):.2f} ms")
    redis_shares = [
        (sample.redis_get_ms + sample.redis_set_ms) / total
        for sample, total in zip(samples, accounted, strict=True)
        if total > 0
    ]
    if redis_shares:
        print(f"  redis_share_p95:   {_percentile(redis_shares, 0.95) * 100:.1f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description="Token Trail Step API load test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=100)
    parser.add_argument("--requests", type=int, default=10, help="requests per worker")
    parser.add_argument(
        "--session-mode",
        choices=("shared", "isolated"),
        default="shared",
        help="shared: all workers use one session (H3 A); isolated: one session per worker (H3 B)",
    )
    args = parser.parse_args()

    result = asyncio.run(
        run_load(args.base_url, args.concurrency, args.requests, args.session_mode)
    )
    print(f"Session mode: {result.session_mode}")
    print(f"Samples: {len(result.samples)}")
    print(f"Errors: {result.errors}")
    if result.latencies_ms:
        print(f"Client P50: {statistics.median(result.latencies_ms):.2f} ms")
        print(f"Client P95: {result.p95_ms:.2f} ms")
        print(f"Client Max: {max(result.latencies_ms):.2f} ms")
    if result.server_latencies_ms:
        print(f"Server P50: {statistics.median(result.server_latencies_ms):.2f} ms")
        print(f"Server P95: {result.server_p95_ms:.2f} ms")
        print(f"Server Max: {max(result.server_latencies_ms):.2f} ms")
    _print_profile_breakdown(result.profile_samples)


if __name__ == "__main__":
    main()
