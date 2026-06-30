export type GameMode = "classic" | "qing";
export type ModelProfile = "qwen" | "gemini";
export type GameStatus = "PLAYING" | "ENDED" | "GAME_OVER";

export type TokenFood = {
  token_id: string;
  text: string;
  prob: number;
  is_eos?: boolean;
};

export type StepResponse = {
  session_id: string;
  game_status: GameStatus;
  current_temperature: number;
  snake_speed_multiplier: number;
  next_tokens_food: TokenFood[];
  cache_hit?: boolean;
};

export type CorpusNode = {
  next: TokenFood[];
};

export type InitialToken = {
  token_id: string;
  text: string;
};

export type Corpus = {
  mode: GameMode;
  initial_tokens: InitialToken[];
  nodes: Record<string, CorpusNode>;
};

export type ModelProfileConfig = {
  label: string;
  engine_label: string;
};

export type ModelProfiles = {
  profiles: Record<ModelProfile, ModelProfileConfig>;
  text_overrides: Record<GameMode, Record<string, string>>;
};

export type PersonalityType =
  | "Greedy Searcher"
  | "Chaos Explorer"
  | "Balanced Navigator";

export type PersonalityResult = {
  type: PersonalityType;
  averageProb: number;
  description: string;
};

export type GameSession = {
  sessionId: string;
  mode: GameMode;
  model: ModelProfile;
  status: GameStatus;
  score: number;
  contextTokens: string[];
  storyPath: string[];
  chosenProbs: number[];
  temperatureHistory: number[];
  currentTemperature: number;
  currentNodeId: string | null;
  nextTokens: TokenFood[];
};

export type Point = {
  x: number;
  y: number;
};

export type Direction = "UP" | "DOWN" | "LEFT" | "RIGHT";

export type PlacedFood = TokenFood & Point;

export type SnakeSegment = Point & {
  text: string;
  isHead?: boolean;
};
