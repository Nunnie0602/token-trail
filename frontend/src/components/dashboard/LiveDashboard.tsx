import { LogitsChart } from "./LogitsChart";
import { TemperatureChart } from "./TemperatureChart";
import type { TokenFood } from "../../types/game";

type LiveDashboardProps = {
  tokens: TokenFood[];
  temperatureHistory: number[];
  apiLatencyMs?: number;
};

export function LiveDashboard({
  tokens,
  temperatureHistory,
  apiLatencyMs = 6,
}: LiveDashboardProps) {
  return (
    <aside className="live-dashboard">
      <LogitsChart tokens={tokens} />
      <TemperatureChart history={temperatureHistory} />
      <section className="health-block">
        <h3>PRODUCTION HEALTH</h3>
        <p>API Latency: {apiLatencyMs}ms</p>
        <p>App Status: NOMINAL</p>
      </section>
    </aside>
  );
}
