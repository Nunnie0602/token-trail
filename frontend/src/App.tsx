import { useEffect, useState } from "react";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type HealthResponse = {
  status: string;
  service: string;
  redis: boolean;
};

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${apiBaseUrl}/health`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json() as Promise<HealthResponse>;
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <main className="app">
      <header>
        <p className="brand">nc_</p>
        <h1>Token Trail</h1>
        <p className="subtitle">Visualizing LLM Decoding Through Interactive Gameplay</p>
      </header>

      <section className="status-card">
        <h2>系統狀態</h2>
        {health && (
          <ul>
            <li>API: {health.status}</li>
            <li>Redis: {health.redis ? "connected" : "disconnected"}</li>
          </ul>
        )}
        {error && <p className="error">無法連線至後端 ({error})</p>}
        {!health && !error && <p>檢查後端連線中…</p>}
      </section>

      <footer>
        <span>Phase 1 Frontend MVP — 建置中</span>
      </footer>
    </main>
  );
}
