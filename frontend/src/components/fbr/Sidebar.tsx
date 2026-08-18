import {
  BookOpen,
  Calculator,
  CreditCard,
  LayoutDashboard,
  ShieldCheck,
  Sparkles,
  Terminal,
  ChevronsUpDown,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type NavKey =
  | "dashboard"
  | "copilot"
  | "rag"
  | "calculator"
  | "audit"
  | "payments"
  | "logs";

const ITEMS: { key: NavKey; label: string; icon: typeof Sparkles; badge?: string }[] =
  [
    { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { key: "copilot", label: "Copilot Chat", icon: Sparkles, badge: "LIVE" },
    { key: "rag", label: "Statutory RAG Search", icon: BookOpen },
    { key: "calculator", label: "Income & WHT Calculator", icon: Calculator },
    { key: "audit", label: "Audit & Compliance", icon: ShieldCheck, badge: "3" },
    { key: "payments", label: "Payment Sandbox", icon: CreditCard },
    { key: "logs", label: "System Logs", icon: Terminal },
  ];

export function Sidebar({
  active,
  onSelect,
  open,
}: {
  active: NavKey;
  onSelect: (k: NavKey) => void;
  open: boolean;
}) {
  return (
    <aside
      className={cn(
        "absolute inset-y-0 left-0 z-20 flex w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-transform duration-300 lg:static lg:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full",
      )}
    >
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        <div className="text-data px-2 pb-2 text-[10px] uppercase tracking-widest text-muted-foreground">
          Tax Workflows
        </div>
        {ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.key;
          return (
            <button
              key={item.key}
              onClick={() => onSelect(item.key)}
              className={cn(
                "group relative flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-all",
                isActive
                  ? "bg-primary/10 text-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent hover:text-foreground",
              )}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 h-6 w-0.5 -translate-y-1/2 rounded-r bg-primary shadow-[var(--glow-primary)]" />
              )}
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0",
                  isActive ? "text-primary" : "text-muted-foreground",
                )}
              />
              <span className="truncate text-left">{item.label}</span>
              {item.badge && (
                <span
                  className={cn(
                    "text-data ml-auto rounded border px-1.5 py-0.5 text-[9px]",
                    item.badge === "LIVE"
                      ? "border-primary/30 bg-primary/10 text-primary"
                      : "border-warning/30 bg-warning/10 text-warning",
                  )}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <button className="panel flex w-full items-center gap-3 px-3 py-2.5 text-left transition-transform hover:-translate-y-0.5">
          <span className="text-data grid h-8 w-8 place-items-center rounded bg-primary/15 text-xs text-primary">
            BP
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-xs font-medium">Bilal Pasha</span>
            <span className="text-data block truncate text-[10px] text-muted-foreground">
              NTN 4210198-7 · Corporate
            </span>
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </div>
    </aside>
  );
}
