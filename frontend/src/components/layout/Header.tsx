import { Link } from "react-router-dom";
import type { GameMode, ModelProfile } from "../../types/game";
import { loadModelProfiles } from "../../services/corpusLoader";
import { MAX_SNAKE_LENGTH } from "../../engine/constants";

type HeaderProps = {
  score: number;
  contextLength: number;
  mode: GameMode;
  model: ModelProfile;
  cacheHit?: number;
  onModelChange?: (model: ModelProfile) => void;
};

const MODE_LABEL: Record<GameMode, string> = {
  classic: "CLASSIC",
  qing: "QING",
};

export function Header({
  score,
  contextLength,
  mode,
  model,
  cacheHit = 100,
  onModelChange,
}: HeaderProps) {
  const profiles = loadModelProfiles();

  return (
    <header className="app-header">
      <div className="header-brand">
        <Link to="/" className="brand-mark">
          nc_
        </Link>
        <span className="header-title">TOKEN TRAIL: 準備好開始你的故事了嗎？</span>
      </div>
      <div className="header-stats">
        <span>SCORE: {String(score).padStart(5, "0")}</span>
        <span>
          CONTEXT: {String(contextLength).padStart(2, "0")}/{MAX_SNAKE_LENGTH}
        </span>
        <span>DECODING MODE: {MODE_LABEL[mode]}</span>
        <span>CACHE HIT: {cacheHit}%</span>
      </div>
      {onModelChange && (
        <div className="model-switch">
          {(Object.keys(profiles.profiles) as ModelProfile[]).map((key) => (
            <button
              key={key}
              type="button"
              className={model === key ? "active" : ""}
              onClick={() => onModelChange(key)}
            >
              {profiles.profiles[key].label}
            </button>
          ))}
        </div>
      )}
    </header>
  );
}
