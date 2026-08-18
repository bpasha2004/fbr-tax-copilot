import { Database, HardDrive, Layers, Server } from "lucide-react";
import { PulseDot } from "./StatusBits";

const SERVICES = [
  { label: "Ollama", detail: "qwen2.5:3b", icon: Server, tone: "primary" as const },
  { label: "ChromaDB", detail: "1,586 chunks", icon: Layers, tone: "primary" as const },
  { label: "PostgreSQL", detail: "12ms", icon: Database, tone: "primary" as const },
  { label: "Redis", detail: "cache 84%", icon: HardDrive, tone: "warning" as const },
];

export function BottomDock() {
  return (
    <footer className="z-30 flex h-9 shrink-0 items-center gap-4 overflow-x-auto border-t border-border bg-background/80 px-4 backdrop-blur-md">
      {SERVICES.map((s) => {
        const Icon = s.icon;
        return (
          <div
            key={s.label}
            className="text-data flex shrink-0 items-center gap-2 text-[10px] text-muted-foreground"
          >
            <PulseDot tone={s.tone} />
            <Icon className="h-3 w-3" />
            <span className="text-foreground/80">{s.label}</span>
            <span>{s.detail}</span>
          </div>
        );
      })}
      <div className="text-data ml-auto shrink-0 text-[10px] text-muted-foreground">
        Local Ollama pipeline · embeddings nomic-embed-text · idx v4.0.0
      </div>
    </footer>
  );
}
