import { describe, expect, it } from "vitest";
import {
  createInitialFpsStats,
  updateFpsStats,
} from "../src/utils/fpsStats";

describe("fpsStats", () => {
  it("tracks rolling min and average fps samples", () => {
    let stats = createInitialFpsStats();
    stats = updateFpsStats(stats, 60);
    stats = updateFpsStats(stats, 58);
    stats = updateFpsStats(stats, 55);

    expect(stats.current).toBe(55);
    expect(stats.min).toBe(55);
    expect(stats.avg).toBe(58);
    expect(stats.samples).toBe(3);
  });
});
