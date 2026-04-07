type Props = { workspaceId: string; onClose: () => void };

export function DeliberationRail({ workspaceId, onClose }: Props) {
  return (
    <aside role="dialog" aria-label="Délibération">
      <button type="button" onClick={onClose} aria-label="Fermer">
        ×
      </button>
      <h2>Délibération</h2>
      <p>Workspace {workspaceId}</p>
    </aside>
  );
}
