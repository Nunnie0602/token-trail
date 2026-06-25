import { describe, expect, it } from "vitest";
import { spawnFoodsOnGrid } from "../src/engine/gridSpawner";

describe("gridSpawner", () => {
  it("P1-T05: does not place food on occupied snake cells", () => {
    const occupied = [
      { x: 3, y: 3 },
      { x: 4, y: 3 },
      { x: 5, y: 3 },
      { x: 3, y: 4 },
      { x: 4, y: 4 },
      { x: 5, y: 4 },
      { x: 3, y: 5 },
      { x: 4, y: 5 },
      { x: 5, y: 5 },
    ];

    const tokens = [
      { token_id: "A", text: "甲", prob: 0.4 },
      { token_id: "B", text: "乙", prob: 0.3 },
      { token_id: "C", text: "丙", prob: 0.2 },
      { token_id: "D", text: "丁", prob: 0.1 },
    ];

    const foods = spawnFoodsOnGrid(tokens, 10, 10, occupied);
    for (const food of foods) {
      expect(occupied.some((cell) => cell.x === food.x && cell.y === food.y)).toBe(
        false,
      );
    }
  });
});
