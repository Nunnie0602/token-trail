import { describe, expect, it } from "vitest";
import { applySlidingWindow } from "../src/engine/slidingWindow";

describe("slidingWindow", () => {
  it("P1-T04: evicts oldest item when exceeding max length", () => {
    const initial = Array.from({ length: 20 }, (_, index) => `token-${index}`);
    const result = applySlidingWindow(initial, "token-new", 20);

    expect(result.items).toHaveLength(20);
    expect(result.items[0]).toBe("token-1");
    expect(result.items[19]).toBe("token-new");
    expect(result.evicted).toBe("token-0");
  });
});
