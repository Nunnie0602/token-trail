import { describe, expect, it } from "vitest";
import { buildStoryText } from "../src/utils/storyBuilder";

describe("storyBuilder", () => {
  it("P1-T06: joins token path into PRD continuous narrative", () => {
    const story = buildStoryText(["夜半時分", "看見鬼影", "聽見敲門"]);
    expect(story).toBe("夜半時分，看見鬼影聽見敲門......。");
  });

  it("handles single-token path", () => {
    expect(buildStoryText(["夜半時分"])).toBe("夜半時分......。");
  });

  it("handles empty path", () => {
    expect(buildStoryText([])).toBe("");
  });
});
