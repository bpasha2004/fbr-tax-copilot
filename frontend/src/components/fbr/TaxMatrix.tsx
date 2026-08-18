import { useMemo, useState } from "react";
import { Sparkles, TrendingDown } from "lucide-react";
import { computeTax, PKR, SLABS } from "./data";
import { cn } from "@/lib/utils";

function Field({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  onChange: (n: number) => void;
}) {
  return (
    <label className="panel group block p-3 transition-all focus-within:border-primary/50 focus-within:shadow-[var(--glow-primary-soft)] hover:-translate-y-0.5">
      <span className="text-data block text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <span className="mt-2 flex items-baseline gap-2">
        <span className="text-data text-xs text-muted-foreground">PKR</span>
        <input
          type="number"
          value={value}
          min={0}
          onChange={(e) => onChange(Number(e.target.value) || 0)}
          className="text-data w-full bg-transparent text-lg outline-none"
        />
      </span>
      <span className="mt-1 block text-[10px] text-muted-foreground">{hint}</span>
    </label>
  );
}

export function TaxMatrix() {
  const [salary, setSalary] = useState(4_800_000);
  const [business, setBusiness] = useState(1_200_000);
  const [exemptions, setExemptions] = useState(300_000);
  const [allowance, setAllowance] = useState(240_000);
  const [wht, setWht] = useState(520_000);

  const taxable = Math.max(0, salary + business - exemptions - allowance);
  const { breakdown, total } = useMemo(() => computeTax(taxable), [taxable]);
  const payable = total - wht;
  const effective = taxable > 0 ? (total / taxable) * 100 : 0;

  const maxSpan = Math.max(taxable, 1);

  return (
    <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4 md:p-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Field label="Gross Salary Income" hint="Section 12 — annual" value={salary} onChange={setSalary} />
        <Field label="Business Income" hint="Section 18 — net profit" value={business} onChange={setBusiness} />
        <Field label="Exempt Income" hint="Second Schedule, Part I" value={exemptions} onChange={setExemptions} />
        <Field label="Deductible Allowance" hint="Section 60 / 60C" value={allowance} onChange={setAllowance} />
        <Field label="Withholding Tax Paid" hint="Sections 149 / 153 credits" value={wht} onChange={setWht} />
        <div className="panel relative overflow-hidden p-3">
          <span className="absolute inset-x-0 top-0 h-px bg-[var(--gradient-slab)]" />
          <span className="text-data block text-[10px] uppercase tracking-widest text-muted-foreground">
            Taxable Income
          </span>
          <span className="text-data mt-2 block text-lg text-primary">{PKR(taxable)}</span>
          <span className="mt-1 block text-[10px] text-muted-foreground">
            Effective rate {effective.toFixed(2)}%
          </span>
        </div>
      </div>

      <section className="panel p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-medium">Tax Slab Distribution</h3>
          <span className="text-data text-[10px] text-muted-foreground">
            Salaried individual · FY 2025-26
          </span>
        </div>

        <div className="flex h-6 w-full overflow-hidden rounded-md border border-border bg-background">
          {breakdown.map(({ slab, amount }) =>
            amount > 0 ? (
              <div
                key={slab.label}
                title={`${slab.label} — ${PKR(amount)}`}
                style={{ width: `${(amount / maxSpan) * 100}%` }}
                className={cn(
                  "h-full transition-all duration-500",
                  slab.rate === 0
                    ? "bg-muted-foreground/30"
                    : slab.rate <= 0.11
                      ? "bg-primary/70"
                      : slab.rate <= 0.23
                        ? "bg-primary"
                        : slab.rate <= 0.3
                          ? "bg-warning/80"
                          : "bg-destructive/80",
                )}
              />
            ) : null,
          )}
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[34rem] text-xs">
            <thead>
              <tr className="text-data text-[10px] uppercase tracking-widest text-muted-foreground">
                <th className="py-2 text-left font-normal">Slab</th>
                <th className="py-2 text-left font-normal">Bracket</th>
                <th className="py-2 text-right font-normal">Income in slab</th>
                <th className="py-2 text-right font-normal">Tax</th>
              </tr>
            </thead>
            <tbody>
              {breakdown.map(({ slab, amount, tax }) => (
                <tr
                  key={slab.label}
                  className={cn(
                    "border-t border-border",
                    amount === 0 && "text-muted-foreground/50",
                  )}
                >
                  <td className="py-2">
                    <span className="text-data rounded border border-border px-1.5 py-0.5 text-[10px]">
                      {slab.label}
                    </span>
                  </td>
                  <td className="text-data py-2 text-muted-foreground">
                    {slab.from.toLocaleString()} –{" "}
                    {slab.to ? slab.to.toLocaleString() : "above"}
                  </td>
                  <td className="text-data py-2 text-right">{PKR(amount)}</td>
                  <td className="text-data py-2 text-right text-primary">{PKR(tax)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="panel p-4">
          <span className="text-data block text-[10px] uppercase tracking-widest text-muted-foreground">
            Total Tax Liability
          </span>
          <span className="text-data mt-1 block text-xl">{PKR(total)}</span>
        </div>
        <div className="panel p-4">
          <span className="text-data block text-[10px] uppercase tracking-widest text-muted-foreground">
            WHT Credit Applied
          </span>
          <span className="text-data mt-1 block text-xl text-warning">−{PKR(wht)}</span>
        </div>
        <div className="panel relative overflow-hidden p-4">
          <span className="absolute inset-x-0 top-0 h-px bg-primary shadow-[var(--glow-primary)]" />
          <span className="text-data block text-[10px] uppercase tracking-widest text-muted-foreground">
            {payable >= 0 ? "Balance Payable" : "Refundable"}
          </span>
          <span
            className={cn(
              "text-data mt-1 block text-xl",
              payable >= 0 ? "text-primary" : "text-destructive",
            )}
          >
            {PKR(Math.abs(payable))}
          </span>
        </div>
      </div>

      <div className="panel flex items-start gap-3 border-warning/25 bg-warning/5 p-4">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-warning/30 bg-warning/10 text-warning">
          <Sparkles className="h-4 w-4" />
        </span>
        <div className="text-sm">
          <div className="flex items-center gap-2 font-medium">
            Optimization Insight
            <TrendingDown className="h-3.5 w-3.5 text-primary" />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Claiming the full Section 60C housing-finance allowance and pension
            contribution credit under Section 63 could legitimately reduce taxable
            income by up to{" "}
            <span className="text-data text-primary">{PKR(Math.min(taxable * 0.1, 500_000))}</span>
            , cutting liability by roughly{" "}
            <span className="text-data text-primary">
              {PKR(Math.min(taxable * 0.1, 500_000) * 0.3)}
            </span>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
