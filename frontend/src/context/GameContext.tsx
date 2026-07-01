import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { isApiEnabled } from "../api/client";
import { createSession, finalizeGame, postGameStep } from "../api/gameApi";
import {
  createGameSession,
  markGameOver,
  processTokenEaten,
  type EatTokenResult,
} from "../services/gameSimulator";
import {
  applyStepResponse,
  mapApiSessionToGameSession,
} from "../services/apiGameAdapter";
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
  sessionLoading: boolean;
  cacheHitPercent: number;
  fpsStats: FpsStats;
  recordFps: (fps: number) => void;
  startSession: (mode: GameMode, model: ModelProfile) => Promise<GameSession>;
  eatToken: (food: TokenFood) => Promise<EatTokenResult | null>;
  setModel: (model: ModelProfile) => void;
  triggerGameOver: () => void;
  resetSession: () => void;
};

const GameContext = createContext<GameContextValue | null>(null);

export function GameProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<GameSession | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [cacheHitPercent, setCacheHitPercent] = useState(100);
  const [fpsStats, setFpsStats] = useState(createInitialFpsStats);
  const useApi = isApiEnabled();

  const recordFps = useCallback((fps: number) => {
    setFpsStats((current) => updateFpsStats(current, fps));
  }, []);

  const startSession = useCallback(
    async (mode: GameMode, model: ModelProfile): Promise<GameSession> => {
      if (!useApi) {
        const next = createGameSession(mode, model);
        setSession(next);
        setCacheHitPercent(100);
        return next;
      }

      setSessionLoading(true);
      try {
        const apiSession = await createSession(mode, model);
        const next = mapApiSessionToGameSession(apiSession, model);
        setSession(next);
        setCacheHitPercent(100);
        return next;
      } finally {
        setSessionLoading(false);
      }
    },
    [useApi],
  );

  const eatToken = useCallback(
    async (food: TokenFood): Promise<EatTokenResult | null> => {
      if (!session || session.status !== "PLAYING") {
        return null;
      }

      if (!useApi) {
        let result: EatTokenResult | null = null;
        setSession((current) => {
          if (!current || current.status !== "PLAYING") {
            return current;
          }
          result = processTokenEaten(current, food);
          return result.session;
        });
        return result;
      }

      try {
        const step = await postGameStep({
          session_id: session.sessionId,
          eaten_token_id: food.token_id,
          current_snake_length: session.contextTokens.length + 1,
        });
        setCacheHitPercent(step.cache_hit ? 100 : 0);

        const updated = applyStepResponse(session, food, step);
        const result: EatTokenResult = {
          session: updated,
          evictedToken: null,
          isEos: step.game_status === "ENDED",
        };
        setSession(updated);
        return result;
      } catch {
        try {
          await finalizeGame({
            session_id: session.sessionId,
            completion_type: "api_error",
            failure_reason: "api_error",
          });
        } catch {
          /* result may be unavailable if session already expired */
        }

        const aborted: GameSession = { ...session, status: "ABORTED" };
        setSession(aborted);
        return {
          session: aborted,
          evictedToken: null,
          isEos: false,
          stepFailed: true,
        };
      }
    },
    [session, useApi],
  );

  const setModel = useCallback(
    (model: ModelProfile) => {
      setSession((current) => {
        if (!current) {
          return current;
        }
        const nextTokens =
          !useApi && current.currentNodeId
            ? getNextTokens(current.mode, model, current.currentNodeId) ?? []
            : current.nextTokens;
        return { ...current, model, nextTokens };
      });
    },
    [useApi],
  );

  const triggerGameOver = useCallback(() => {
    setSession((current) => (current ? markGameOver(current) : current));
  }, []);

  const resetSession = useCallback(() => {
    setSession(null);
    setCacheHitPercent(100);
    setFpsStats(createInitialFpsStats());
  }, []);

  const value = useMemo(
    () => ({
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
    }),
    [
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
