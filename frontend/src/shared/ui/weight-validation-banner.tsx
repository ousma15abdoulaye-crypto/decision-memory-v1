type V = { valid: boolean; weighted_sum: number; errors: string[] } | undefined;

export function WeightValidationBanner({ validation }: { validation?: V }) {
  if (!validation) return null;
  if (validation.valid) {
    return (
      <div role="status" className="wv-ok">
        Poids pondérés : {validation.weighted_sum} %
      </div>
    );
  }
  return (
    <div role="alert" className="wv-err">
      {validation.errors.join(" ")}
    </div>
  );
}
