# Argus Style Guide

Design tokens, component patterns, and conventions used across the Argus frontend.

> **Scope:** This is a **dark-mode-only** interface.
All opacity-based surfaces (`bg-slate-900/40`, `bg-slate-900/50`, etc.)
assume a `#0f172a` parent background. Do not render this UI in a light container or iframe without a full theme audit.

---

## Table of Contents

1. [Stack](#1-stack)
2. [Color Palette](#2-color-palette)
3. [Accessibility — Color Compliance](#3-accessibility--color-compliance)
4. [Typography](#4-typography)
5. [Spacing & Layout](#5-spacing--layout)
6. [Borders & Surfaces](#6-borders--surfaces)
7. [Components](#7-components)
8. [Charts (Recharts)](#8-charts-recharts)
9. [Scrollbar](#9-scrollbar)
10. [Motion Patterns (Framer Motion)](#10-motion-patterns-framer-motion)
11. [Empty & Loading States](#11-empty--loading-states)
12. [Logo & Brand Rules](#12-logo--brand-rules)
13. [AI Assistance Notes](#13-ai-assistance-notes)
14. [Changelog](#14-changelog)

---

## 1. Stack

| Concern | Tool | Version |
| --- | --- | --- |
| Styling | Tailwind CSS | v3 |
| Component framework | React + TypeScript | 18 |
| Animation | Framer Motion | v10+ |
| Icons | Lucide React | latest |
| Charts | Recharts | v2 |
| Font | Inter (Google Fonts, weights 300–800) | — |

---

## 2. Color Palette

### 2.1 Base / Backgrounds

| Token | Hex | Usage |
| --- | --- | --- |
| `slate-950` | `#0f172a` | App background, header, sidebar |
| `slate-900/40` | `#0f172a66` | Card surface |
| `slate-900/50` | `#0f172a80` | Metric card surface |
| `slate-800` | `#1e293b` | Borders, hover surfaces, chart grid |
| `slate-700` | `#334155` | Input borders, muted borders |

### 2.2 Text

| Token | Hex | Ratio on slate-950 | Usage |
| --- | --- | --- | --- |
| `slate-100` | `#f1f5f9` | 16.8:1 AAA | Primary text, page titles |
| `slate-200` | `#e2e8f0` | 13.4:1 AAA | Section/card headings, table data |
| `slate-300` | `#cbd5e1` | 9.8:1 AAA | Form labels, table cell text; **minimum for body text on card surfaces** |
| `slate-400` | `#94a3b8` | 5.9:1 AA | Secondary text, nav inactive, captions, chart axes, placeholders |
| `slate-500` | `#64748b` | 3.1:1 ✗ | **Do not use for readable text.** Decorative/non-text only (borders, dividers). |

> ⚠️ **`slate-500` text is a WCAG AA failure (3.1:1).**
Use `slate-400` as the minimum for any text the user needs to read.
See [Section 3](#3-accessibility--color-compliance) for full details.

### 2.3 Accent / Semantic

| Token | Hex | Ratio on slate-950 | Role | Used for |
| --- | --- | --- | --- | --- |
| `purple-400` | `#c084fc` | 7.1:1 AAA | Primary accent | Active power metric, nav active, links |
| `purple-500` | `#a855f7` | 4.9:1 AA | Primary action | Primary button bg, toggle-on (default) |
| `violet-400` | `#a78bfa` | 5.6:1 AA | Secondary power | Secondary power rail, reactive power metric |
| `fuchsia-400` | `#e879f9` | 7.8:1 AAA | Peak / Critical | Peak demand, critical threshold breached |
| `amber-400` | `#fbbf24` | 9.3:1 AAA | Warning | Overvoltage / undervoltage warnings |
| `emerald-400` | `#34d399` | 8.2:1 AAA | Nominal / Healthy | Within-spec indicators, success states |
| `orange-400` | `#fb923c` | 5.2:1 AA | Alerts | User-configured alert notifications |
| `red-400` | `#f87171` | 5.1:1 AA | Error | System/sensor failures, fault states |

### 2.4 Semantic Color Boundary — Red vs Orange

These two colors appear close in purpose. Their boundaries are explicit:

| Color | Token | Meaning |
| --- | --- | --- |
| Red | `red-400` | **System / sensor failure** — a device, channel, or reading errored or is offline |
| Orange | `orange-400` | **User-configured alert notification** — thresholds triggered a user's alert rules |

Never use red for alert notifications or orange for system failures.

### 2.5 Semantic Color Boundary — Purple vs Fuchsia

| Color | Token | Meaning |
| --- | --- | --- |
| Purple | `purple-400` | **Active (real) power** — the primary power metric; kW, watts |
| Fuchsia | `fuchsia-400` | **Peak / critical demand** — instantaneous peaks, demand-limit breaches |

Fuchsia is reserved exclusively for peak and critical states. Do not use it as a general accent.

### 2.6 Tint Surface System

All colored tint surfaces follow the same pattern: `bg-{color}-500/10 border border-{color}-500/20 text-{color}-400`.
This ensures consistent contrast on the dark parent background.

| Metric / State | Bg tint | Border | Text | Ratio |
| --- | --- | --- | --- | --- |
| Active Power / Purple | `bg-purple-500/10` | `border-purple-500/20` | `text-purple-400` | 7.1:1 AAA |
| Reactive Power / Violet | `bg-violet-500/10` | `border-violet-500/20` | `text-violet-400` | 5.6:1 AA |
| Peak / Fuchsia | `bg-fuchsia-500/10` | `border-fuchsia-500/20` | `text-fuchsia-400` | 7.8:1 AAA |
| Warning / Amber | `bg-amber-500/10` | `border-amber-500/20` | `text-amber-400` | 9.3:1 AAA |
| Nominal / Emerald | `bg-emerald-500/10` | `border-emerald-500/20` | `text-emerald-400` | 8.2:1 AAA |
| Alert | `bg-orange-500/10` | `border-orange-500/20` | `text-orange-400` | 5.2:1 AA |
| Error | `bg-red-500/10` | `border-red-500/20` | `text-red-400` | 5.1:1 AA |
| Success | `bg-emerald-500/10` | `border-emerald-500/20` | `text-emerald-400` | 8.2:1 AAA |

### 2.7 Disabled Color Pattern

Disabled colored elements use their normal color at reduced opacity:

```css
/* Disabled toggle, button, or colored indicator */
opacity: 40%;
cursor: not-allowed;

/* Example — disabled purple toggle */
/* bg-purple-500/40 instead of bg-purple-500 */
```

---

## 3. Accessibility — Color Compliance

### 3.1 Summary

| Status | Count | Details |
| --- | --- | --- |
| ✅ Pass AAA (7:1+) | 6 pairs | slate-100/200/300 on slate-950; purple-400, fuchsia-400, amber-400, emerald-400 on slate-950 |
| ✅ Pass AA (4.5:1+) | 8 pairs | All accent colors on slate-950; slate-400 on slate-950 |
| ⚠️ Borderline | 1 pair | purple-500 button (4.9:1 — passes AA; slate-950 label required) |
| ❌ Fail | 2 pairs | **slate-500 on slate-950 (3.1:1); slate-500 on slate-800 (2.1:1)** |

### 3.2 Required Token Rules

- **`slate-500` → `slate-400`** everywhere used for readable text (helper, caption, chart axes, placeholders, table headers)
- **`placeholder:text-slate-400`** — never `placeholder:text-slate-500`
- **Scrollbar thumb:** `#475569` (slate-600) for WCAG 1.4.11 Non-text Contrast (~3.4:1)
- **Card body text minimum:** `slate-300` on `bg-slate-900/40` card surfaces

### 3.3 Full Contrast Reference Table

| Foreground | Background | Ratio | AA Normal | Used for |
| --- | --- | --- | --- | --- |
| `slate-100` `#f1f5f9` | `slate-950` | 16.8:1 | ✅ AAA | Page titles |
| `slate-200` `#e2e8f0` | `slate-950` | 13.4:1 | ✅ AAA | Card headings |
| `slate-300` `#cbd5e1` | `slate-950` | 9.8:1 | ✅ AAA | Form labels |
| `slate-400` `#94a3b8` | `slate-950` | 5.9:1 | ✅ AA | Secondary text |
| `slate-500` `#64748b` | `slate-950` | 3.1:1 | ❌ FAIL | **Text use prohibited** |
| `slate-300` `#cbd5e1` | `slate-900/40` | ~8.4:1 | ✅ AAA | Card body text |
| `purple-400` `#c084fc` | `slate-950` | 7.1:1 | ✅ AAA | Nav active, primary metric |
| `purple-500` `#a855f7` (as bg) | `slate-950` text on it | 4.9:1 | ✅ AA | Button label |
| `violet-400` `#a78bfa` | `slate-950` | 5.6:1 | ✅ AA | Reactive power metric |
| `fuchsia-400` `#e879f9` | `slate-950` | 7.8:1 | ✅ AAA | Peak / critical |
| `amber-400` `#fbbf24` | `slate-950` | 9.3:1 | ✅ AAA | Warnings |
| `emerald-400` `#34d399` | `slate-950` | 8.2:1 | ✅ AAA | Nominal / success |
| `orange-400` `#fb923c` | `slate-950` | 5.2:1 | ✅ AA | Alerts |
| `red-400` `#f87171` | `slate-950` | 5.1:1 | ✅ AA | Errors |
| `slate-600` `#475569` | transparent/dark | ~3.4:1 | ✅ 1.4.11 | Scrollbar thumb |

---

## 4. Typography

Font family: **Inter** — `font-family: 'Inter', system-ui, sans-serif`
Anti-aliasing: `-webkit-font-smoothing: antialiased`

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
```

| Style | Tailwind classes | Example |
| --- | --- | --- |
| Display (metric value) | `text-3xl md:text-4xl font-bold tracking-tighter` | `3.84` |
| Page title | `text-2xl font-bold text-slate-100` | `Dashboard` |
| Section heading | `text-lg font-semibold text-slate-200` | `Power History` |
| Card heading | `text-base font-semibold text-slate-200` | `Circuit Breaker A` |
| Sub-section heading | `text-sm font-medium text-slate-300` | `Phase Voltages` |
| Body / description | `text-sm text-slate-300` | `Monitoring active · last polled…` |
| Form label | `text-sm font-medium text-slate-300` | `Poll Interval (seconds)` |
| Helper / caption | `text-xs text-slate-400` | `Minimum 5 seconds.` |
| Table header | `text-xs font-medium uppercase tracking-wider text-slate-400` | `TIMESTAMP` |
| Monospace data | `font-mono font-medium text-slate-200` | `240.1 V` |
| Unit label | `text-sm text-slate-400` | `kW · kVAR · PF` |
| Badge / pill text | `text-xs` | `12 channels` |

> **Power unit values** (kW, kVAR, kWh, V, A, Hz, PF) should always be rendered in `font-mono` to align digits in tables and metric cards.

---

## 5. Spacing & Layout

| Token | Value | Usage |
| --- | --- | --- |
| Header height | `h-14` (56px) | Fixed top bar |
| Sidebar width | `w-56` (224px) | Desktop left sidebar |
| Page max-width | `max-w-6xl` | Dashboard content area |
| Settings max-width | `max-w-3xl` | Settings page |
| Content padding (mobile) | `p-4` | Main content wrapper |
| Content padding (desktop) | `md:p-6` | Main content wrapper |
| Section gap | `space-y-6` | Between top-level page sections |
| Card padding | `p-6` | Standard card interior |
| Card border-radius | `rounded-2xl` | Cards, metric tiles |
| Panel border-radius | `rounded-xl` | Collapsible panels |
| Input border-radius | `rounded-lg` | Text inputs, textareas |
| Badge border-radius | `rounded-full` | Pills and status chips |
| Badge border-radius (chip) | `rounded-md` | Inline status badges (e.g. "Polling") |

---

## 6. Borders & Surfaces

```css
/* Card */
bg-slate-900/40  border border-slate-800  rounded-2xl

/* Panel */
bg-slate-900/30  border border-slate-800  rounded-xl

/* Row item */
bg-slate-800/30  border border-slate-700/50  rounded-lg

/* Header */
bg-slate-950/90  border-b border-slate-800  backdrop-blur

/* Sidebar */
bg-slate-950/50  border-r border-slate-800

/* Input */
bg-slate-950  border border-slate-700  rounded-lg

/* Divider (within cards) */
border-t border-slate-700
```

> **Purple glow accent on critical metric cards:** A subtle `shadow-purple-500/20` box shadow may be applied to active-power metric cards to reinforce brand identity. Use sparingly — only on the primary kW card, not on every card.

---

## 7. Components

### 7.1 Buttons

#### Primary

```css
bg-purple-500 hover:bg-purple-400 text-slate-950
shadow-lg shadow-purple-500/20
px-4 py-2 rounded-lg font-medium transition-all
```

> Button label text: `text-slate-950` on `bg-purple-500` = 4.9:1 (passes AA at font-medium 14px+). Do not reduce button font size below 14px bold without switching to `bg-purple-400`.

#### Ghost / Tinted (purple)

```css
bg-purple-500/10 hover:bg-purple-500/20 text-purple-400
border border-purple-500/30
px-4 py-2 rounded-lg font-medium transition-all
```

#### Success state

```css
bg-emerald-500/20 text-emerald-400 border border-emerald-500/30
```

#### Error state

```css
bg-red-500/10 text-red-400 border border-red-500/20
```

#### Disabled

```css
bg-slate-800 text-slate-500 cursor-not-allowed
```

> `slate-500` is acceptable here — disabled elements are exempt from contrast requirements under WCAG 1.4.3.

#### Icon-only

```css
p-2 rounded-md text-slate-400
hover:text-slate-200 hover:bg-slate-800/50 transition-colors
```

> **Required:** every icon-only button must have `aria-label="[action description]"`. Examples: `aria-label="Export CSV"`, `aria-label="Collapse event log"`, `aria-label="Acknowledge alert"`.

---

### 7.2 Inputs & Textareas

Base classes shared by all inputs:

```css
bg-slate-950 border border-slate-700 rounded-lg
px-4 py-2 text-slate-200
placeholder:text-slate-400
focus:outline-none focus:ring-1 transition-all
```

Focus ring color varies by section:

| Context | Focus border / ring |
| --- | --- |
| General / Settings | `focus:border-purple-500 focus:ring-purple-500` |
| Alert thresholds | `focus:border-orange-500 focus:ring-orange-500` |
| API / Integration | `focus:border-amber-500 focus:ring-amber-500` |

---

### 7.3 Toggles

Large (h-5 w-9) — used for channel enables and master polling toggle:

```jsx
<button
  role="switch"
  aria-checked={enabled}
  aria-label="Enable Channel 1 Monitoring"
  onClick={() => setEnabled(!enabled)}
  className={cn(
    "relative inline-flex h-5 w-9 items-center rounded-full transition-colors",
    enabled ? "bg-purple-500" : "bg-slate-700"
  )}
>
  <span
    className={cn(
      "inline-block h-3 w-3 rounded-full bg-white transition-transform",
      enabled ? "translate-x-5" : "translate-x-1"
    )}
  />
</button>
```

Small (h-4 w-8) — used for individual alert providers:

```jsx
// Same pattern, different sizing:
// h-4 w-8 · thumb: h-2.5 w-2.5
// enabled: translate-x-4.5 · disabled: translate-x-1
```

Toggle-on color by context:

| Context | Active color |
| --- | --- |
| Channel / device monitoring | `bg-purple-500` |
| Alert master toggle | `bg-orange-500` |
| Nominal threshold indicator | `bg-emerald-500` |

> **ARIA required:** `role="switch"` and `aria-checked={boolean}` must be present on every toggle. `aria-label` must describe the specific setting being toggled.

---

### 7.4 Badges & Pills

| Variant | Classes |
| --- | --- |
| Default count/label | `text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700` |
| Version mono | `text-xs px-2 py-0.5 rounded-full bg-slate-800/60 text-slate-400 border border-slate-700/50 font-mono` |
| Status chip (active / polling) | `text-xs px-2 py-1 rounded-md bg-purple-500/10 border border-purple-500/20 text-purple-400 font-medium` |
| Status chip (nominal) | `text-xs px-2 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-medium` |
| Status chip (fault) | `text-xs px-2 py-1 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 font-medium` |
| Peak indicator | `text-xs px-2 py-0.5 rounded-full bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/30` |

---

### 7.5 Alert Banners

```css
flex items-center gap-2 px-4 py-3 rounded-lg text-sm
```

| Type | Background | Border | Text |
| --- | --- | --- | --- |
| Error | `bg-red-500/10` | `border-red-500/20` | `text-red-400` |
| Success | `bg-emerald-500/10` | `border-emerald-500/20` | `text-emerald-400` |
| Warning | `bg-amber-500/10` | `border-amber-500/20` | `text-amber-400` |
| Alert (user threshold) | `bg-orange-500/10` | `border-orange-500/20` | `text-orange-400` |

---

### 7.6 Navigation Links

```css
flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all
```

| State | Classes |
| --- | --- |
| Active | `bg-purple-500/10 text-purple-400 border border-purple-500/20` |
| Inactive | `text-slate-400 hover:text-slate-200 hover:bg-slate-800/50` |

---

### 7.7 Metric Cards (PowerGauge)

Each metric card is a `rounded-2xl border bg-slate-900/50` with a thin top accent strip:

```css
relative overflow-hidden rounded-2xl border {metric.border} bg-slate-900/50 p-5
flex flex-col items-center justify-center text-center
```

Top accent strip:

```css
absolute top-0 left-0 w-full h-0.5 {metric.bg}
```

Icon container:

```css
p-2.5 rounded-full {metric.bg} {metric.color} mb-3
```

| Metric | Text color | Background tint | Border | Label color |
| --- | --- | --- | --- | --- |
| Active Power (kW) | `text-purple-400` | `bg-purple-500/10` | `border-purple-500/20` | `text-slate-400` |
| Reactive Power (kVAR) | `text-violet-400` | `bg-violet-500/10` | `border-violet-500/20` | `text-slate-400` |
| Voltage (V) | `text-amber-400` | `bg-amber-500/10` | `border-amber-500/20` | `text-slate-400` |
| Power Factor (PF) | `text-emerald-400` | `bg-emerald-500/10` | `border-emerald-500/20` | `text-slate-400` |
| Peak Demand | `text-fuchsia-400` | `bg-fuchsia-500/10` | `border-fuchsia-500/20` | `text-slate-400` |
| Current (A) | `text-slate-200` | `bg-slate-700/30` | `border-slate-700/40` | `text-slate-400` |

> The **Active Power (kW)** card is the hero metric. It may carry the optional `shadow-purple-500/20` glow. No other card uses this glow.

---

### 7.8 Event Log / Collapsible Panel

The Event Log is a collapsible panel with a header row, badge count, export action, and animated body.

**Panel header:**

```css
flex items-center justify-between px-6 py-4
```

| Element | Classes |
| --- | --- |
| Title | `text-lg font-semibold text-slate-200` |
| Entry count badge | `text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700` |
| Export CSV button | Ghost/tinted button variant (purple) |
| Collapse chevron | Icon-only button — requires `aria-label="Collapse event log"` and `aria-expanded={open}` |

**Collapse animation:**

```jsx
<AnimatePresence>
  {open && (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
    >
      {/* table content */}
    </motion.div>
  )}
</AnimatePresence>
```

**Data table inside panel:**

| Element | Classes |
| --- | --- |
| Table header row | `text-xs font-medium uppercase tracking-wider text-slate-400 border-b border-slate-700` |
| Table header cell | `px-4 py-3` |
| Table body row | `border-b border-slate-800 hover:bg-slate-800/30 transition-colors` |
| Table body cell | `px-4 py-3 text-sm text-slate-300` |
| Monospace data cell | `font-mono text-slate-200` |
| Fault / error row | `bg-red-500/5 border-red-500/10` with `text-red-400` for status cell |
| Peak demand row | `bg-fuchsia-500/5 border-fuchsia-500/10` with `text-fuchsia-400` for value cell |
| Alert-triggered row | `bg-orange-500/5 border-orange-500/10` with `text-orange-400` for status cell |

---

### 7.9 Settings Section Icons

| Section | Icon | Color |
| --- | --- | --- |
| Poll Interval | `Timer` | `text-purple-400` |
| Channels / Devices | `Cpu` | `text-violet-400` |
| Alerts | `Bell` | `text-orange-400` |
| API / Integration | `Key` | `text-amber-400` |
| Thresholds | `Sliders` | `text-fuchsia-400` |
| Export | `Database` | `text-emerald-400` |

---

## 8. Charts (Recharts)

```jsx
<LineChart strokeWidth={2} dot={false}>
  <CartesianGrid
    strokeDasharray="3 3"
    stroke="#1e293b"
    vertical={false}
  />
```

### 8.1 Line Colors

| Series | Hex | Token |
| --- | --- | --- |
| Active Power (kW) | `#c084fc` | `purple-400` |
| Reactive Power (kVAR) | `#a78bfa` | `violet-400` |
| Voltage (V) | `#fbbf24` | `amber-400` |
| Current (A) | `#94a3b8` | `slate-400` |
| Peak Demand reference line | `#e879f9` | `fuchsia-400` |

> The Peak Demand series is rendered as a `ReferenceLine` (dashed, `strokeDasharray="4 2"`) rather than a full series line, to distinguish a demand ceiling from a live reading.

### 8.2 Active Dot

```jsx
activeDot={{ r: 5, stroke: '#0f172a', strokeWidth: 2 }}
```

### 8.3 Axes

```jsx
// Shared axis props
stroke="#64748b"    // slate-500 — acceptable for non-text decorative axis lines
fontSize={12}
tickLine={false}
axisLine={false}

// Tick fill — must use slate-400, not slate-500
fill="#94a3b8"   // slate-400

// XAxis
dy={10}

// YAxis
dx={-10}
// left margin: -20
```

### 8.4 Tooltip

```css
/* Container */
bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl

/* Label */    text-slate-300 text-sm
/* Channel */  text-slate-400 text-xs
/* Name */     text-slate-400
/* Value */    font-mono font-medium text-slate-200
/* Unit */     text-slate-400 text-xs
/* Dot */      w-2 h-2 rounded-full (series color)
```

---

## 9. Scrollbar

```css
scrollbar-width: thin;
scrollbar-color: #475569 transparent; /* slate-600 thumb */

::-webkit-scrollbar        { width: 6px; height: 6px; }
::-webkit-scrollbar-track  { background: transparent; }
::-webkit-scrollbar-thumb  {
  background-color: #475569; /* slate-600 */
  border-radius: 9999px;
}
```

---

## 10. Motion Patterns (Framer Motion)

### 10.1 Standard Patterns

| Pattern | Props |
| --- | --- |
| Page enter | `initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}` |
| Card / section enter | `initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}` |
| Staggered metric cards | `transition={{ delay: i * 0.08 }}` |
| Mobile sidebar | `initial={{ x: '-100%' }} animate={{ x: 0 }}` · `type: 'tween', duration: 0.22` |
| Collapsible panel | `height: 0 → 'auto'` + `opacity: 0 → 1` via `AnimatePresence` |
| Overlay backdrop | `opacity: 0 → 1` |

### 10.2 Standard Duration Tokens

| Name | Value | Used for |
| --- | --- | --- |
| Fast | `0.15s` | Hover color transitions, toggle state |
| Default | `0.20s` | Card enter, collapse, sidebar |
| Slow | `0.30s` | Page enter, staggered sequences |
| Stagger step | `0.08s` | Per-card delay in metric grid |

### 10.3 Tailwind Animation Utilities

| Class | Usage |
| --- | --- |
| `animate-spin` | Activity icon while polling is active |
| `animate-pulse` | Metric value when a threshold is near breach |

### 10.4 Reduced Motion

All animations must respect `prefers-reduced-motion`. Use Framer Motion's `useReducedMotion()` hook:

```jsx
import { useReducedMotion } from 'framer-motion';

function MyComponent() {
  const reduceMotion = useReducedMotion();

  const variants = {
    hidden: { opacity: 0, y: reduceMotion ? 0 : 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      variants={variants}
      initial="hidden"
      animate="visible"
      transition={{ duration: reduceMotion ? 0 : 0.2 }}
    >
      ...
    </motion.div>
  );
}
```

Fallback when reduced motion is preferred: instant opacity transition only, no translate, no stagger delay.

---

## 11. Empty & Loading States

### Empty state

```css
text-center py-20 text-slate-400
/* Icon: */ w-10 h-10 mx-auto mb-3 opacity-30
/* Heading: */ text-lg
/* Sub-text: */ text-sm mt-1  /* accent word: text-purple-400 font-medium */
```

### Loading / device not ready

```css
text-slate-400 text-sm py-10 text-center
```

### Loading spinner (inline)

```css
w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin
```

### No-data chart state

When a chart has no historical data yet, render a centered empty state within the chart container:

```css
/* Overlay on chart area */
flex items-center justify-center h-full
text-slate-400 text-sm
/* Icon: */ Eye (Lucide) opacity-20 w-8 h-8 mb-2
/* Text: */ "No readings yet" · accent: text-purple-400
```

---

## 12. Logo & Brand Rules

The Argus mark is a circular emblem containing a stylized eye motif — referencing the mythological all-seeing giant — with radial circuit-trace lines emanating outward from the iris. The circuit traces use the primary power metric colors, connecting the brand mark to the data the app displays.

### 12.1 Logo Anatomy

| Element | Color | Notes |
| --- | --- | --- |
| Outer ring | `#c084fc` (purple-400) | Matches primary accent |
| Inner field | `#0a0e1a` (near-black) | Darker than slate-950 |
| Iris outline | `#c084fc` (purple-400) | Neon line art |
| Pupil fill | `#a855f7` (purple-500) | Glowing core |
| Circuit trace 1 (top) | `#c084fc` | Active power / purple |
| Circuit trace 2 | `#a78bfa` | Reactive power / violet |
| Circuit trace 3 | `#e879f9` | Peak / fuchsia |
| Circuit trace 4 | `#fbbf24` | Voltage / amber |
| Circuit trace 5 (lower) | gradient violet→purple | Decorative, follows metric palette |

The metric colors appearing in the circuit traces is the visual connection between the brand mark and the data the app displays. Preserve this when resizing or reproducing the mark.

### 12.2 Wordmark Color by Background

| Background | Logo treatment |
| --- | --- |
| Dark (`#0f172a`, `#141414`) | Full color — purple ring + neon eye |
| Light surface | Not recommended — this is a dark-only mark. Use on dark bg only. |
| On purple surface | Use white/light version; avoid full-color on purple |

### 12.3 Minimum Sizes

| Context | Minimum |
| --- | --- |
| Emblem (screen) | 24×24px |
| Emblem (print) | 6mm |
| In-app nav (current) | 28×28px — appropriate |

### 12.4 Clear Space

Maintain clear space equal to the emblem height on all sides. No other text or icons within this zone.

### 12.5 Prohibited Uses

- Do not recolor the purple outline to any other color
- Do not remove or recolor the circuit traces — they carry semantic meaning (metric colors)
- Do not place on light backgrounds without a dedicated light-mode variant
- Do not add drop shadows or glows beyond what is in the original asset
- Do not stretch or distort the aspect ratio
- Do not substitute a generic eye icon for the Argus emblem

---

## 13. AI Assistance Notes

This section provides direct rules for AI code generation tools
(Claude, Copilot, Cursor, etc.) to generate on-brand, accessible Argus UI code.

### When generating Argus UI components

**Typography:**

- Always use `font-family: 'Inter', system-ui, sans-serif` with `-webkit-font-smoothing: antialiased`
- Page titles: `text-2xl font-bold text-slate-100`
- Card headings: `text-base font-semibold text-slate-200`
- Body/description text: `text-sm text-slate-300` (on card surfaces) or `text-sm text-slate-400` (on page bg)
- Helper/caption: `text-xs text-slate-400` — never `text-slate-500` for readable text
- All power unit values (kW, V, A, Hz, PF, kVAR, kWh): `font-mono font-medium text-slate-200`

**Color rules:**

- Never use `text-slate-500` for any readable text — it fails WCAG AA
- Minimum text color on `slate-950` bg: `slate-400` (#94a3b8)
- Minimum text color on `slate-900/40` card bg: `slate-300` (#cbd5e1)
- `slate-500` is permitted only for decorative non-text elements (borders, dividers, disabled states, decorative axis lines)
- All placeholder text: `placeholder:text-slate-400` — never `placeholder:text-slate-500`
- Scrollbar thumb: `#475569` (slate-600)

**Accent colors — semantic rules:**

- `purple-400` / `purple-500` — primary accent, active power (kW), interactive actions, nav active
- `violet-400` — reactive power (kVAR) only
- `fuchsia-400` — peak demand and critical threshold states only; never as a general accent
- `amber-400` — voltage metric, overvoltage/undervoltage warnings
- `emerald-400` — power factor nominal, success states, within-spec indicators
- `orange-400` — alerts (user-configured notifications) only
- `red-400` — system/sensor failures only. Never use red for alert notifications.

**Power domain specifics:**

- Active power (kW / W) → `purple-400` exclusively
- Reactive power (kVAR) → `violet-400` exclusively
- Peak demand → `fuchsia-400` exclusively; render as `ReferenceLine` in charts, not a series line
- Voltage warnings → `amber-400`; voltage within spec → `emerald-400`
- All numeric readings must use `font-mono`

**Components:**

- All toggles require: `role="switch"` `aria-checked={boolean}` `aria-label="[setting name]"`
- All icon-only buttons require: `aria-label="[action]"`
- All collapsible sections require: `aria-expanded={boolean}` on the trigger
- Buttons: `rounded-lg` — not `rounded-full` or `rounded-xl`
- Cards: `rounded-2xl`
- Inputs: `rounded-lg` with `placeholder:text-slate-400`
- Tint chips/badges: `rounded-full` for pills, `rounded-md` for inline status chips

**Surfaces:**

- This is a dark-mode-only app. Always use dark backgrounds.
- Card surface: `bg-slate-900/40 border border-slate-800 rounded-2xl`
- Primary kW metric card only: may add `shadow-purple-500/20` — no other card uses this glow
- No `backdrop-blur` except on the fixed header

**Motion:**

- Always include `useReducedMotion()` check for any Framer Motion animation
- Standard duration: 200ms. Fast: 150ms. Slow: 300ms.
- Stagger delay: `i * 0.08s` for metric card grids

**Copy tone:**

- Terse, technical, data-forward
- Prefer: "Polling active", "Last reading", "ms", "kW", "240.1 V", "PF 0.94", "12 channels"
- Avoid: marketing language, decorative descriptions, emoji in UI text
- Use SI units consistently: W/kW/MW, VAR/kVAR, Wh/kWh, V, A, Hz

---

## 14. Changelog

### v1.0 (Initial)

- Derived from Hermes Style Guide (post-audit revision, 2026)
- **Primary accent shifted:** `cyan-400`/`cyan-500` → `purple-400`/`purple-500`
- **Secondary accent:** `violet-400` retained; now mapped to reactive power (kVAR)
- **New accent added:** `fuchsia-400` — peak demand and critical threshold states
- **Metric color map:** rewritten for power domain (kW, kVAR, V, A, PF, peak demand)
- **Download/Upload/Ping/Jitter** metric slots replaced with **Active Power / Reactive Power / Voltage / Power Factor**
- **Chart series:** updated for power domain; peak demand rendered as `ReferenceLine`
- **Settings section icons:** updated to power-monitoring contexts
- **Logo & Brand Rules:** new Argus eye motif defined; circuit traces carry power metric colors
- **Event Log** replaces Result Log; fault rows, peak demand rows, and alert-triggered rows specified
- **Copy tone:** SI units and power-domain microcopy conventions added
- All Hermes accessibility rules inherited unchanged (slate-500 text prohibition, scrollbar thumb, card body text minimums)

---

### Argus Style Guide · v1.0 · 2026
