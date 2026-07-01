import { getApiBaseUrl, isApiEnabled } from "../api/client";
import { finalizeGame, type FinalizeRequestBody } from "../api/gameApi";
import type { GameResult, GameSession } from "../types/game";

export type ExitFailureReason = "voluntary_exit" | "tab_closed" | "api_error";

export function isPlayingSession(session: GameSession | null): boolean {
  return session?.status === "PLAYING";
}

export function buildFinalizeRequest(
  sessionId: string,
  reason: ExitFailureReason,
): FinalizeRequestBody {
  if (reason === "api_error") {
    return {
      session_id: sessionId,
      completion_type: "api_error",
      failure_reason: "api_error",
    };
  }

  return {
    session_id: sessionId,
    completion_type: "voluntary_exit",
    failure_reason: reason,
  };
}

export function sendFinalizeBeacon(
  sessionId: string,
  reason: ExitFailureReason,
): boolean {
  if (!isApiEnabled() || typeof navigator.sendBeacon !== "function") {
    return false;
  }

  const payload = buildFinalizeRequest(sessionId, reason);
  const blob = new Blob([JSON.stringify(payload)], {
    type: "application/json",
  });
  return navigator.sendBeacon(`${getApiBaseUrl()}/api/v1/game/finalize`, blob);
}

export async function finalizePlayingSession(
  sessionId: string,
  reason: ExitFailureReason,
): Promise<GameResult | null> {
  if (!isApiEnabled()) {
    return null;
  }
  return finalizeGame(buildFinalizeRequest(sessionId, reason));
}
