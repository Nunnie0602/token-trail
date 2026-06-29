def derive_temperature(prob: float) -> float:
    return round(0.5 + (1.0 - prob) * 1.2, 2)


def derive_speed_multiplier(temperature: float) -> float:
    return round(1.0 + temperature * 0.17, 1)
