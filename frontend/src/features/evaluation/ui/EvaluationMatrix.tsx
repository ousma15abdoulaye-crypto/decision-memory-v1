import { useMemo, useState } from "react";

import type { M16FrameApi } from "../model/useEvaluationFrame";
import { DeliberationRail } from "../../committee/ui/DeliberationRail";
import { WeightValidationBanner } from "../../../shared/ui/weight-validation-banner";

type Props = {
  workspaceId: string;
  data: M16FrameApi | undefined;
  isLoading: boolean;
  error: Error | null;
  onRetry?: () => void;
};

function scoreFromCell(cell: Record<string, unknown>): string {
  const v = cell.score ?? cell.numeric_score ?? cell.value;
  if (v === undefined || v === null) return "—";
  return String(v);
}

export function EvaluationMatrix({
  workspaceId,
  data,
  isLoading,
  error,
  onRetry,
}: Props) {
  const [railOpen, setRailOpen] = useState(false);

  const firstCell = useMemo(() => {
    if (!data?.assessments?.length) return null;
    const a = data.assessments[0];
    const label = a.criterion_key || "critère";
    const score = scoreFromCell(a.cell_json || {});
    const supplier = a.bundle_id.slice(0, 8);
    return { label, score, supplier };
  }, [data]);

  if (isLoading) {
    return <div role="status">Chargement du cadre…</div>;
  }
  if (error) {
    return (
      <div role="alert">
        Erreur de chargement.
        {onRetry ? (
          <button type="button" onClick={onRetry}>
            Réessayer
          </button>
        ) : null}
      </div>
    );
  }
  if (!firstCell) {
    return <div>Aucune donnée.</div>;
  }

  return (
    <div>
      <WeightValidationBanner validation={data?.weight_validation} />
      <table>
        <tbody>
          <tr>
            <th scope="row">{firstCell.label}</th>
            <td>
              <button
                type="button"
                role="button"
                tabIndex={0}
                aria-label={`Cellule ${firstCell.label} ${firstCell.supplier}`}
                onClick={() => setRailOpen(true)}
              >
                {firstCell.score}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      {railOpen ? (
        <DeliberationRail workspaceId={workspaceId} onClose={() => setRailOpen(false)} />
      ) : null}
    </div>
  );
}
