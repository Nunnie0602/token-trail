import { loadModelProfiles } from "../../services/corpusLoader";
import type { FpsStats } from "../../utils/fpsStats";
import type { ModelProfile } from "../../types/game";

type FooterProps = {
  fpsStats: FpsStats;
  model: ModelProfile;
};

export function Footer({ fpsStats, model }: FooterProps) {
  const engineLabel = loadModelProfiles().profiles[model].engine_label;
  const fpsLabel =
    fpsStats.samples > 0
      ? `${fpsStats.current} (avg ${fpsStats.avg}, min ${fpsStats.min})`
      : `${fpsStats.current}`;

  return (
    <footer className="app-footer">
      <span>FPS: {fpsLabel}</span>
      <span>ENGINE: {engineLabel}</span>
      <span>REFRESH OVER HTTP POST</span>
    </footer>
  );
}
