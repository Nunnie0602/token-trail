from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

GameMode = Literal["classic", "qing"]
GameStatus = Literal["PLAYING", "ENDED", "GAME_OVER"]
ModelProfile = Literal["qwen", "gemini"]


class TokenFood(BaseModel):
    token_id: str
    text: str
    prob: float = Field(ge=0.0, le=1.0)
    is_eos: bool = False


class StepRequest(BaseModel):
    session_id: str
    eaten_token_id: str
    current_snake_length: int = Field(ge=1)


class StepResponse(BaseModel):
    session_id: str
    game_status: GameStatus
    current_temperature: float
    snake_speed_multiplier: float
    next_tokens_food: list[TokenFood]
    cache_hit: bool = False


class CreateSessionRequest(BaseModel):
    mode: GameMode
    model: ModelProfile = "qwen"


class CreateSessionResponse(BaseModel):
    session_id: str
    mode: GameMode
    model: ModelProfile
    game_status: GameStatus
    current_prompt: str
    current_temperature: float
    snake_length: int
    current_node_id: str
    next_tokens_food: list[TokenFood]


class SessionResponse(BaseModel):
    session_id: str
    mode: GameMode
    model: ModelProfile
    game_status: GameStatus
    current_prompt: str
    current_temperature: float
    snake_length: int
    current_node_id: str | None
    updated_at: datetime


class LeaderboardSubmitRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=32)
    score: int = Field(ge=0)
    session_id: str


class LeaderboardEntry(BaseModel):
    rank: int
    player_name: str
    score: int
    session_id: str


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
