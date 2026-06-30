# Token Trail API 文件

> 版本：0.2.0 | 對照 PRD §7.1 | Phase 2 後端整合  
> **本文件為 API 契約唯一來源（Single Source of Truth）**；修改 `backend/app/api/` 時須同步更新。

## 1. 總覽

| 項目 | 說明 |
|------|------|
| Base URL（本地） | `http://localhost:8000` |
| API 前綴 | `/api/v1` |
| 互動文件 | `GET /docs`（Swagger UI） |
| 內容格式 | `application/json` |
| 字元編碼 | UTF-8 |

### 1.1 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 連線 |
| `CORS_ORIGINS` | `http://localhost:3000` | 允許的前端來源（逗號分隔） |
| `LOG_LEVEL` | `INFO` | Structlog 等級 |
| `OLLAMA_HOST` | `http://localhost:11434` | Phase 3 推理用（Phase 2 尚未接入） |

### 1.2 共用型別

```typescript
type GameMode = "classic" | "qing";
type GameStatus = "PLAYING" | "ENDED" | "GAME_OVER";
type ModelProfile = "qwen" | "gemini";

type TokenFood = {
  token_id: string;
  text: string;
  prob: number;       // 0.0 ~ 1.0
  is_eos?: boolean;   // 預設 false
};
```

### 1.3 請求追蹤

| Header | 方向 | 說明 |
|--------|------|------|
| `X-Trace-Id` | Request（選填） | 客戶端自訂追蹤 ID |
| `X-Trace-Id` | Response | 實際使用的 trace ID（未提供時由後端產生 UUID） |

---

## 2. 健康檢查

### `GET /health`

服務與 Redis 連線探測，供 Docker healthcheck 與運維使用。

**Response 200**

```json
{
  "status": "ok",
  "service": "token-trail-api",
  "redis": true
}
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| status | string | `"ok"`（Redis 正常）或 `"degraded"`（Redis 不可用） |
| service | string | 固定 `"token-trail-api"` |
| redis | boolean | Redis `PING` 結果 |

---

## 3. Session API

### `POST /api/v1/session`

建立新遊戲 Session，隨機選取初始 Token，並為當前 4 個候選分支寫入預載快取。

**Request Body**

```json
{
  "mode": "classic",
  "model": "qwen"
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| mode | GameMode | 是 | 遊戲模式 |
| model | ModelProfile | 否 | 模型風格，預設 `"qwen"` |

**Response 201**

```json
{
  "session_id": "fb6a8b12-9c34",
  "mode": "classic",
  "model": "qwen",
  "game_status": "PLAYING",
  "current_prompt": "夜半時分",
  "current_temperature": 1.0,
  "snake_length": 1,
  "current_node_id": "INIT_01",
  "next_tokens_food": [
    { "token_id": "C_L1A", "text": "聽見敲門", "prob": 0.78, "is_eos": false },
    { "token_id": "C_L1B", "text": "看見鬼影", "prob": 0.11, "is_eos": false },
    { "token_id": "C_L1C", "text": "撿到珍珠奶茶", "prob": 0.05, "is_eos": false },
    { "token_id": "C_L1D", "text": "窗外傳來笑聲", "prob": 0.06, "is_eos": false }
  ]
}
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| session_id | string | UUID 前 13 字元 |
| current_prompt | string | 初始 Token 文字（蛇頭） |
| snake_length | integer | 初始為 1 |
| current_node_id | string | 當前語料節點 ID |
| next_tokens_food | TokenFood[] | 固定 4 組候選食物 |

**副作用：** 對 `next_tokens_food` 中各非 EOS `token_id` 平行寫入 Branch Cache（見 §7）。

---

### `GET /api/v1/session/{session_id}`

查詢 Session 完整狀態。

**Path Parameters**

| 參數 | 說明 |
|------|------|
| session_id | Session 識別碼 |

**Response 200**

```json
{
  "session_id": "fb6a8b12-9c34",
  "mode": "classic",
  "model": "qwen",
  "game_status": "PLAYING",
  "current_prompt": "夜半時分聽見敲門",
  "current_temperature": 1.15,
  "snake_length": 2,
  "current_node_id": "C_L1A",
  "updated_at": "2026-06-25T10:30:00+00:00"
}
```

**Response 404**

```json
{
  "detail": "Session not found: {session_id}"
}
```

Session 不存在或 Redis TTL 過期（30 分鐘）時回傳 404。

---

## 4. Step API

### `POST /api/v1/game/step`

玩家吃下 Token 後觸發。優先讀取 Branch Cache；Miss 時走 Fallback（Mock 推理或靜態安全語料）。

**Request Body**

```json
{
  "session_id": "fb6a8b12-9c34",
  "eaten_token_id": "C_L1A",
  "current_snake_length": 3
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| session_id | string | 是 | 遊戲 Session ID |
| eaten_token_id | string | 是 | 被吃下的 Token ID |
| current_snake_length | integer | 是 | 當前蛇身長度，≥ 1 |

**Response 200**

```json
{
  "session_id": "fb6a8b12-9c34",
  "game_status": "PLAYING",
  "current_temperature": 1.15,
  "snake_speed_multiplier": 1.2,
  "next_tokens_food": [
    { "token_id": "C_L2A", "text": "打開門縫", "prob": 0.71, "is_eos": false },
    { "token_id": "C_L2B", "text": "裝作沒聽見", "prob": 0.15, "is_eos": false },
    { "token_id": "C_L2C", "text": "拿起掃把防身", "prob": 0.09, "is_eos": false },
    { "token_id": "C_L2D", "text": "開始直播求援", "prob": 0.05, "is_eos": false }
  ],
  "cache_hit": true
}
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| game_status | GameStatus | 吃下 EOS 時為 `"ENDED"` |
| current_temperature | number | 依被吃 Token 機率動態計算 |
| snake_speed_multiplier | number | 依 temperature 衍生（`1.0 + temperature × 0.17`） |
| next_tokens_food | TokenFood[] | 下一輪 4 組候選；EOS 時為空陣列 |
| cache_hit | boolean | 本次是否命中 Branch Cache |

**錯誤回應**

| 狀態碼 | 條件 | Response Body 範例 |
|--------|------|-------------------|
| 404 | session_id 無效 | `{ "detail": "Session not found: ..." }` |
| 422 | eaten_token_id 無效 | `{ "detail": "Invalid token: ..." }` |

**副作用：**

1. 更新 Session：`current_prompt`（追加文字）、`snake_length`、`current_temperature`、`current_node_id`、`score`
2. 若 `game_status` 仍為 `PLAYING`，背景啟動 Prefetch Task，平行預載 4 個新分支至 Redis

**業務規則：**

- 吃下 `is_eos: true` 的 Token → `game_status: "ENDED"`，`next_tokens_food: []`
- `GAME_OVER`（撞牆）由前端本地處理，不透過此 API

---

## 5. Leaderboard API

### `POST /api/v1/leaderboard`

提交玩家結算成績至全域排行榜。

**Request Body**

```json
{
  "player_name": "PlayerA",
  "score": 215,
  "session_id": "fb6a8b12-9c34"
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| player_name | string | 是 | 1–32 字元 |
| score | integer | 是 | ≥ 0 |
| session_id | string | 是 | 對應遊戲 Session |

**Response 204** — 無 Response Body

---

### `GET /api/v1/leaderboard`

取得分數最高的 Top 100 筆紀錄。

**Response 200**

```json
{
  "entries": [
    {
      "rank": 1,
      "player_name": "PlayerA",
      "score": 215,
      "session_id": "fb6a8b12-9c34"
    }
  ]
}
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| rank | integer | 排名（1 起算） |
| player_name | string | 玩家署名 |
| score | integer | 最終得分 |
| session_id | string | 遊戲 Session ID |

---

## 6. 端點總表

| Method | Endpoint | 說明 | 成功狀態碼 |
|--------|----------|------|------------|
| GET | `/health` | 健康檢查 | 200 |
| POST | `/api/v1/session` | 建立 Session | 201 |
| GET | `/api/v1/session/{session_id}` | 查詢 Session | 200 |
| POST | `/api/v1/game/step` | 執行玩家操作（吃 Token） | 200 |
| POST | `/api/v1/leaderboard` | 提交排行榜成績 | 204 |
| GET | `/api/v1/leaderboard` | 取得 Top 100 | 200 |

---

## 7. Redis 資料模型

| 用途 | 鍵格式 | 值格式 | TTL |
|------|--------|--------|-----|
| Player Session | `session:{session_id}` | JSON（見下表） | 1800s（30 分鐘） |
| Branch Cache | `prefetch:{session_id}:{eaten_token_id}` | `{ "next_tokens_food": [...] }` | 1800s（30 分鐘） |
| Leaderboard | `global:leaderboard` | ZSET，score = 分數 | 無 |

### 7.1 Session JSON 欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| session_id | string | Session ID |
| mode | GameMode | 遊戲模式 |
| model | ModelProfile | 模型風格 |
| game_status | GameStatus | 遊戲狀態 |
| current_prompt | string | 累積 Context 文本 |
| current_temperature | float | 動態溫度 |
| snake_length | int | 蛇身長度 |
| current_node_id | string \| null | 當前語料節點 |
| score | int | 累計得分 |
| updated_at | string | ISO 8601 時間戳 |

### 7.2 Leaderboard ZSET Member 格式

```
{player_name}|{session_id}
```

範例：`PlayerA|fb6a8b12-9c34`

---

## 8. 典型遊戲流程

```
1. POST /api/v1/session          → 取得 session_id + 初始 next_tokens_food
2. [前端] 玩家移動蛇吃下候選 Token
3. POST /api/v1/game/step        → 取得下一輪 next_tokens_food（cache_hit 標記）
4. 重複 2–3 直到 game_status = "ENDED"
5. POST /api/v1/leaderboard      → 提交結算成績
6. GET  /api/v1/leaderboard      → 顯示排行榜（選用）
```

---

## 9. 可觀測性（Structlog）

Step 相關請求輸出 JSON 結構化日誌，必含 `session_id` 與 `trace_id`。

| Event | 觸發時機 |
|-------|----------|
| `step_cache_hit` | Branch Cache 命中 |
| `step_cache_miss` | Branch Cache 未命中 |
| `fallback_mock_inference` | Fallback 使用 Mock LLM |
| `fallback_static_corpus` | Fallback 使用靜態安全語料 |
| `prefetch_completed` | 背景預載成功 |
| `prefetch_failed` | 背景預載失敗（不影響 Step 回應） |

---

## 10. 前端整合備註

前端透過環境變數 `VITE_API_BASE_URL` 啟用 API 模式（例：`http://localhost:8000`）。

| 前端模組 | 對應 API |
|----------|----------|
| `frontend/src/api/gameApi.ts` → `createSession()` | `POST /api/v1/session` |
| `frontend/src/api/gameApi.ts` → `postGameStep()` | `POST /api/v1/game/step` |
| `frontend/src/api/gameApi.ts` → `submitLeaderboard()` | `POST /api/v1/leaderboard` |

未設定 `VITE_API_BASE_URL` 時，前端維持 Phase 1 本地語料模式。

---

## 11. 變更紀錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 0.2.0 | 2026-06-25 | Phase 2 初版：Session / Step / Leaderboard / Health |
