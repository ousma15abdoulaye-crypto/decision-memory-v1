import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { M16FrameApi } from "../model/useEvaluationFrame";
import { EvaluationMatrix } from "../ui/EvaluationMatrix";

function expectText(s: string) {
  expect(document.body.textContent).toContain(s);
}

describe("EvaluationMatrix", () => {
  const frame: M16FrameApi = {
    domains: [{ id: "d1", code: "technical", label: "Technique", display_order: 1 }],
    assessments: [
      {
        id: "a1",
        bundle_id: "b1",
        criterion_key: "Qualité",
        cell_json: { score: 8.5 },
        assessment_status: "draft",
        confidence: 0.85,
        signal: "green",
      },
    ],
    bundle_weighted_totals: { b1: 51.0 },
    weight_validation: { valid: true, weighted_sum: 100.0, errors: [] },
  };

  it("renders matrix with scores", async () => {
    render(
      <EvaluationMatrix
        workspaceId="ws1"
        data={frame}
        isLoading={false}
        error={null}
      />,
    );
    await waitFor(() => {
      expectText("Qualité");
      expectText("8.5");
    });
  });

  it("does not contain forbidden words", () => {
    const { container } = render(
      <EvaluationMatrix
        workspaceId="ws1"
        data={frame}
        isLoading={false}
        error={null}
      />,
    );
    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("winner");
    expect(text).not.toContain("gagnant");
    expect(text).not.toContain("classement");
    expect(text).not.toContain("recommandation");
  });

  it("clicking cell opens deliberation rail", async () => {
    const user = userEvent.setup();
    render(
      <EvaluationMatrix
        workspaceId="ws1"
        data={frame}
        isLoading={false}
        error={null}
      />,
    );
    await screen.findByText("8.5");
    await user.click(
      screen.getByRole("button", { name: /Cellule Qualité/i }),
    );
    await waitFor(() => {
      expect(document.querySelector('[role="dialog"]')).not.toBeNull();
    });
  });
});
