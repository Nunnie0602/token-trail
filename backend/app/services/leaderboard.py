from redis.asyncio import Redis

from app.cache.keys import LEADERBOARD_KEY
from app.models.schemas import LeaderboardEntry


class LeaderboardService:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

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
        member = self._member(player_name, session_id)
        await self._redis.zadd(LEADERBOARD_KEY, {member: score})

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
