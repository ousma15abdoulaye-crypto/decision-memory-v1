import { Sidebar } from "@/components/workspace/sidebar";

/** Même shell que le dashboard (navigation cohérente workspace ↔ liste). */
export default function WorkspacesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
