import { Navigate, useNavigate } from "react-router-dom";
import { useGame } from "../context/GameContext";
import { ResultOverlay } from "../components/result/ResultOverlay";
import { Header } from "../components/layout/Header";
import { Footer } from "../components/layout/Footer";
import { MAX_SNAKE_LENGTH } from "../engine/constants";

export function ResultPage() {
  const navigate = useNavigate();
  const { session, fpsStats, resetSession, startSession } = useGame();

  if (!session || session.status !== "ENDED") {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="game-layout">
      <Header
        score={session.score}
        contextLength={Math.min(session.contextTokens.length, MAX_SNAKE_LENGTH)}
        mode={session.mode}
        model={session.model}
      />
      <main className="result-page-main">
        <ResultOverlay
          session={session}
          onRetry={() => {
            const { mode, model } = session;
            resetSession();
            startSession(mode, model);
            navigate("/game", { state: { mode, model }, replace: true });
          }}
        />
      </main>
      <Footer fpsStats={fpsStats} model={session.model} />
    </div>
  );
}
