type Props = { onSend: (body: string) => void };

export function MessageComposer({ onSend }: Props) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const fd = new FormData(e.currentTarget);
        onSend(String(fd.get("body") ?? ""));
      }}
    >
      <label htmlFor="msg">Message</label>
      <textarea id="msg" name="body" required />
      <button type="submit">Envoyer</button>
    </form>
  );
}
