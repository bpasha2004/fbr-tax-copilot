import { useState } from "react";
import { FileText, Radar, Zap } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { Citation } from "./data";

function ConfidenceGauge({ value }: { value: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative grid h-24 w-24 place-items-center">
      <svg className="h-24 w-24 -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={r} className="fill-none stroke-border" strokeWidth="6" />
        <circle
          cx="40"
          cy="40"
          r={r}
          className="fill-none stroke-primary transition-all duration-700"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c - (c * value) / 100}
        />
      </svg>
      <span className="text-data absolute text-sm text-primary">{value.toFixed(1)}%</span>
    </div>
  );
}

const GATEWAYS = ["JazzCash", "EasyPaisa", "Raast"] as const;

export function InspectorPanel({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState<Citation | null>(null);
  const [gateway, setGateway] = useState<(typeof GATEWAYS)[number]>("JazzCash");
  const [txn, setTxn] = useState("TXN-2026-88431");
  const [amount, setAmount] = useState("184500");
  const [callback, setCallback] = useState("https://fbr.local/api/hooks/psp");
  const [state, setState] = useState<"idle" | "sending" | "ok">("idle");

  const top = citations[0];

  function simulate() {
    setState("sending");
    window.setTimeout(() => {
      setState("ok");
      toast.success("200 OK · Webhook delivered", {
        description: `${gateway} · ${txn} · PKR ${Number(amount).toLocaleString()}`,
      });
      window.setTimeout(() => setState("idle"), 2400);
    }, 1100);
  }

  return (
    <aside className="hidden w-[22rem] shrink-0 flex-col gap-4 overflow-y-auto border-l border-border bg-sidebar p-4 xl:flex">
      <section>
        <div className="mb-3 flex items-center gap-2">
          <Radar className="h-3.5 w-3.5 text-primary" />
          <h3 className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Statutory Provenance
          </h3>
        </div>

        {top ? (
          <div className="panel flex items-center gap-4 p-3">
            <ConfidenceGauge value={top.score} />
            <div className="min-w-0 text-xs">
              <div className="text-muted-foreground">Vector similarity</div>
              <div className="text-data mt-1 text-foreground">{top.section}</div>
              <div className="text-data mt-1 text-[10px] text-muted-foreground">
                cosine · nomic-embed-text
              </div>
            </div>
          </div>
        ) : (
          <div className="panel p-4 text-xs text-muted-foreground">
            No retrieval yet. Ask the copilot a question to populate cited ordinance
            sections.
          </div>
        )}

        <div className="mt-3 space-y-2">
          {citations.map((c) => (
            <button
              key={c.id}
              onClick={() => setOpen(c)}
              className="panel group w-full p-3 text-left transition-transform hover:-translate-y-0.5 hover:border-primary/40"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-data text-[11px] text-primary">{c.section}</span>
                <span className="text-data rounded border border-warning/30 bg-warning/10 px-1.5 py-0.5 text-[9px] text-warning">
                  {c.score}%
                </span>
              </div>
              <div className="mt-1 line-clamp-2 text-xs text-foreground/90">{c.title}</div>
              <div className="text-data mt-1 text-[10px] text-muted-foreground">{c.act}</div>
            </button>
          ))}
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center gap-2">
          <Zap className="h-3.5 w-3.5 text-warning" />
          <h3 className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Payment Sandbox
          </h3>
        </div>

        <div className="panel space-y-3 p-3">
          <div className="grid grid-cols-3 gap-2">
            {GATEWAYS.map((g) => (
              <button
                key={g}
                onClick={() => setGateway(g)}
                className={cn(
                  "rounded-md border px-2 py-2 text-[11px] transition-all",
                  gateway === g
                    ? "border-primary/50 bg-primary/10 text-primary shadow-[var(--glow-primary-soft)]"
                    : "border-border bg-background text-muted-foreground hover:border-border-strong",
                )}
              >
                {g}
              </button>
            ))}
          </div>

          <SandboxInput label="Transaction ID" value={txn} onChange={setTxn} />
          <SandboxInput label="Amount (PKR)" value={amount} onChange={setAmount} />
          <SandboxInput label="Callback URL" value={callback} onChange={setCallback} />

          <Button
            onClick={simulate}
            disabled={state === "sending"}
            className={cn(
              "w-full transition-all active:scale-[0.98]",
              state === "ok"
                ? "bg-primary shadow-[var(--glow-primary)]"
                : "hover:shadow-[var(--glow-primary)]",
            )}
          >
            {state === "sending"
              ? "Dispatching hook…"
              : state === "ok"
                ? "200 OK · Webhook Delivered"
                : "Simulate Instant Payment Hook"}
          </Button>

          <pre className="text-data overflow-x-auto rounded-md border border-border bg-background p-2 text-[10px] text-muted-foreground">
{`POST ${callback}
{ "gateway": "${gateway.toLowerCase()}",
  "txn_id": "${txn}",
  "amount": ${Number(amount) || 0},
  "status": "${state === "ok" ? "captured" : "pending"}" }`}
          </pre>
        </div>
      </section>

      <Sheet open={!!open} onOpenChange={(v) => !v && setOpen(null)}>
        <SheetContent className="glass w-full sm:max-w-lg">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2 text-sm">
              <FileText className="h-4 w-4 text-primary" />
              {open?.section}
            </SheetTitle>
          </SheetHeader>
          {open && (
            <div className="space-y-3 overflow-y-auto px-4 pb-6 text-sm">
              <div className="text-data text-[10px] uppercase tracking-widest text-muted-foreground">
                {open.act} · chunk match {open.score}%
              </div>
              <div className="panel bg-background/60 p-4 leading-relaxed text-foreground/90">
                {open.chunk.split(open.highlight).map((part, i, arr) => (
                  <span key={i}>
                    {part}
                    {i < arr.length - 1 && (
                      <mark className="rounded bg-primary/25 px-0.5 text-primary">
                        {open.highlight}
                      </mark>
                    )}
                  </span>
                ))}
              </div>
              <div className="text-xs text-muted-foreground">{open.title}</div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </aside>
  );
}

function SandboxInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-data block text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-data mt-1 w-full rounded-md border border-border bg-background px-2.5 py-2 text-xs outline-none transition-colors focus:border-primary/50"
      />
    </label>
  );
}
