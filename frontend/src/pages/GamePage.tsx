import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { isApiEnabled } from "../api/client";
import { finalizeGame } from "../api/gameApi";
import { usePlayingSessionExit } from "../hooks/usePlayingSessionExit";
import { createPlacedFoods, GameCanvas } from "../components/game/GameCanvas";
import { LiveDashboard } from "../components/dashboard/LiveDashboard";
import { Footer } from "../components/layout/Footer";
import { Header } from "../components/layout/Header";
import { MAX_SNAKE_LENGTH, GRID_COLS, GRID_ROWS } from "../engine/constants";
import type { SnakeEngine } from "../engine/snakeEngine";
import { useGame } from "../context/GameContext";
import type { GameMode, ModelProfile, PlacedFood, TokenFood } from "../types/game";

type LocationState = {
  mode?: GameMode;
  model?: ModelProfile;
};

export function GamePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { mode = "classic", model = "qwen" } = (location.state as LocationState) ?? {};
  const useApi = isApiEnabled();
  const {
    session,
    sessionLoading,
    cacheHitPercent,
    fpsStats,
    recordFps,
    startSession,
    eatToken,
    setModel,
    triggerGameOver,
    resetSession,
  } = useGame();

  const [placedFoods, setPlacedFoods] = useState<PlacedFood[]>([]);
  const [gameOverMessage, setGameOverMessage] = useState<string | null>(null);
  const [finalizing, setFinalizing] = useState(false);
  const engineRef = useRef<SnakeEngine | null>(null);
  const skipExitFinalizeRef = useRef(false);

  usePlayingSessionExit({
    enabled: useApi,
    session,
    skipFinalizeRef: skipExitFinalizeRef,
  });

  useEffect(() => {
    if (!session) {
      startSession(mode, model);
    }
  }, [session, mode, model, startSession]);

  useEffect(() => {
    if (session?.status === "ENDED" && session.sessionId) {
      navigate(`/result/${session.sessionId}`, { replace: true });
    }
  }, [session?.status, session?.sessionId, navigate]);

  const spawnFoods = useCallback((tokens: TokenFood[]) => {
    if (!tokens || tokens.length === 0) {
      setPlacedFoods([]);
      return;
    }
    const occupied =
      engineRef.current?.getOccupiedCells() ?? [
        { x: Math.floor(GRID_COLS / 2), y: Math.floor(GRID_ROWS / 2) },
      ];
    setPlacedFoods(createPlacedFoods(tokens, occupied));
  }, []);

  useEffect(() => {
    if (session?.status === "PLAYING") {
      spawnFoods(session.nextTokens);
    }
  }, [session?.nextTokens, session?.status, spawnFoods]);

  const handleEatFood = useCallback(
    async (food: PlacedFood) => {
      const result = await eatToken(food);
      if (!result) {
        return;
      }
      if (result.stepFailed) {
        skipExitFinalizeRef.current = true;
        navigate(`/result/${result.session.sessionId}`, { replace: true });
        return;
      }
      if (result.isEos) {
        skipExitFinalizeRef.current = true;
        setPlacedFoods([]);
        navigate(`/result/${result.session.sessionId}`, { replace: true });
        return;
      }
      if (result.session.nextTokens.length > 0) {
        spawnFoods(result.session.nextTokens);
      } else {
        setPlacedFoods([]);
      }
    },
    [eatToken, spawnFoods, navigate],
  );

  const handleEngineReady = useCallback(
    (engine: SnakeEngine) => {
      engineRef.current = engine;
      if (session?.status === "PLAYING" && session.nextTokens.length > 0) {
        spawnFoods(session.nextTokens);
      }
    },
    [session?.status, session?.nextTokens, spawnFoods],
  );

  const handleCollision = useCallback(async () => {
    if (!session) {
      return;
    }

    if (useApi) {
      setFinalizing(true);
      setGameOverMessage("撞牆或咬到自己！正在產生結算報告…");
      skipExitFinalizeRef.current = true;
      try {
        await finalizeGame({
          session_id: session.sessionId,
          completion_type: "collision",
          failure_reason: "collision",
        });
        navigate(`/result/${session.sessionId}`, { replace: true });
      } catch {
        setGameOverMessage("結算失敗，請重試或返回首頁。");
        setFinalizing(false);
        skipExitFinalizeRef.current = false;
      }
      return;
    }

    triggerGameOver();
    setGameOverMessage("撞牆或咬到自己！遊戲結束。");
    navigate(`/result/${session.sessionId}`, { replace: true });
  }, [session, useApi, navigate, triggerGameOver]);

  const handleRetry = useCallback(() => {
    resetSession();
    setGameOverMessage(null);
    setFinalizing(false);
    engineRef.current = null;
    startSession(session?.mode ?? mode, session?.model ?? model);
  }, [resetSession, startSession, session, mode, model]);

  const headText = useMemo(
    () => session?.contextTokens[session.contextTokens.length - 1] ?? "",
    [session?.contextTokens],
  );

  if (!session || sessionLoading) {
    return <div className="loading-state">初始化遊戲中…</div>;
  }

  const showGameOver =
    session.status === "COLLISION_FAILED" || finalizing || Boolean(gameOverMessage);

  return (
    <div className="game-layout">
      <Header
        score={session.score}
        contextLength={Math.min(session.contextTokens.length, MAX_SNAKE_LENGTH)}
        mode={session.mode}
        model={session.model}
        cacheHit={cacheHitPercent}
        onModelChange={setModel}
      />

      <main className="game-main">
        <section className="game-stage">
          <GameCanvas
            key={session.sessionId}
            headText={headText}
            foods={placedFoods}
            onEatFood={handleEatFood}
            onCollision={handleCollision}
            onFpsUpdate={recordFps}
            onEngineReady={handleEngineReady}
            paused={showGameOver}
          />
          {showGameOver && (
            <div className="game-over-panel">
              <p>{gameOverMessage}</p>
              {!finalizing && (
                <>
                  <button type="button" onClick={handleRetry}>
                    重試
                  </button>
                  <button type="button" onClick={() => navigate("/")}>
                    返回首頁
                  </button>
                </>
              )}
            </div>
          )}
        </section>

        <LiveDashboard
          tokens={session.nextTokens}
          temperatureHistory={session.temperatureHistory}
        />
      </main>

      <Footer fpsStats={fpsStats} model={session.model} />
    </div>
  );
}
