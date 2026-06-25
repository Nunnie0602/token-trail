import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type TemperatureChartProps = {
  history: number[];
};

export function TemperatureChart({ history }: TemperatureChartProps) {
  const data = history.map((value, index) => ({
    step: index + 1,
    temperature: value,
  }));

  return (
    <div className="chart-block" data-testid="temperature-chart">
      <h3>TEMPERATURE TREND</h3>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0dc" />
          <XAxis dataKey="step" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 2]} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? value.toFixed(2) : String(value)
            }
          />
          <Line
            type="monotone"
            dataKey="temperature"
            stroke="#1a1a1a"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
