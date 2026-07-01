def average_probability(probs: list[float]) -> float:
    if not probs:
        return 0.0
    return sum(probs) / len(probs)


def decode_personality(probs: list[float]) -> tuple[str, str]:
    average_prob = average_probability(probs)

    if average_prob >= 0.7:
        return (
            "Greedy Searcher",
            (
                "你偏好高機率路徑，解碼策略接近 Greedy Search——"
                "穩健、可預測，擅長跟隨模型最自信的 token。"
            ),
        )

    if average_prob < 0.2:
        return (
            "Chaos Explorer",
            "你天生具備高 Temperature 屬性，極度擅長向模型點擊低機率的幻覺 Token！",
        )

    return (
        "Balanced Navigator",
        "你在高機率穩健與低機率探索之間保持平衡，展現出接近 Beam Search 的務實解碼風格。",
    )
