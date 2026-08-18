export type Citation = {
  id: string;
  section: string;
  title: string;
  act: string;
  score: number;
  chunk: string;
  highlight: string;
};

export const CITATIONS: Citation[] = [
  {
    id: "c1",
    section: "Section 153(1)(b)",
    title: "Payments for goods, services and contracts — Sale of Services",
    act: "Income Tax Ordinance, 2001",
    score: 94.8,
    highlight: "deduct tax from the gross amount payable at the rate specified",
    chunk:
      "(1) Every prescribed person making a payment in full or part including a payment by way of advance to a resident person — (b) for the rendering of or providing of services, shall, at the time of making the payment, deduct tax from the gross amount payable at the rate specified in Division III of Part III of the First Schedule.",
  },
  {
    id: "c2",
    section: "Division I, Part I — First Schedule",
    title: "Rates of tax for salaried individuals (Tax Year 2026)",
    act: "Finance Act, 2025",
    score: 91.2,
    highlight: "where taxable income exceeds Rs. 2,200,000",
    chunk:
      "Where taxable income does not exceed Rs. 600,000 the rate of tax is 0%. Where taxable income exceeds Rs. 600,000 but does not exceed Rs. 1,200,000 the rate is 1% of the amount exceeding Rs. 600,000. Where taxable income exceeds Rs. 2,200,000 but does not exceed Rs. 3,200,000 the tax is Rs. 180,000 plus 25% of the amount exceeding Rs. 2,200,000.",
  },
  {
    id: "c3",
    section: "Section 60C",
    title: "Deductible allowance for profit on debt (house financing)",
    act: "Income Tax Ordinance, 2001",
    score: 87.4,
    highlight: "shall be entitled to a deductible allowance",
    chunk:
      "Every individual shall be entitled to a deductible allowance for the amount of any profit or share in rent and share in appreciation for value of house paid by the individual on a loan by a scheduled bank utilised for the construction of a new house or the acquisition of a house.",
  },
  {
    id: "c4",
    section: "Section 149",
    title: "Salary — deduction of tax at source by employer",
    act: "Income Tax Ordinance, 2001",
    score: 83.6,
    highlight: "average rate of tax computed at the rates specified",
    chunk:
      "Every employer paying salary to an employee shall, at the time of payment, deduct tax from the amount paid at the employee's average rate of tax computed at the rates specified in Division I of Part I of the First Schedule for the tax year in which the payment is made.",
  },
];

export type Slab = {
  label: string;
  from: number;
  to: number | null;
  rate: number;
  base: number;
};

/** Salaried individual slabs, illustrative FY 2025-26. */
export const SLABS: Slab[] = [
  { label: "0%", from: 0, to: 600_000, rate: 0, base: 0 },
  { label: "1%", from: 600_000, to: 1_200_000, rate: 0.01, base: 0 },
  { label: "11%", from: 1_200_000, to: 2_200_000, rate: 0.11, base: 6_000 },
  { label: "23%", from: 2_200_000, to: 3_200_000, rate: 0.23, base: 116_000 },
  { label: "30%", from: 3_200_000, to: 4_100_000, rate: 0.3, base: 346_000 },
  { label: "35%", from: 4_100_000, to: null, rate: 0.35, base: 616_000 },
];

export function computeTax(taxable: number) {
  const breakdown = SLABS.map((s) => {
    const upper = s.to ?? Number.POSITIVE_INFINITY;
    const amount = Math.max(0, Math.min(taxable, upper) - s.from);
    return { slab: s, amount, tax: amount * s.rate };
  });
  const total = breakdown.reduce((a, b) => a + b.tax, 0);
  return { breakdown, total };
}

export const PKR = (n: number) =>
  "PKR " +
  Math.round(n).toLocaleString("en-PK", { maximumFractionDigits: 0 });
