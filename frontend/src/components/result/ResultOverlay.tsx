import { useCallback, useState, type ChangeEvent } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { isApiEnabled } from "../../api/client";
import { submitLeaderboard } from "../../api/gameApi";
import {
  generateDefaultPlayerName,
  PLAYER_NAME_MAX_LENGTH,
  sanitizePlayerName,
} from "../../utils/playerName";
import { buildStoryText } from "../../utils/storyBuilder";
import type { GameSession } from "../../types/game";

type ResultOverlayProps = {
  session: GameSession;
  onRetry?: () => void;
};

export function ResultOverlay({ session, onRetry }: ResultOverlayProps) {
  const story = buildStoryText(session.storyPath) || "故事尚未生成。";

  const [playerName, setPlayerName] = useState(() => generateDefaultPlayerName());
  const [submitStatus, setSubmitStatus] = useState<"idle" | "submitted">("idle");

  const handleNameChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      setPlayerName(sanitizePlayerName(event.target.value));
      setSubmitStatus("idle");
    },
    [],
  );

  const handleSubmitLeaderboard = useCallback(async () => {
    if (isApiEnabled()) {
      await submitLeaderboard(playerName, session.score, session.sessionId);
      setSubmitStatus("submitted");
      return;
    }

    const entry = {
      name: playerName,
      score: session.score,
      sessionId: session.sessionId,
      submittedAt: new Date().toISOString(),
    };
    const existing = JSON.parse(
      localStorage.getItem("token-trail-leaderboard") ?? "[]",
    ) as typeof entry[];
    existing.push(entry);
    localStorage.setItem("token-trail-leaderboard", JSON.stringify(existing));
    setSubmitStatus("submitted");
  }, [playerName, session.score, session.sessionId]);

  return createPortal(
    <div
      className="result-overlay"
      data-testid="result-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="結算畫面"
    >
      <div className="result-panel">
        <p className="result-eyebrow">TECHNICAL STORY</p>
        <p className="result-story">&ldquo;{story}&rdquo;</p>
        <hr />

        <div className="result-signature">
          <label htmlFor="player-name">署名</label>
          <input
            id="player-name"
            type="text"
            className="result-name-input"
            value={playerName}
            maxLength={PLAYER_NAME_MAX_LENGTH}
            onChange={handleNameChange}
            data-testid="player-name-input"
          />
          <div className="result-leaderboard-actions">
            <button
              type="button"
              className="result-submit-btn"
              onClick={handleSubmitLeaderboard}
              disabled={!playerName || submitStatus === "submitted"}
              data-testid="submit-leaderboard-btn"
            >
              {submitStatus === "submitted" ? "SUBMITTED" : "SUBMIT TO ZSET"}
            </button>
            <button
              type="button"
              className="result-share-btn"
              disabled
              title="Phase 4：LinkedIn 分享 API 尚未串接"
              data-testid="share-linkedin-btn"
            >
              SHARE TO LINKEDIN
            </button>
          </div>
        </div>

        <div className="result-actions">
          {onRetry && (
            <button type="button" onClick={onRetry}>
              再玩一局
            </button>
          )}
          <Link to="/" className="button-link">
            返回首頁
          </Link>
        </div>
      </div>
    </div>,
    document.body,
  );
}
