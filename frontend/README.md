# Emerald Ledger

Product Vision: FBR Tax Copilot (AI Tax Engine & Compliance Workstation)

Design Philosophy:

The design balances statutory authority with modern FinTech precision—combining high-density corporate data visualization with an approachable, intelligent conversational copilot. The aesthetic merges Deep Emerald & Obsidian Cyber-Minimalism (conveying regulatory authority and trust) with high-contrast emerald green, muted gold accents, and tactical micro-interactions.




1. Visual Identity & Color Palette

Color Palette Tokens

Background (Primary): Obsidian Gray (#090D12) — Deep, clean dark mode to eliminate eye strain during dense tax auditing.

Background (Surface/Cards): Slate Charcoal (#121820) — Subtle elevated panels with backdrop-filter: blur(12px) and 1px border (#1E293B).

Primary Accent (FinTech Emerald): #10B981 (Glow: rgba(16, 185, 129, 0.25)) — Denotes tax accuracy, financial liquidity, and active system health.

Secondary Accent (Regulatory Gold/Amber): #F59E0B — Used for active tax liabilities, compliance warnings, and statutory audit highlights.

Alert Red: #EF4444 — For tax penalty risks, non-compliance alerts, and system exceptions.

Typography: Primary text #F8FAFC, Muted text #94A3B8, Monospace (Data & Code) JetBrains Mono or Fira Code.

2. Architecture & Layout Structure

A 3-Column Professional Workstation Layout designed for financial analysts, business owners, and tax consultants.




+-------------------------------------------------------------------------------------------------+
| TOP NAV: System Health | Ollama LLM Status | Model: Qwen 2.5 3B | API Key Config | User Profile  |
+----------------------+------------------------------------------+-------------------------------+
|                      |                                          |                               |
|   LEFT SIDEBAR       |            CENTER WORKSPACE              |         RIGHT PANEL           |
|   (Navigation &      |          (Dual Mode: Chat /              |    (Statutory Evidence &      |
|    Tax Workflows)    |           Tax Calculators)               |      Payment Gateway)         |
|                      |                                          |                               |
|  - Dashboard         |  [Tab 1: AI Tax Copilot Chat]             |  - Cited Ordinance Sections   |
|  - RAG Statutory Search| - Streaming response feed               |    (Income Tax Ordinance 2001) |
|  - Tax Calculators   | - Collapsible source provenance tags     |  - Confidence Score Meter     |
|  - Compliance Audit  | - Quick prompt pills                     |  - Active Tax Deductions      |
|  - Payment Sandbox   |                                          |  - Payment Sandbox Trigger    |
|  - System Logs       |  [Tab 2: Tax Calculation Matrix]         |    (JazzCash / EasyPaisa /     |
|                      | - Dynamic inputs (Salary, Business, WHT) |     Raast Webhook Simulator)  |
|                      | - Live visual tax slab distribution      |                               |
+----------------------+------------------------------------------+-------------------------------+
| BOTTOM DOCK: Active Local Ollama Pipeline | ChromaDB Index Status (1,586 Chunks Active)         |
+-------------------------------------------------------------------------------------------------+


3. Key Interface Components & Design Details

A. Top Navigation & System Status Bar

System Status Pill: Live pulsing emerald green LED badge: API status: 200 OK (v4.0.0).

Local LLM Telemetry Monitor: Miniature hardware monitor showing Ollama runtime specs (Qwen2.5:3b | nomic-embed-text | Memory Allocation).

Global Search Bar: Command-K (Cmd+K / Ctrl+K) spotlight bar searching across Ordinance Sections, Finance Acts, and previous tax session histories.

B. Left Sidebar: Tactical Navigation

Nav Items:




Copilot Chat (Icon: Sparkles + Terminal)

Statutory RAG Search (Icon: Book Open / Scale)

Income & Withholding Calculator (Icon: Calculator / Percentage)

Audit & Compliance Checklist (Icon: Shield Check)

Payment Webhook Sandbox (Icon: Credit Card / Terminal)

Bottom Profile Card: User FinTech Workspace switcher (e.g., Individual Filer vs. Corporate Entity).

C. Central Workspace: Dual-Tab Architecture

Tab 1: AI Tax Copilot Chat Interface

Prompt Input Box: Floating glassmorphic panel with glass elevation (backdrop-blur-md). Features quick-action pills above the text input:




[⚡ Calculate Section 153 WHT]

[📜 Income Tax Ordinance 2001 Slices]

[💰 Salary Tax Slabs FY2025-26]

Message Bubble Design:




User Message: Dark slate panel aligned right with a clean emerald accent edge.

Copilot Message: Obsidian panel aligned left with structured Markdown support (tables, statutory bullet points, and inline LaTeX math equations for tax formulas).

Interactive Code/Formula Block: Any tax calculation equation rendered with a "Copy Formula" button and interactive parameter slider.

Tab 2: Multi-Source Tax Calculation Matrix

Dynamic Input Cards: Glowing input boxes for Gross Income, Exemptions, Allowance Deductions under Section 60, and Withholding Tax paid.

Interactive Slabs Chart: Visual breakdown bar showing which income bracket falls into which tax percentage slab, with animated gradient fills.

Break-Even & Optimization Card: AI-generated summary pill highlighting potential legitimate tax savings or tax credit opportunities.

D. Right Panel: Regulatory Inspector & Payment Sandbox

1. Statutory Provenance & Citation Panel

Citation Cards: Whenever the Copilot answers, this panel automatically renders the exact statutory citations retrieved from ChromaDB (e.g., Section 153(1)(b) - Sale of Services).

Chunk Viewer Modal: Clicking a citation opens a glass slide-over showing the raw PDF layout chunk, complete with highlight overlays on the exact text used by the RAG model.

Confidence Meter: A radial gauge indicating vector similarity precision (94.8% Match Score).

2. Integrated Payment Sandbox Simulator UI

Gateway Cards: Visual selector cards for JazzCash, EasyPaisa, and Raast.

Simulated Webhook Dispatcher:




Input field for Transaction ID, Amount (PKR), and Callback URL.

A single "Simulate Instant Payment Hook" button with haptic press animation and neon green success state animation (200 OK Webhook Delivered).

4. Component Design System Details

Buttons

Primary CTA Button: High-contrast FinTech emerald (#10B981) background, sharp border-radius (6px), dark text (#090D12), subtle glow effect on hover (box-shadow: 0 0 15px rgba(16, 185, 129, 0.4)).

Secondary Action Button: Transparent glass button with 1px slate border (#334155), white text, turning emerald on focus.

Destructive/Clear Button: Deep crimson ghost button (#EF4444) for clearing sessions or resetting input matrices.

Cards & Glassmorphism

Card Containers: #121820 with 1px solid #1E293B, subtle hover state elevation (transform: translateY(-2px)), and thin top accent line.

Tab Switches: Segmented control toggles with sliding obsidian active pill indicator.

Micro-Interactions & Animation Cues

RAG Query Pulse: When searching ChromaDB, a horizontal neon beam sweeps across the top of the chat area.

Streaming Typography Effect: Answers stream in smoothly with a blip cursor indicator.

Status Badges: Real-time ping pulses on active service indicators (PostgreSQL, Redis, ChromaDB, Ollama).

5. Prompt Directives to Copy-Paste into Lovable

Plaintext

Build a modern dark-mode FinTech Web Application called "FBR Tax Copilot". 

Theme & Aesthetic:
- Obsidian Cyber-Minimalism theme. Primary background #090D12, card background #121820 with 1px border #1E293B.
- Accents: FinTech Emerald (#10B981) for primary actions and active statuses; Regulatory Gold (#F59E0B) for warnings and tax slab highlights.
- Fonts: Inter for UI body, JetBrains Mono or Fira Code for tax figures, API logs, and formulas.

Layout Architecture:
1. Top Navigation Bar: Displays app logo "FBR Tax Copilot", API status LED badge ("API: 200 OK v4.0.0"), Ollama Model Badge ("Qwen 2.5 3B"), and Cmd+K Search trigger.
2. Left Sidebar (Collapsible): Navigation items for Copilot Chat, Statutory RAG Search, Tax Calculator, Audit Checklist, and Payment Webhook Sandbox.
3. Central Main Content Area (Dual-Tab View):
   - Tab 1 (AI Tax Copilot): Modern AI Chat interface with streaming text bubbles, quick prompt pill overlays ([⚡ Section 153 WHT], [📜 Finance Act 2024 Slices]), markdown table support, and code syntax highlighting.
   - Tab 2 (Tax Calculation Matrix): Financial inputs for salary, business income, exemptions, and withholding tax paid, accompanied by a dynamic visual tax slab distribution bar.
4. Right Inspector Panel:
   - Statutory Citations Card: Displays retrieved sections from the Income Tax Ordinance 2001 with vector similarity confidence scores.
   - Payment Sandbox Card: Simulator for JazzCash, EasyPaisa, and Raast webhooks with interactive "Simulate Webhook" trigger and instant status response toast.

Components & Polish:
- Include glassmorphism backdrop blurs for floating toolbars.
- Responsive design with smooth transition states, haptic-style button animations, and crisp status badges.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/54394acf-1133-4e8f-ae3b-145e817b4d90).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
