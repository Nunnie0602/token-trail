from dataclasses import dataclass

from app.models.schemas import GameMode, ModelProfile

CANDIDATE_COUNT = 4


@dataclass(frozen=True)
class SamplingProfile:
    temperature: float
    top_p: float
    num_predict: int


_PROFILES: dict[ModelProfile, SamplingProfile] = {
    "qwen": SamplingProfile(temperature=0.85, top_p=0.9, num_predict=160),
    "gemini": SamplingProfile(temperature=1.05, top_p=0.95, num_predict=160),
}

_MODE_SYSTEM: dict[GameMode, str] = {
    "classic": (
        "你是互動故事遊戲的敘事引擎。請用半白話現代中文，"
        "產出簡短、可接續的情境片語（2到8個漢字），不要標點或 JSON。"
    ),
    "qing": (
        "你是清代背景互動故事的敘事引擎。請用簡短古文語境片語（2到8個漢字），"
        "可含之乎者也等語助，不要標點或 JSON。"
    ),
}

_MODEL_STYLE: dict[ModelProfile, str] = {
    "qwen": "語氣平實、節奏明快，偏現代口語敘事。",
    "gemini": "語氣較華麗、意象豐富，可略帶詩意修辭。",
}


def get_sampling_profile(model: ModelProfile) -> SamplingProfile:
    return _PROFILES[model]


def build_generation_prompt(
    *,
    story_context: str,
    mode: GameMode,
    model: ModelProfile,
) -> str:
    return (
        f"{_MODE_SYSTEM[mode]}\n"
        f"風格：{_MODEL_STYLE[model]}\n"
        f"目前故事：{story_context}\n"
        f"請輸出恰好{CANDIDATE_COUNT}個候選，每行一個，不要編號、不要解釋。"
    )
