import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TokenFood } from "../../types/game";

type LogitsChartProps = {
  tokens: TokenFood[];
};

export function LogitsChart({ tokens }: LogitsChartProps) {
  const data = tokens.map((token) => ({
    name: token.text.length > 8 ? `${token.text.slice(0, 7)}…` : token.text,
    prob: token.prob,
    fullText: token.text,
  }));

  if (data.length === 0) {
    return <p className="chart-empty">等待下一輪候選 Token…</p>;
  }

  return (
    <div className="chart-block" data-testid="logits-chart">
      <h3>LOGITS DISTRIBUTION</h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0dc" />
          <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" width={72} tick={{ fontSize: 10 }} />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? value.toFixed(2) : String(value)
            }
            labelFormatter={(_, payload) =>
              payload?.[0]?.payload?.fullText ?? ""
            }
          />
          <Bar dataKey="prob" fill="#1a1a1a" barSize={14} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
