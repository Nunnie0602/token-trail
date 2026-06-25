import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { LandingPage } from "../../src/pages/LandingPage";

describe("LandingPage", () => {
  it("P1-T09: renders selectable mode buttons", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    const classicButton = screen.getByRole("button", { name: /經典模式/ });
    const qingButton = screen.getByRole("button", { name: /清代模式/ });

    expect(classicButton).toBeInTheDocument();
    expect(qingButton).toBeInTheDocument();

    await user.click(qingButton);
    expect(qingButton.className).toContain("active");
  });
});
