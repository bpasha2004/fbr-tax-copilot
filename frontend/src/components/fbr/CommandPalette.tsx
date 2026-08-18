import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

const GROUPS = [
  {
    heading: "Ordinance Sections",
    items: [
      "Section 153 — Payments for goods and services",
      "Section 149 — Salary withholding",
      "Section 60C — Housing finance allowance",
      "Section 236 — Advance tax on utilities",
    ],
  },
  {
    heading: "Finance Acts",
    items: ["Finance Act 2025 — Salary slabs", "Finance Act 2024 — Super tax 4C"],
  },
  {
    heading: "Recent Sessions",
    items: ["WHT reconciliation Q3", "Corporate return TY2025 draft"],
  },
];

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search ordinance sections, finance acts, sessions…" />
      <CommandList>
        <CommandEmpty>No statutory match found.</CommandEmpty>
        {GROUPS.map((g) => (
          <CommandGroup key={g.heading} heading={g.heading}>
            {g.items.map((i) => (
              <CommandItem key={i} onSelect={() => onOpenChange(false)}>
                <span className="text-data text-xs">{i}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}
