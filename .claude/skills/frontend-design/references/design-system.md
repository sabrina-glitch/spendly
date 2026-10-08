# Spendly design system reference

Extracted from the Spendly repo (`static/css/style.css`, `static/css/profile.css`, `templates/base.html`). These are the real values — reuse them. If the user's copy of the repo differs, their code wins; check it.

## Contents
1. CSS variables
2. Fonts
3. Global layout from base.html
4. Reusable classes (buttons, forms, cards, tables, badges, flashes)
5. Page layout patterns
6. Breakpoints

---

## 1. CSS variables (`:root` in style.css)

```css
--ink: #0f0f0f;          /* primary text, primary button bg */
--ink-soft: #2d2d2d;     /* body text in cards, labels */
--ink-muted: #6b6b6b;    /* secondary text, uppercase labels */
--ink-faint: #a0a0a0;    /* tertiary text, placeholders */
--paper: #f7f6f3;        /* page background, input background */
--paper-warm: #f0ede6;   /* alternate section background */
--paper-card: #ffffff;   /* card background */
--accent: #1a472a;       /* deep green: hover, focus, active, brand */
--accent-light: #e8f0eb;
--accent-2: #c17f24;     /* amber secondary */
--accent-2-light: #fdf3e3;
--danger: #c0392b;
--danger-light: #fdecea;
--border: #e4e1da;
--border-soft: #eeebe4;  /* row dividers, section title underline */

--font-display: 'DM Serif Display', Georgia, serif;
--font-body: 'DM Sans', system-ui, sans-serif;

--max-width: 1200px;
--auth-width: 440px;     /* narrow centered forms */

--radius-sm: 6px;        /* buttons, inputs */
--radius-md: 12px;       /* cards */
--radius-lg: 20px;       /* large hero surfaces */
```

Category tokens (defined in profile.css — copy into a new page's CSS if you need them there):

```css
--cat-food: var(--accent);            --cat-food-bg: var(--accent-light);
--cat-transport: var(--accent-2);     --cat-transport-bg: var(--accent-2-light);
--cat-bills: #5b7fa6;                 --cat-bills-bg: #e8ecf4;
--cat-health: #b94040;                --cat-health-bg: #fef0f0;
--cat-entertainment: #8b5e83;         --cat-entertainment-bg: #f0ebf4;
--cat-shopping: var(--accent-2);      --cat-shopping-bg: var(--accent-2-light);
--cat-other: var(--ink-faint);        --cat-other-bg: var(--border-soft);
```

## 2. Fonts

Loaded in base.html from Google Fonts: DM Serif Display (400, italic) and DM Sans (300–600). Use display for page titles, card titles, avatar initials, and large stat numbers; body for everything else.

## 3. Global layout (base.html)

- Sticky `.navbar` (60px tall, `--paper` background, bottom border) with `.nav-brand` (◈ + "Spendly") and `.nav-links`. Logged-in links: Analytics, Dashboard (`profile`), Sign out. Active link uses `.nav-link-active`.
- `<main class="main-content">` wraps a flash block (`.flash-container` > `.flash.flash-{category}`) and `{% block content %}`.
- Footer with brand and Terms/Privacy links.
- Blocks available: `title`, `head`, `flash`, `content`, `scripts`.

Page shell pattern:

```html
{% extends "base.html" %}
{% block title %}Page Name — Spendly{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/page.css') }}">
{% endblock %}
{% block content %}
<div class="page-name-page">
  <div class="page-name-inner"> ... </div>
</div>
{% endblock %}
```

with

```css
.page-name-page  { padding: 3rem 2rem 5rem; }
.page-name-inner { max-width: var(--max-width); margin: 0 auto;
                   display: flex; flex-direction: column; gap: 1.5rem; }
```

## 4. Reusable global classes (style.css)

**Buttons**
- `.btn-primary` — ink bg, paper text, `0.65rem 1.5rem` padding, radius-sm, 0.9rem/500; hover → `--accent`.
- `.btn-ghost` — transparent, `--ink-soft` text, 1px `--border`; hover → ink border/text.
- `.btn-delete` — transparent, danger text + border, small (`0.35rem 0.75rem`); hover → `--danger-light` bg.
- `.btn-submit` — full-width ink button for forms; hover → `--accent`.

**Forms**
- `.form-group` (margin-bottom 1.25rem) > `label` (0.85rem, 500, `--ink-soft`) + `.form-input`.
- `.form-input` — full width, `0.6rem 0.875rem` padding, 1px `--border`, radius-sm, `--paper` background; focus → border `--accent`.
- `.form-select` (add_expense.css) — custom chevron via SVG data URI.
- `.form-textarea`, `.field-optional` (small faint "(optional)" text).
- `.auth-error` — danger-light box for form-level errors.

**Narrow form-page layout** (login, register, add/edit expense): `.auth-section` > `.auth-container` (`--auth-width`) > `.auth-header` (`.auth-title`, `.auth-subtitle`) + `.auth-card` + `.auth-switch` (back link).

**Cards** (profile.css shared treatment):
```css
background: var(--paper-card);
border: 1px solid var(--border);
border-radius: var(--radius-md);
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
```
Used by `.profile-header-card`, `.stat-card`, `.profile-section` (padding 1.75rem).

**Section titles**: `.section-title` (display font, 1.15rem, bottom border `--border-soft`), `.section-title-row` for a title with an action on the right.

**Stat cards**: `.stat-card` > `.stat-label` (uppercase 0.72rem/600, letter-spacing 0.08em, muted) + `.stat-value` (display font, 1.75rem, tabular-nums).

**Tables**: `.tx-table-wrapper` (overflow-x auto) > `.tx-table`. Headers: 0.7rem uppercase muted. Cells: `0.8rem 0.75rem` padding, `--border-soft` dividers, hover row → `--paper`. `.tx-amount` right-aligned, tabular-nums, 500. `.tx-date` muted, nowrap. `.tx-empty` for the empty row.

**Badges**: `.cat-badge.cat-badge--{category|lower}` — pill (radius 999px), 0.72rem/600, category color on category bg.

**Category bars**: `.cat-row` > `.cat-row-header` + `.cat-bar-track` > `.cat-bar.cat-bar--{cat}` with inline width %.

**Filters**: `.filter-bar`, `.filter-preset-btn` (+ `--active`), `.filter-date-input`, `.filter-apply-btn` on the profile page.

**Flashes**: `.flash-error`, `.flash-success`, `.flash-warning`, `.flash-info`.

## 5. Page layout patterns

- **Dashboard/profile**: header card → filter bar → 3-column stats grid → `2fr 1fr` grid of sections (table + breakdown).
- **Form pages**: narrow centered `auth-*` layout.
- **Landing**: marketing hero + features (landing.css) — the only place where more expressive styling is appropriate.

## 6. Breakpoints

Existing media queries use `max-width: 900px` (grids collapse to one column, hero stacks) and `max-width: 600px` (navbar hides non-CTA links, tighter padding). Use the same two.
