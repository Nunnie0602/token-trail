import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TemperatureChart } from "../../src/components/dashboard/TemperatureChart";

describe("TemperatureChart", () => {
  it("P1-T11: renders line chart for temperature history", () => {
    render(<TemperatureChart history={[1.0, 1.2, 0.9, 1.5]} />);
    expect(screen.getByTestId("temperature-chart")).toBeInTheDocument();
    expect(screen.getByText("TEMPERATURE TREND")).toBeInTheDocument();
  });
});
