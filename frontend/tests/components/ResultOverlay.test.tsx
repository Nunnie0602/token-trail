import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { ResultOverlay } from "../../src/components/result/ResultOverlay";
import type { GameSession } from "../../src/types/game";

const endedSession: GameSession = {
  sessionId: "test-session",
  mode: "classic",
  model: "qwen",
  status: "ENDED",
  score: 120,
  contextTokens: ["夜半", "聽見敲門"],
  storyPath: ["夜半", "聽見敲門"],
  chosenProbs: [0.78],
  temperatureHistory: [1.0, 1.1],
  currentTemperature: 1.1,
  currentNodeId: "C_L1A",
  nextTokens: [],
};

describe("ResultOverlay", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("P1-T12: shows story when game ended", () => {
    render(
      <MemoryRouter>
        <ResultOverlay session={endedSession} completionType="eos" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("result-overlay")).toBeInTheDocument();
    expect(screen.queryByText(/解碼風格/)).not.toBeInTheDocument();
    expect(screen.getByText(/夜半，聽見敲門/)).toBeInTheDocument();
  });

  it("shows signature field and leaderboard actions per PRD §3.3", () => {
    render(
      <MemoryRouter>
        <ResultOverlay session={endedSession} completionType="eos" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("player-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("submit-leaderboard-btn")).toBeInTheDocument();
    expect(screen.getByTestId("share-linkedin-btn")).toBeDisabled();
  });

  it("submits player name to local leaderboard mock", () => {
    render(
      <MemoryRouter>
        <ResultOverlay session={endedSession} completionType="eos" />
      </MemoryRouter>,
    );
    const input = screen.getByTestId("player-name-input");
    fireEvent.change(input, { target: { value: "低調的四庫全書編纂官" } });
    fireEvent.click(screen.getByTestId("submit-leaderboard-btn"));
    expect(screen.getByText("SUBMITTED")).toBeInTheDocument();
    const stored = JSON.parse(
      localStorage.getItem("token-trail-leaderboard") ?? "[]",
    );
    expect(stored[0].name).toBe("低調的四庫全書編纂官");
    expect(stored[0].score).toBe(120);
  });

  it("hides leaderboard actions for non-eos completion", () => {
    render(
      <MemoryRouter>
        <ResultOverlay session={endedSession} completionType="collision" />
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("submit-leaderboard-btn")).not.toBeInTheDocument();
    expect(screen.getByTestId("leaderboard-disabled-note")).toBeInTheDocument();
  });
});
