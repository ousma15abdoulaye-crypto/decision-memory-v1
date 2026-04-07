type Thread = { id: string; title: string };

export function ThreadList({ threads }: { threads: Thread[] }) {
  return (
    <ul>
      {threads.map((t) => (
        <li key={t.id}>{t.title}</li>
      ))}
    </ul>
  );
}
