import type { GameMode, GameStatus, ModelProfile, TokenFood } from "../../src/types/game";

export type CreateSessionResponse = {
  session_id: string;
  mode: GameMode;
  model: ModelProfile;
  game_status: GameStatus;
  current_prompt: string;
  current_temperature: number;
  snake_length: number;
  current_node_id: string;
  next_tokens_food: TokenFood[];
};

export type StepResponse = {
  session_id: string;
  game_status: GameStatus;
  current_temperature: number;
  snake_speed_multiplier: number;
  next_tokens_food: TokenFood[];
  cache_hit: boolean;
};

export type LeaderboardEntry = {
  rank: number;
  player_name: string;
  score: number;
  session_id: string;
};

export type LeaderboardResponse = {
  entries: LeaderboardEntry[];
};

export type E2eGameResult = {
  session_id: string;
  score: number;
  completion_type: string;
};

function readProcessEnv(key: string): string | undefined {
  const runtime = globalThis as {
    process?: { env?: Record<string, string | undefined> };
  };
  return runtime.process?.env?.[key];
}

export function getE2eApiBase(): string {
  const base = readProcessEnv("E2E_API_BASE_URL") ?? import.meta.env.VITE_API_BASE_URL ?? "";
  return base.replace(/\/$/, "");
}

export function isE2eApiAvailable(): boolean {
  return getE2eApiBase().length > 0;
}

async function e2eRequest<T>(
  path: string,
  options: { method?: "GET" | "POST"; body?: unknown } = {},
): Promise<T> {
  const response = await fetch(`${getE2eApiBase()}${path}`, {
    method: options.method ?? "GET",
    headers: { "Content-Type": "application/json" },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`E2E API ${response.status}: ${detail}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function e2eHealthCheck(): Promise<boolean> {
  try {
    const payload = await e2eRequest<{ service: string; redis: boolean }>("/health");
    return payload.service === "token-trail-api" && payload.redis === true;
  } catch {
    return false;
  }
}

export async function e2eCreateSession(
  mode: GameMode,
  model: ModelProfile,
): Promise<CreateSessionResponse> {
  return e2eRequest<CreateSessionResponse>("/api/v1/session", {
    method: "POST",
    body: { mode, model },
  });
}

export async function e2ePostGameStep(body: {
  session_id: string;
  eaten_token_id: string;
  current_snake_length: number;
}): Promise<StepResponse> {
  return e2eRequest<StepResponse>("/api/v1/game/step", {
    method: "POST",
    body,
  });
}

export async function e2eSubmitLeaderboard(
  playerName: string,
  score: number,
  sessionId: string,
): Promise<void> {
  await e2eRequest<void>("/api/v1/leaderboard", {
    method: "POST",
    body: {
      player_name: playerName,
      score,
      session_id: sessionId,
    },
  });
}

export async function e2eGetLeaderboard(): Promise<LeaderboardResponse> {
  return e2eRequest<LeaderboardResponse>("/api/v1/leaderboard");
}

export async function e2eGetResult(sessionId: string): Promise<E2eGameResult> {
  return e2eRequest<E2eGameResult>(`/api/v1/game/result/${sessionId}`);
}

export function pickToken(tokens: TokenFood[], preferEos: boolean): TokenFood {
  if (preferEos) {
    const eos = tokens.find((token) => token.is_eos);
    if (eos) {
      return eos;
    }
  }
  const nonEos = tokens.filter((token) => !token.is_eos);
  const pool = nonEos.length > 0 ? nonEos : tokens;
  return pool.reduce((best, token) => (token.prob > best.prob ? token : best));
}
