import { describe, expect, it } from "vitest";
import {
  generateDefaultPlayerName,
  PLAYER_NAME_MAX_LENGTH,
  sanitizePlayerName,
} from "../src/utils/playerName";

describe("playerName", () => {
  it("generates default name within length limit", () => {
    const name = generateDefaultPlayerName();
    expect(name.length).toBeGreaterThan(0);
    expect(name.length).toBeLessThanOrEqual(PLAYER_NAME_MAX_LENGTH);
    expect(name).toMatch(/^(不願具名|低調|隱姓埋名)的/);
  });

  it("sanitizes malicious characters and truncates", () => {
    const sanitized = sanitizePlayerName('<script>"admin"&</script>abcdefghijklmnop');
    expect(sanitized).not.toMatch(/[<>"'&]/);
    expect(sanitized.length).toBeLessThanOrEqual(PLAYER_NAME_MAX_LENGTH);
  });
});
