export type FpsStats = {
  current: number;
  min: number;
  avg: number;
  samples: number;
};

export function createInitialFpsStats(): FpsStats {
  return { current: 60, min: 60, avg: 60, samples: 0 };
}

export function updateFpsStats(prev: FpsStats, fps: number): FpsStats {
  const samples = prev.samples + 1;
  const avg = Math.round((prev.avg * prev.samples + fps) / samples);
  return {
    current: fps,
    min: prev.samples === 0 ? fps : Math.min(prev.min, fps),
    avg,
    samples,
  };
}
