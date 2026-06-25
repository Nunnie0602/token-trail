import type { PersonalityResult } from "../types/game";

export function averageProbability(probs: number[]): number {
  if (probs.length === 0) {
    return 0;
  }
  return probs.reduce((sum, value) => sum + value, 0) / probs.length;
}

export function decodePersonality(probs: number[]): PersonalityResult {
  const averageProb = averageProbability(probs);

  if (averageProb >= 0.7) {
    return {
      type: "Greedy Searcher",
      averageProb,
      description:
        "你偏好高機率路徑，解碼策略接近 Greedy Search——穩健、可預測，擅長跟隨模型最自信的 token。",
    };
  }

  if (averageProb < 0.2) {
    return {
      type: "Chaos Explorer",
      averageProb,
      description:
        "你天生具備高 Temperature 屬性，極度擅長向模型點擊低機率的幻覺 Token！",
    };
  }

  return {
    type: "Balanced Navigator",
    averageProb,
    description:
      "你在高機率穩健與低機率探索之間保持平衡，展現出接近 Beam Search 的務實解碼風格。",
  };
}
