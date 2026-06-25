import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LogitsChart } from "../../src/components/dashboard/LogitsChart";

describe("LogitsChart", () => {
  it("P1-T10: renders four bars for top-4 tokens", () => {
    render(
      <LogitsChart
        tokens={[
          { token_id: "A", text: "聽見敲門", prob: 0.78 },
          { token_id: "B", text: "發現奏摺", prob: 0.11 },
          { token_id: "C", text: "撿到珍奶", prob: 0.05 },
          { token_id: "D", text: "看見鬼影", prob: 0.02 },
        ]}
      />,
    );

    expect(screen.getByTestId("logits-chart")).toBeInTheDocument();
    expect(screen.getByText("LOGITS DISTRIBUTION")).toBeInTheDocument();
  });
});
