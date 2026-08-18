import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { MessageSquare, Table2 } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";
import { TopNav } from "@/components/fbr/TopNav";
import { Sidebar, type NavKey } from "@/components/fbr/Sidebar";
import { CopilotChat } from "@/components/fbr/CopilotChat";
import { TaxMatrix } from "@/components/fbr/TaxMatrix";
import { InspectorPanel } from "@/components/fbr/InspectorPanel";
import { BottomDock } from "@/components/fbr/BottomDock";
import { CommandPalette } from "@/components/fbr/CommandPalette";
import type { Citation } from "@/components/fbr/data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "FBR Tax Copilot — AI Tax Engine & Compliance Workstation" },
      {
        name: "description",
        content:
          "AI copilot for Pakistan tax compliance: statutory RAG search over the Income Tax Ordinance 2001, withholding calculators, slab analysis and payment webhook sandbox.",
      },
      {
        property: "og:title",
        content: "FBR Tax Copilot — AI Tax Engine & Compliance Workstation",
      },
      {
        property: "og:description",
        content:
          "Statutory RAG search, live tax slab computation and payment sandbox in one dark-mode compliance workstation.",
      },
    ],
  }),
  component: Workstation,
});

const TABS = [
  { key: "chat", label: "AI Tax Copilot", icon: MessageSquare },
  { key: "matrix", label: "Tax Calculation Matrix", icon: Table2 },
] as const;

function Workstation() {
  const [nav, setNav] = useState<NavKey>("copilot");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tab, setTab] = useState<"chat" | "matrix">("chat");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [searching, setSearching] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (nav === "calculator") setTab("matrix");
    if (nav === "copilot" || nav === "rag") setTab("chat");
  }, [nav]);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background grid-noise">
      <TopNav
        onOpenSearch={() => setPaletteOpen(true)}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
      />

      <div className="relative flex min-h-0 flex-1">
        <Sidebar active={nav} onSelect={(k) => { setNav(k); setSidebarOpen(false); }} open={sidebarOpen} />
        {sidebarOpen && (
          <div
            className="absolute inset-0 z-10 bg-background/60 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <main className="relative flex min-w-0 flex-1 flex-col">
          <div className="relative flex items-center gap-3 border-b border-border px-4 py-2.5">
            {searching && (
              <span className="pointer-events-none absolute inset-x-0 top-0 h-px overflow-hidden">
                <span className="block h-px w-1/3 animate-beam bg-primary shadow-[var(--glow-primary)]" />
              </span>
            )}

            <div className="flex rounded-md border border-border bg-surface p-1">
              {TABS.map((t) => {
                const Icon = t.icon;
                const active = tab === t.key;
                return (
                  <button
                    key={t.key}
                    onClick={() => setTab(t.key)}
                    className={cn(
                      "flex items-center gap-2 rounded px-3 py-1.5 text-xs transition-all",
                      active
                        ? "bg-background text-primary shadow-[var(--glow-primary-soft)]"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {t.label}
                  </button>
                );
              })}
            </div>

            <span className="text-data ml-auto hidden text-[10px] text-muted-foreground sm:block">
              {searching ? "Querying ChromaDB vectors…" : "Context: 1,586 chunks indexed"}
            </span>
          </div>

          {tab === "chat" ? (
            <CopilotChat onCitations={setCitations} onSearching={setSearching} />
          ) : (
            <TaxMatrix />
          )}
        </main>

        <InspectorPanel citations={citations} />
      </div>

      <BottomDock />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
      <Toaster position="bottom-right" />
    </div>
  );
}
