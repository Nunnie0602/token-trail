import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
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
  const {
    session,
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
  const engineRef = useRef<SnakeEngine | null>(null);

  useEffect(() => {
    if (!session) {
      startSession(mode, model);
    }
  }, [session, mode, model, startSession]);

  useEffect(() => {
    if (session?.status === "ENDED") {
      navigate("/result", { replace: true });
    }
  }, [session?.status, navigate]);

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
    (food: PlacedFood) => {
      const result = eatToken(food);
      if (!result) {
        return;
      }
      if (result.isEos) {
        setPlacedFoods([]);
        navigate("/result", { replace: true });
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

  const handleCollision = useCallback(() => {
    triggerGameOver();
    setGameOverMessage("撞牆或咬到自己！遊戲結束。");
  }, [triggerGameOver]);

  const handleRetry = useCallback(() => {
    resetSession();
    setGameOverMessage(null);
    engineRef.current = null;
    startSession(session?.mode ?? mode, session?.model ?? model);
  }, [resetSession, startSession, session, mode, model]);

  const headText = useMemo(
    () => session?.contextTokens[session.contextTokens.length - 1] ?? "",
    [session?.contextTokens],
  );

  if (!session) {
    return <div className="loading-state">初始化遊戲中…</div>;
  }

  const showGameOver = session.status === "GAME_OVER";

  return (
    <div className="game-layout">
      <Header
        score={session.score}
        contextLength={Math.min(session.contextTokens.length, MAX_SNAKE_LENGTH)}
        mode={session.mode}
        model={session.model}
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
              <button type="button" onClick={handleRetry}>
                重試
              </button>
              <button type="button" onClick={() => navigate("/")}>
                返回首頁
              </button>
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
