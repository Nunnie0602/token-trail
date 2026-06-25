import { describe, expect, it } from "vitest";
import { decodePersonality } from "../src/utils/personalityDecoder";

describe("personalityDecoder", () => {
  it("P1-T01: returns Greedy Searcher for average 0.85", () => {
    const result = decodePersonality([0.9, 0.8]);
    expect(result.type).toBe("Greedy Searcher");
  });

  it("P1-T02: returns Chaos Explorer for average 0.14", () => {
    const result = decodePersonality([0.02, 0.05, 0.35]);
    expect(result.type).toBe("Chaos Explorer");
  });

  it("P1-T03: returns Balanced Navigator for average 0.45", () => {
    const result = decodePersonality([0.5, 0.4]);
    expect(result.type).toBe("Balanced Navigator");
  });
});
