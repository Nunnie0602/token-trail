import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  createGameSession,
  markGameOver,
  processTokenEaten,
  type EatTokenResult,
} from "../services/gameSimulator";
import { getNextTokens } from "../services/corpusLoader";
import {
  createInitialFpsStats,
  updateFpsStats,
  type FpsStats,
} from "../utils/fpsStats";
import type {
  GameMode,
  GameSession,
  ModelProfile,
  TokenFood,
} from "../types/game";

type GameContextValue = {
  session: GameSession | null;
  fpsStats: FpsStats;
  recordFps: (fps: number) => void;
  startSession: (mode: GameMode, model: ModelProfile) => GameSession;
  eatToken: (food: TokenFood) => EatTokenResult | null;
  setModel: (model: ModelProfile) => void;
  triggerGameOver: () => void;
  resetSession: () => void;
};

const GameContext = createContext<GameContextValue | null>(null);

export function GameProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<GameSession | null>(null);
  const [fpsStats, setFpsStats] = useState(createInitialFpsStats);

  const recordFps = useCallback((fps: number) => {
    setFpsStats((current) => updateFpsStats(current, fps));
  }, []);

  const startSession = useCallback((mode: GameMode, model: ModelProfile) => {
    const next = createGameSession(mode, model);
    setSession(next);
    return next;
  }, []);

  const eatToken = useCallback((food: TokenFood): EatTokenResult | null => {
    let result: EatTokenResult | null = null;
    setSession((current) => {
      if (!current || current.status !== "PLAYING") {
        return current;
      }
      result = processTokenEaten(current, food);
      return result.session;
    });
    return result;
  }, []);

  const setModel = useCallback((model: ModelProfile) => {
    setSession((current) => {
      if (!current) {
        return current;
      }
      const nextTokens = current.currentNodeId
        ? getNextTokens(current.mode, model, current.currentNodeId) ?? []
        : current.nextTokens;
      return { ...current, model, nextTokens };
    });
  }, []);

  const triggerGameOver = useCallback(() => {
    setSession((current) => (current ? markGameOver(current) : current));
  }, []);

  const resetSession = useCallback(() => {
    setSession(null);
    setFpsStats(createInitialFpsStats());
  }, []);

  const value = useMemo(
    () => ({
      session,
      fpsStats,
      recordFps,
      startSession,
      eatToken,
      setModel,
      triggerGameOver,
      resetSession,
    }),
    [
      session,
      fpsStats,
      recordFps,
      startSession,
      eatToken,
      setModel,
      triggerGameOver,
      resetSession,
    ],
  );

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
}

export function useGame(): GameContextValue {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error("useGame must be used within GameProvider");
  }
  return context;
}
