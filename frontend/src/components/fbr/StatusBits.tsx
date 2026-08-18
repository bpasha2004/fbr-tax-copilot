import { cn } from "@/lib/utils";

type Tone = "primary" | "warning" | "destructive" | "muted";

const dotTone: Record<Tone, string> = {
  primary: "bg-primary",
  warning: "bg-warning",
  destructive: "bg-destructive",
  muted: "bg-muted-foreground",
};

export function PulseDot({
  tone = "primary",
  className,
}: {
  tone?: Tone;
  className?: string;
}) {
  return (
    <span className={cn("relative inline-flex h-2 w-2", className)}>
      <span
        className={cn(
          "absolute inline-flex h-full w-full rounded-full opacity-70 animate-ping-slow",
          dotTone[tone],
        )}
      />
      <span
        className={cn("relative inline-flex h-2 w-2 rounded-full", dotTone[tone])}
      />
    </span>
  );
}

export function StatusPill({
  label,
  tone = "primary",
  mono = true,
  className,
}: {
  label: string;
  tone?: Tone;
  mono?: boolean;
  className?: string;
}) {
  const ring: Record<Tone, string> = {
    primary: "border-primary/30 text-primary bg-primary/10",
    warning: "border-warning/30 text-warning bg-warning/10",
    destructive: "border-destructive/30 text-destructive bg-destructive/10",
    muted: "border-border text-muted-foreground bg-secondary/60",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-md border px-2.5 py-1 text-[11px] leading-none",
        mono && "text-data",
        ring[tone],
        className,
      )}
    >
      <PulseDot tone={tone} />
      {label}
    </span>
  );
}
