"""H1 verification: confirm Step API cache_hit and Redis prefetch key alignment."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

import httpx
import redis.asyncio as redis


def prefetch_key(session_id: str, eaten_token_id: str) -> str:
    return f"prefetch:{session_id}:{eaten_token_id}"


async def run(base_url: str, redis_url: str, sequential: int, concurrent: int) -> None:
    client = redis.from_url(redis_url, decode_responses=True)
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            create = await http.post(
                f"{base_url}/api/v1/session",
                json={"mode": "classic", "model": "qwen"},
            )
            create.raise_for_status()
            payload = create.json()
            session_id = payload["session_id"]
            token_id = payload["next_tokens_food"][0]["token_id"]
            await asyncio.sleep(0.1)

            cache_key = prefetch_key(session_id, token_id)
            redis_exists = bool(await client.exists(cache_key))
            redis_raw = await client.get(cache_key)
            redis_ttl = await client.ttl(cache_key)
            token_count = 0
            if redis_raw:
                token_count = len(json.loads(redis_raw).get("next_tokens_food", []))

            seq_hits = 0
            seq_misses = 0
            seq_latencies: list[float] = []
            for index in range(sequential):
                started = time.perf_counter()
                response = await http.post(
                    f"{base_url}/api/v1/game/step",
                    json={
                        "session_id": session_id,
                        "eaten_token_id": token_id,
                        "current_snake_length": 2,
                    },
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                body = response.json() if response.status_code == 200 else {}
                cache_hit = body.get("cache_hit")
                if cache_hit is True:
                    seq_hits += 1
                    seq_latencies.append(elapsed_ms)
                elif cache_hit is False:
                    seq_misses += 1
                print(
                    f"  seq {index + 1:02d}: status={response.status_code} "
                    f"cache_hit={cache_hit} latency={elapsed_ms:.2f}ms"
                )

            async def one_step() -> tuple[int, bool | None, float]:
                started = time.perf_counter()
                response = await http.post(
                    f"{base_url}/api/v1/game/step",
                    json={
                        "session_id": session_id,
                        "eaten_token_id": token_id,
                        "current_snake_length": 2,
                    },
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                body = response.json() if response.status_code == 200 else {}
                return response.status_code, body.get("cache_hit"), elapsed_ms

            burst = await asyncio.gather(*[one_step() for _ in range(concurrent)])
            burst_hits = sum(1 for status, hit, _ in burst if status == 200 and hit is True)
            burst_misses = sum(1 for status, hit, _ in burst if status == 200 and hit is False)
            burst_errors = sum(1 for status, _, _ in burst if status != 200)
            burst_latencies = [ms for status, hit, ms in burst if status == 200 and hit is True]

            print("--- H1 Cache Hit Verification ---")
            print(f"session_id: {session_id}")
            print(f"token_id: {token_id}")
            print(f"redis_key: {cache_key}")
            print(f"redis_exists: {redis_exists}")
            print(f"redis_ttl: {redis_ttl}s")
            print(f"redis_next_tokens_count: {token_count}")
            print(
                f"sequential: total={sequential} hits={seq_hits} misses={seq_misses} "
                f"hit_rate={seq_hits / sequential * 100:.1f}%"
            )
            if seq_latencies:
                print(f"sequential_p50: {statistics.median(seq_latencies):.2f} ms")
            print(
                f"concurrent_{concurrent}: hits={burst_hits} misses={burst_misses} "
                f"errors={burst_errors} hit_rate={burst_hits / concurrent * 100:.1f}%"
            )
            if burst_latencies:
                sorted_ms = sorted(burst_latencies)
                p95_index = max(0, int(len(sorted_ms) * 0.95) - 1)
                print(f"concurrent_p50: {statistics.median(burst_latencies):.2f} ms")
                print(f"concurrent_p95: {sorted_ms[p95_index]:.2f} ms")
    finally:
        await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify cache hit path for P2-T18 H1")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--redis-url", default="redis://localhost:6379/0")
    parser.add_argument("--sequential", type=int, default=20)
    parser.add_argument("--concurrent", type=int, default=50)
    args = parser.parse_args()
    asyncio.run(run(args.base_url, args.redis_url, args.sequential, args.concurrent))


if __name__ == "__main__":
    main()
