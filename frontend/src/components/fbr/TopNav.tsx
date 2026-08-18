import { Command, Cpu, KeyRound, ScrollText, Menu } from "lucide-react";
import { StatusPill } from "./StatusBits";
import { Button } from "@/components/ui/button";

export function TopNav({
  onOpenSearch,
  onToggleSidebar,
}: {
  onOpenSearch: () => void;
  onToggleSidebar: () => void;
}) {
  return (
    <header className="z-30 flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background/80 px-3 backdrop-blur-md md:px-4">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        aria-label="Toggle navigation"
        onClick={onToggleSidebar}
      >
        <Menu className="h-4 w-4" />
      </Button>

      <div className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-md border border-primary/30 bg-primary/10 text-primary">
          <ScrollText className="h-4 w-4" />
        </span>
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight">FBR Tax Copilot</div>
          <div className="text-data text-[10px] text-muted-foreground">
            AI Tax Engine &amp; Compliance Workstation
          </div>
        </div>
      </div>

      <div className="ml-2 hidden items-center gap-2 md:flex">
        <StatusPill label="API: 200 OK · v4.0.0" tone="primary" />
        <StatusPill label="Qwen 2.5 3B" tone="warning" />
      </div>

      <button
        onClick={onOpenSearch}
        className="ml-auto flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary md:h-9 md:w-72 md:justify-between md:px-3"
      >
        <span className="hidden items-center gap-2 text-xs md:flex">
          <Command className="h-3.5 w-3.5" />
          Search ordinance, acts, sessions
        </span>
        <Command className="h-4 w-4 md:hidden" />
        <kbd className="text-data hidden rounded border border-border px-1.5 py-0.5 text-[10px] md:inline">
          ⌘K
        </kbd>
      </button>

      <div className="hidden items-center gap-2 xl:flex">
        <div className="text-data flex items-center gap-2 rounded-md border border-border bg-surface px-2.5 py-1.5 text-[10px] text-muted-foreground">
          <Cpu className="h-3.5 w-3.5 text-primary" />
          <span>nomic-embed-text</span>
          <span className="text-border-strong">|</span>
          <span>3.4 GB VRAM</span>
        </div>
        <Button variant="outline" size="sm" className="gap-2">
          <KeyRound className="h-3.5 w-3.5" />
          API Keys
        </Button>
      </div>

      <div className="ml-1 flex items-center gap-2 rounded-md border border-border bg-surface px-2 py-1">
        <span className="text-data grid h-6 w-6 place-items-center rounded bg-primary/15 text-[10px] text-primary">
          BP
        </span>
        <span className="hidden text-xs text-muted-foreground sm:inline">
          Corporate Entity
        </span>
      </div>
    </header>
  );
}
