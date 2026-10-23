from app.models.schemas import StepRecord

PROMPT_WINDOW_MAX_SEGMENTS = 20
LOW_PROB_THRESHOLD = 0.2
TEMPERATURE_BASE = 0.5
TEMPERATURE_SCALE = 1.2
SPEED_BASE = 1.0
SPEED_TEMP_FACTOR = 0.17


def derive_temperature(prob: float, *, current: float = 1.0) -> float:
    bump = (1.0 - prob) * TEMPERATURE_SCALE
    if prob < LOW_PROB_THRESHOLD:
        bump += 0.15
    return round(max(current, TEMPERATURE_BASE + bump), 2)


def derive_speed_multiplier(temperature: float) -> float:
    return round(SPEED_BASE + temperature * SPEED_TEMP_FACTOR, 1)


def rebuild_sliding_prompt(initial_text: str, step_history: list[StepRecord]) -> str:
    segments = [initial_text] + [record.text for record in step_history]
    if len(segments) > PROMPT_WINDOW_MAX_SEGMENTS:
        segments = segments[-PROMPT_WINDOW_MAX_SEGMENTS:]
    return "".join(segments)


def initial_prompt_segment(prompt: str, step_history: list[StepRecord]) -> str:
    if not step_history:
        return prompt
    consumed = "".join(record.text for record in step_history)
    if prompt.endswith(consumed):
        return prompt[: -len(consumed)] or prompt
    return prompt[: max(len(prompt) - len(consumed), 0)] or prompt
