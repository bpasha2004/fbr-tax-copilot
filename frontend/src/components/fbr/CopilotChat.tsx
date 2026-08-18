import { useEffect, useRef, useState } from "react";
import { ArrowUp, Copy, Sparkles, Trash2, User } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { CITATIONS, type Citation } from "./data";

type Msg = {
  id: string;
  role: "user" | "copilot";
  text: string;
  formula?: { title: string; expr: string };
  citations?: Citation[];
};

const PILLS = [
  { emoji: "⚡", label: "Calculate Section 153 WHT" },
  { emoji: "📜", label: "Income Tax Ordinance 2001 Slices" },
  { emoji: "💰", label: "Salary Tax Slabs FY2025-26" },
];

const ANSWER = `Under **Section 153(1)(b)** of the Income Tax Ordinance, 2001, every prescribed person must deduct withholding tax at the time of payment for services rendered.

- Company (filer) rendering services: **9%** of gross amount
- Individual / AOP (filer): **11%** of gross amount
- Non-filer: rate is **doubled** under the Tenth Schedule

| Payee type | Filer | Non-filer |
| Company | 9% | 18% |
| Individual / AOP | 11% | 22% |
| Transport services | 3% | 6% |

The deduction is a minimum tax for most service providers, so it is not adjustable against a lower final liability.`;

const INITIAL: Msg[] = [
  {
    id: "m0",
    role: "copilot",
    text: "Statutory index loaded — 1,586 chunks across Income Tax Ordinance 2001, Sales Tax Act 1990 and Finance Act 2025. Ask a question or run a quick action below.",
  },
];

export function CopilotChat({
  onCitations,
  onSearching,
}: {
  onCitations: (c: Citation[]) => void;
  onSearching: (v: boolean) => void;
}) {
  const [messages, setMessages] = useState<Msg[]>(INITIAL);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({
      top: scroller.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, streamText]);

  function send(question: string) {
    if (!question.trim() || streaming) return;
    setInput("");
    setMessages((m) => [
      ...m,
      { id: crypto.randomUUID(), role: "user", text: question },
    ]);
    setStreaming(true);
    onSearching(true);
    setStreamText("");

    window.setTimeout(() => {
      onSearching(false);
      onCitations(CITATIONS);
      let i = 0;
      const timer = window.setInterval(() => {
        i += 4;
        setStreamText(ANSWER.slice(0, i));
        if (i >= ANSWER.length) {
          window.clearInterval(timer);
          setStreaming(false);
          setStreamText("");
          setMessages((m) => [
            ...m,
            {
              id: crypto.randomUUID(),
              role: "copilot",
              text: ANSWER,
              formula: {
                title: "Withholding tax on services",
                expr: "WHT = Gross Amount × Rate(payee_type, filer_status)",
              },
              citations: CITATIONS.slice(0, 2),
            },
          ]);
        }
      }, 16);
    }, 900);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={scroller} className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4 md:p-6">
        {messages.map((m) => (
          <Bubble key={m.id} msg={m} />
        ))}
        {streaming && (
          <Bubble
            msg={{ id: "stream", role: "copilot", text: streamText }}
            typing
          />
        )}
      </div>

      <div className="border-t border-border p-3 md:p-4">
        <div className="mb-2 flex flex-wrap gap-2">
          {PILLS.map((p) => (
            <button
              key={p.label}
              onClick={() => send(p.label)}
              className="glass rounded-full px-3 py-1.5 text-xs text-muted-foreground transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:text-primary"
            >
              <span className="mr-1.5">{p.emoji}</span>
              {p.label}
            </button>
          ))}
        </div>

        <div className="glass flex items-end gap-2 rounded-xl p-2 shadow-[var(--shadow-panel)] focus-within:border-primary/50">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={2}
            placeholder="Ask about WHT rates, slab computation, exemptions, audit exposure…"
            className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-muted-foreground"
          />
          <Button
            variant="ghost"
            size="icon"
            aria-label="Clear session"
            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
            onClick={() => {
              setMessages(INITIAL);
              onCitations([]);
              toast("Session cleared", { description: "Context window reset." });
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button
            size="icon"
            disabled={streaming}
            onClick={() => send(input)}
            aria-label="Send message"
            className="hover:shadow-[var(--glow-primary)]"
          >
            <ArrowUp className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function Bubble({ msg, typing }: { msg: Msg; typing?: boolean }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-3 animate-rise", isUser && "flex-row-reverse")}>
      <span
        className={cn(
          "mt-1 grid h-7 w-7 shrink-0 place-items-center rounded-md border",
          isUser
            ? "border-border bg-secondary text-muted-foreground"
            : "border-primary/30 bg-primary/10 text-primary",
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
      </span>

      <div
        className={cn(
          "max-w-[46rem] rounded-lg border px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "border-border border-r-2 border-r-primary bg-surface-raised"
            : "border-border bg-surface",
        )}
      >
        <Markdown text={msg.text} />
        {typing && (
          <span className="text-data ml-0.5 inline-block animate-blip text-primary">▍</span>
        )}

        {msg.formula && (
          <div className="mt-3 rounded-md border border-border bg-background/70 p-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="text-data text-[10px] uppercase tracking-widest text-muted-foreground">
                {msg.formula.title}
              </span>
              <button
                onClick={() => {
                  navigator.clipboard?.writeText(msg.formula!.expr);
                  toast.success("Formula copied");
                }}
                className="text-data inline-flex items-center gap-1.5 rounded border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
              >
                <Copy className="h-3 w-3" /> Copy formula
              </button>
            </div>
            <code className="text-data block text-xs text-primary">
              {msg.formula.expr}
            </code>
          </div>
        )}

        {msg.citations && msg.citations.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {msg.citations.map((c) => (
              <span
                key={c.id}
                className="text-data rounded border border-warning/30 bg-warning/10 px-2 py-0.5 text-[10px] text-warning"
              >
                {c.section} · {c.score}%
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function inline(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i} className="font-semibold text-primary">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const out: React.ReactNode[] = [];
  let table: string[][] = [];

  const flushTable = (key: string) => {
    if (!table.length) return;
    const [head, ...rows] = table;
    if (!head) return;
    out.push(
      <div key={key} className="my-3 overflow-hidden rounded-md border border-border">
        <table className="w-full text-xs">
          <thead className="bg-secondary/60">
            <tr>
              {head.map((h, i) => (
                <th
                  key={i}
                  className="px-3 py-2 text-left font-medium text-muted-foreground"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, ri) => (
              <tr key={ri} className="border-t border-border">
                {r.map((c, ci) => (
                  <td key={ci} className={cn("px-3 py-2", ci > 0 && "text-data")}>
                    {c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>,
    );
    table = [];
  };

  lines.forEach((line, idx) => {
    const t = line.trim();
    if (t.startsWith("|")) {
      table.push(
        t
          .split("|")
          .slice(1, -1)
          .map((c) => c.trim()),
      );
      return;
    }
    flushTable(`t${idx}`);
    if (!t) return;
    if (t.startsWith("- ")) {
      out.push(
        <div key={idx} className="flex gap-2 py-0.5">
          <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary" />
          <span>{inline(t.slice(2))}</span>
        </div>,
      );
      return;
    }
    out.push(
      <p key={idx} className="py-0.5">
        {inline(t)}
      </p>,
    );
  });
  flushTable("t-end");

  return <>{out}</>;
}
