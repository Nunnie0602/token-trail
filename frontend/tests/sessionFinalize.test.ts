import { describe, expect, it } from "vitest";
import {
  buildFinalizeRequest,
  isPlayingSession,
} from "../src/services/sessionFinalize";
import type { GameSession } from "../src/types/game";

const playingSession: GameSession = {
  sessionId: "sess-1",
  mode: "classic",
  model: "qwen",
  status: "PLAYING",
  score: 50,
  contextTokens: ["夜半", "聽見敲門"],
  storyPath: ["夜半", "聽見敲門"],
  chosenProbs: [0.78],
  temperatureHistory: [1.0, 1.1],
  currentTemperature: 1.1,
  currentNodeId: "C_L1A",
  nextTokens: [],
};

describe("sessionFinalize", () => {
  it("builds voluntary_exit payload", () => {
    expect(buildFinalizeRequest("sess-1", "voluntary_exit")).toEqual({
      session_id: "sess-1",
      completion_type: "voluntary_exit",
      failure_reason: "voluntary_exit",
    });
  });

  it("builds tab_closed payload under voluntary_exit completion type", () => {
    expect(buildFinalizeRequest("sess-1", "tab_closed")).toEqual({
      session_id: "sess-1",
      completion_type: "voluntary_exit",
      failure_reason: "tab_closed",
    });
  });

  it("builds api_error payload", () => {
    expect(buildFinalizeRequest("sess-1", "api_error")).toEqual({
      session_id: "sess-1",
      completion_type: "api_error",
      failure_reason: "api_error",
    });
  });

  it("detects active playing session", () => {
    expect(isPlayingSession(playingSession)).toBe(true);
    expect(isPlayingSession({ ...playingSession, status: "ENDED" })).toBe(false);
    expect(isPlayingSession(null)).toBe(false);
  });
});
