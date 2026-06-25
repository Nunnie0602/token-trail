import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Header } from "../../src/components/layout/Header";

describe("Header", () => {
  it("P1-T13: displays context counter as 08/20", () => {
    render(
      <MemoryRouter>
        <Header
          score={215}
          contextLength={8}
          mode="classic"
          model="qwen"
        />
      </MemoryRouter>,
    );

    expect(screen.getByText(/CONTEXT: 08\/20/)).toBeInTheDocument();
  });
});
