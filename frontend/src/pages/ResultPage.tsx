import { useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { isApiEnabled } from "../api/client";
import { getResult } from "../api/gameApi";
import { useGame } from "../context/GameContext";
import { ResultOverlay } from "../components/result/ResultOverlay";
import { Header } from "../components/layout/Header";
import { Footer } from "../components/layout/Footer";
import { MAX_SNAKE_LENGTH } from "../engine/constants";
import { decodePersonality } from "../utils/personalityDecoder";
import type { GameResult, GameSession } from "../types/game";

function isTerminalStatus(status: GameSession["status"]): boolean {
  return status === "ENDED" || status === "COLLISION_FAILED" || status === "ABORTED";
}

function mapResultToSession(result: GameResult): GameSession {
  const initialText = result.story_path[0] ?? "";
  const lastTempIndex = result.temperature_history.length - 1;
  const lastStepIndex = result.step_history.length - 1;
  return {
    sessionId: result.session_id,
    mode: result.mode,
    model: result.model,
    status: result.terminal_game_status,
    score: result.score,
    contextTokens: result.story_path.length > 0 ? result.story_path : [initialText],
    storyPath: result.story_path.length > 0 ? result.story_path : [initialText],
    chosenProbs: result.chosen_probs,
    temperatureHistory: result.temperature_history,
    currentTemperature:
      lastTempIndex >= 0 ? result.temperature_history[lastTempIndex] : 1.0,
    currentNodeId:
      lastStepIndex >= 0 ? result.step_history[lastStepIndex].token_id : null,
    nextTokens: [],
  };
}

export function ResultPage() {
  const navigate = useNavigate();
  const { sessionId: routeSessionId } = useParams();
  const { session, fpsStats, resetSession, startSession } = useGame();
  const useApi = isApiEnabled();
  const [apiResult, setApiResult] = useState<GameResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const effectiveSessionId = routeSessionId ?? session?.sessionId;

  useEffect(() => {
    if (!useApi || !effectiveSessionId) {
      return;
    }

    let cancelled = false;
    getResult(effectiveSessionId)
      .then((result) => {
        if (!cancelled) {
          setApiResult(result);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : "無法載入結算資料");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [useApi, effectiveSessionId]);

  if (useApi) {
    if (!effectiveSessionId) {
      return <Navigate to="/" replace />;
    }
    if (loadError) {
      return <div className="loading-state">{loadError}</div>;
    }
    if (!apiResult) {
      return <div className="loading-state">載入結算中…</div>;
    }

    const displaySession = mapResultToSession(apiResult);
    return (
      <div className="game-layout">
        <Header
          score={displaySession.score}
          contextLength={Math.min(displaySession.contextTokens.length, MAX_SNAKE_LENGTH)}
          mode={displaySession.mode}
          model={displaySession.model}
        />
        <main className="result-page-main">
          <ResultOverlay
            session={displaySession}
            completionType={apiResult.completion_type}
            personalityType={apiResult.personality_type}
            personalityDescription={apiResult.personality_description}
            onRetry={() => {
              const { mode, model } = displaySession;
              resetSession();
              startSession(mode, model);
              navigate("/game", { state: { mode, model }, replace: true });
            }}
          />
        </main>
        <Footer fpsStats={fpsStats} model={displaySession.model} />
      </div>
    );
  }

  if (!session || !isTerminalStatus(session.status)) {
    return <Navigate to="/" replace />;
  }

  const personality = decodePersonality(session.chosenProbs);
  const completionType = session.status === "ENDED" ? "eos" : "collision";

  return (
    <div className="game-layout">
      <Header
        score={session.score}
        contextLength={Math.min(session.contextTokens.length, MAX_SNAKE_LENGTH)}
        mode={session.mode}
        model={session.model}
      />
      <main className="result-page-main">
        <ResultOverlay
          session={session}
          completionType={completionType}
          personalityType={personality.type}
          personalityDescription={personality.description}
          onRetry={() => {
            const { mode, model } = session;
            resetSession();
            startSession(mode, model);
            navigate("/game", { state: { mode, model }, replace: true });
          }}
        />
      </main>
      <Footer fpsStats={fpsStats} model={session.model} />
    </div>
  );
}
