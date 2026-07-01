from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GameMode = Literal["classic", "qing"]
GameStatus = Literal["PLAYING", "ENDED", "COLLISION_FAILED", "ABORTED"]
TerminalGameStatus = Literal["ENDED", "COLLISION_FAILED", "ABORTED"]
GameCompletionType = Literal["eos", "collision", "voluntary_exit", "api_error"]
ModelProfile = Literal["qwen", "gemini"]


class StepRecord(BaseModel):
    step_index: int = Field(ge=1)
    token_id: str
    text: str
    prob: float = Field(ge=0.0, le=1.0)
    temperature: float
    is_eos: bool = False


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


class FinalizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    completion_type: GameCompletionType
    failure_reason: str | None = None


class GameResult(BaseModel):
    session_id: str
    terminal_game_status: TerminalGameStatus
    completion_type: GameCompletionType
    failure_reason: str | None = None
    mode: GameMode
    model: ModelProfile
    score: int
    snake_length: int
    story_path: list[str]
    chosen_probs: list[float]
    temperature_history: list[float]
    step_history: list[StepRecord]
    personality_type: str
    personality_description: str
    created_at: str
