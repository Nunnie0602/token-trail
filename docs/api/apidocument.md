# Token Trail API 文件

> 版本：0.3.1 | 對照 PRD §7.1 | Phase 2.5 結算與防作弊  
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
type GameStatus = "PLAYING" | "ENDED" | "COLLISION_FAILED" | "ABORTED";
type TerminalGameStatus = "ENDED" | "COLLISION_FAILED" | "ABORTED";
type GameCompletionType = "eos" | "collision" | "voluntary_exit" | "api_error";
type ModelProfile = "qwen" | "gemini";

type TokenFood = {
  token_id: string;
  text: string;
  prob: number;       // 0.0 ~ 1.0
  is_eos?: boolean;   // 預設 false
};

type StepRecord = {
  step_index: number;   // 1-based，與 snake_length 對齊
  token_id: string;
  text: string;
  prob: number;
  temperature: number;
  is_eos: boolean;
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

1. 更新 Session：`current_prompt`、`snake_length`、`current_temperature`、`current_node_id`、`score`
2. **append** `StepRecord` 至 `step_history`（伺服器權威決策序列）
3. `score += round(prob × 100)`（唯一計分規則）
4. 吃下 EOS 時自動寫入 `result:{session_id}`（自包含結算，TTL 7 天）
5. 若 `game_status` 仍為 `PLAYING`，背景啟動 Prefetch Task

**業務規則：**

- 吃下 `is_eos: true` 的 Token → `game_status: "ENDED"`，`next_tokens_food: []`，同步產生 `GameResult`
- 碰撞（`COLLISION_FAILED`）由前端呼叫 `POST /game/finalize` 觸發結算
- StepResponse **不回傳** `score`；GET Session **不暴露** `score`

---

## 5. Finalize & Result API

### `POST /api/v1/game/finalize`

非 EOS 或需明確確認的終局情境觸發結算。**僅接受**結束原因，不接受客戶端 `story_path` / `score` 等可偽造欄位（多餘欄位 → 422）。

**Request Body**

```json
{
  "session_id": "fb6a8b12-9c34",
  "completion_type": "collision",
  "failure_reason": "collision"
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| session_id | string | 是 | Session ID |
| completion_type | GameCompletionType | 是 | `eos` / `collision` / `voluntary_exit` / `api_error` |
| failure_reason | string | 否 | `ABORTED` 時區分 `voluntary_exit` / `tab_closed` / `api_error` |

**Response 201** — `GameResult`（見 §7.3）

**Response 204** — `voluntary_exit` 且 `snake_length < 3`：銷毀 Session，不產生 Result

**錯誤回應**

| 狀態碼 | 條件 |
|--------|------|
| 404 | Session 不存在 |
| 409 | Session 已處於不可 finalize 的終局狀態 |
| 422 | 無效 completion_type 或含禁止欄位 |

---

### `GET /api/v1/game/result/{session_id}`

讀取自包含結算資料。Session 過期後仍可查詢（7 天內）。

**Response 200** — `GameResult`

**Response 404** — Result 不存在或已過期

---

## 6. Leaderboard API

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
| score | integer | 是 | ≥ 0，**已棄用**：後端忽略，改讀 `GameResult.score` |
| session_id | string | 是 | 對應遊戲 Session |

**資格門檻：** 僅 `completion_type === "eos"` 且 `result:{session_id}` 存在時可提交。

**Response 204** — 無 Response Body

**錯誤回應**

| 狀態碼 | 條件 |
|--------|------|
| 404 | Result 不存在 |
| 409 | 非 EOS 完賽（如 collision） |

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

## 7. 端點總表

| Method | Endpoint | 說明 | 成功狀態碼 |
|--------|----------|------|------------|
| GET | `/health` | 健康檢查 | 200 |
| POST | `/api/v1/session` | 建立 Session | 201 |
| GET | `/api/v1/session/{session_id}` | 查詢 Session | 200 |
| POST | `/api/v1/game/step` | 執行玩家操作（吃 Token） | 200 |
| POST | `/api/v1/game/finalize` | 觸發結算（非 EOS / 棄賽） | 201 / 204 |
| GET | `/api/v1/game/result/{session_id}` | 讀取結算 Result | 200 |
| POST | `/api/v1/leaderboard` | 提交排行榜成績（僅 EOS） | 204 |
| GET | `/api/v1/leaderboard` | 取得 Top 100 | 200 |

---

## 8. Redis 資料模型

| 用途 | 鍵格式 | 值格式 | TTL |
|------|--------|--------|-----|
| Player Session | `session:{session_id}` | JSON（見 §8.1） | 1800s（30 分鐘） |
| Game Result | `result:{session_id}` | JSON（見 §8.3） | 604800s（7 天） |
| Branch Cache | `prefetch:{session_id}:{eaten_token_id}` | `{ "next_tokens_food": [...] }` | 1800s（30 分鐘） |
| Leaderboard | `global:leaderboard` | ZSET，score = 伺服器權威分數 | 無 |

### 8.1 Session JSON 欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| session_id | string | Session ID |
| mode | GameMode | 遊戲模式 |
| model | ModelProfile | 模型風格 |
| game_status | GameStatus | `PLAYING` / `ENDED` / `COLLISION_FAILED` / `ABORTED` |
| current_prompt | string | 累積 Context 文本 |
| current_temperature | float | 動態溫度 |
| snake_length | int | 蛇身長度 |
| current_node_id | string \| null | 當前語料節點 |
| score | int | 伺服器權威累計得分 |
| step_history | StepRecord[] | 每步決策紀錄 |
| updated_at | string | ISO 8601 時間戳 |

> GET Session 回應**不含** `score` 與 `step_history`（防窺探／防篡改）。

### 8.2 Leaderboard ZSET Member 格式

```
{player_name}|{session_id}
```

範例：`PlayerA|fb6a8b12-9c34`

### 8.3 GameResult JSON 欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| session_id | string | Session ID |
| terminal_game_status | TerminalGameStatus | 精準終局狀態 |
| completion_type | GameCompletionType | 分析用歸類 |
| failure_reason | string \| null | 失敗原因（選填） |
| mode | GameMode | 遊戲模式 |
| model | ModelProfile | 模型風格 |
| score | int | 取自 Session，伺服器權威 |
| snake_length | int | 終局蛇身長度 |
| story_path | string[] | 由 `step_history[].text` 衍生 |
| chosen_probs | number[] | 由 `step_history[].prob` 衍生 |
| temperature_history | number[] | 由 `step_history[].temperature` 衍生 |
| step_history | StepRecord[] | 完整逐步紀錄 |
| personality_type | string | Personality Decoder 類型 |
| personality_description | string | 解碼描述 |
| created_at | string | ISO 8601 |

---

## 9. 典型遊戲流程

**EOS 完賽：**

```
1. POST /api/v1/session
2. POST /api/v1/game/step（重複至 game_status = "ENDED"）
3. GET  /api/v1/game/result/{session_id}   → 結算頁
4. POST /api/v1/leaderboard                → 僅 EOS 可提交
```

**碰撞失敗：**

```
1–2. 同上（至撞牆）
3. POST /api/v1/game/finalize { completion_type: "collision" }
4. GET  /api/v1/game/result/{session_id}   → 展示解碼報告，不可上榜
```

**主動離場（F2）／分頁關閉（F3）：**

```
completion_type: "voluntary_exit"
failure_reason: "voluntary_exit" | "tab_closed"
```

| 情境 | 前端觸發 | 門檻 |
|------|----------|------|
| SPA 導離 `/game` | `finalizeGame`（`useBlocker`） | `snake_length < 3` → 204，銷毀 Session |
| 分頁關閉 | `navigator.sendBeacon` → `POST /finalize` | 同上 |

**Step API 失敗（F4）：**

```
POST /api/v1/game/finalize { completion_type: "api_error", failure_reason: "api_error" }
```

後端唯讀既有 `step_history`（失敗前最後成功步），前端導向 `/result/:session_id`。

---

## 10. 可觀測性（Structlog）

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

## 11. 前端整合備註

前端透過環境變數 `VITE_API_BASE_URL` 啟用 API 模式（例：`http://localhost:8000`）。

| 前端模組 | 對應 API |
|----------|----------|
| `gameApi.ts` → `createSession()` | `POST /api/v1/session` |
| `gameApi.ts` → `postGameStep()` | `POST /api/v1/game/step` |
| `gameApi.ts` → `finalizeGame()` | `POST /api/v1/game/finalize` |
| `sessionFinalize.ts` → `sendFinalizeBeacon()` | `POST /api/v1/game/finalize`（Beacon） |
| `gameApi.ts` → `getResult()` | `GET /api/v1/game/result/{id}` |
| `gameApi.ts` → `submitLeaderboard()` | `POST /api/v1/leaderboard` |

結算頁路由：`/result/:sessionId`，API 模式以 `GET /game/result/{id}` 驅動 UI。

未設定 `VITE_API_BASE_URL` 時，前端維持 Phase 1 本地語料模式。

---

## 12. 變更紀錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 0.3.1 | 2026-07-01 | F2/F3 離場 Beacon finalize、F4 Step API 失敗 api_error 路徑 |
| 0.3.0 | 2026-07-01 | Phase 2.5：step_history、finalize/result、排行榜伺服器權威、非 EOS 結算 |
| 0.2.0 | 2026-06-25 | Phase 2 初版：Session / Step / Leaderboard / Health |
