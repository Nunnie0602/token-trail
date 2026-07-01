from redis.asyncio import Redis

from app.cache.keys import LEADERBOARD_KEY
from app.models.schemas import LeaderboardEntry
from app.services.result import LeaderboardNotEligibleError, ResultManager, ResultNotFoundError


class LeaderboardService:
    def __init__(self, redis: Redis, results: ResultManager) -> None:
        self._redis = redis
        self._results = results

    @staticmethod
    def _member(player_name: str, session_id: str) -> str:
        return f"{player_name}|{session_id}"

    @staticmethod
    def _parse_member(member: str) -> tuple[str, str]:
        if "|" in member:
            name, session_id = member.rsplit("|", 1)
            return name, session_id
        return member, ""

    async def submit(self, player_name: str, score: int, session_id: str) -> None:
        result = await self._results.get(session_id)
        if result is None:
            raise ResultNotFoundError(session_id)
        if result.completion_type != "eos":
            raise LeaderboardNotEligibleError(session_id, result.completion_type)

        authoritative_score = result.score
        member = self._member(player_name, session_id)
        await self._redis.zadd(LEADERBOARD_KEY, {member: authoritative_score})

    async def top(self, limit: int = 100) -> list[LeaderboardEntry]:
        raw = await self._redis.zrevrange(LEADERBOARD_KEY, 0, limit - 1, withscores=True)
        entries: list[LeaderboardEntry] = []
        for rank, (member, score) in enumerate(raw, start=1):
            player_name, session_id = self._parse_member(member)
            entries.append(
                LeaderboardEntry(
                    rank=rank,
                    player_name=player_name,
                    score=int(score),
                    session_id=session_id,
                )
            )
        return entries
