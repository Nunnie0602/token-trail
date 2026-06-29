import { apiRequest } from "./client";
import type {
  GameMode,
  GameStatus,
  ModelProfile,
  StepResponse,
  TokenFood,
} from "../types/game";

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

export type StepRequestBody = {
  session_id: string;
  eaten_token_id: string;
  current_snake_length: number;
};

export async function createSession(
  mode: GameMode,
  model: ModelProfile,
): Promise<CreateSessionResponse> {
  return apiRequest<CreateSessionResponse>("/api/v1/session", {
    method: "POST",
    body: { mode, model },
  });
}

export async function postGameStep(body: StepRequestBody): Promise<StepResponse> {
  return apiRequest<StepResponse>("/api/v1/game/step", {
    method: "POST",
    body,
  });
}

export async function submitLeaderboard(
  playerName: string,
  score: number,
  sessionId: string,
): Promise<void> {
  await apiRequest<void>("/api/v1/leaderboard", {
    method: "POST",
    body: {
      player_name: playerName,
      score,
      session_id: sessionId,
    },
  });
}
