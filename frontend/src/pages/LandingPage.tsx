import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { GameMode, ModelProfile } from "../types/game";

const MODES: { id: GameMode; title: string; description: string }[] = [
  {
    id: "classic",
    title: "經典模式（半白話）",
    description: "現代語境語料，建立 LLM 解碼直覺。",
  },
  {
    id: "qing",
    title: "清代模式（古文）",
    description: "清代歷史文本語料，探索數位人文脈絡重建。",
  },
];

export function LandingPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<GameMode>("classic");
  const [model, setModel] = useState<ModelProfile>("qwen");

  return (
    <div className="landing-page">
      <header className="landing-header">
        <p className="brand-mark">nc_</p>
        <h1>Token Trail</h1>
        <p className="landing-subtitle">
          Visualizing LLM Decoding Through Interactive Gameplay
        </p>
      </header>

      <section className="mode-select">
        <h2>選擇遊戲模式</h2>
        <div className="mode-grid">
          {MODES.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`mode-card ${mode === item.id ? "active" : ""}`}
              onClick={() => setMode(item.id)}
            >
              <strong>{item.title}</strong>
              <span>{item.description}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="model-select">
        <h2>解碼引擎（靜態模擬）</h2>
        <div className="model-grid">
          <button
            type="button"
            className={model === "qwen" ? "active" : ""}
            onClick={() => setModel("qwen")}
          >
            Qwen Mode
          </button>
          <button
            type="button"
            className={model === "gemini" ? "active" : ""}
            onClick={() => setModel("gemini")}
          >
            Gemini Mode
          </button>
        </div>
      </section>

      <button
        type="button"
        className="start-button"
        onClick={() => navigate("/game", { state: { mode, model } })}
      >
        Start Game
      </button>
    </div>
  );
}
