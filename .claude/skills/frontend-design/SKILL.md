---
name: frontend-design
description: Designs and builds modern, production-ready UI pages and components for Spendly, a personal expense tracker (Flask + Jinja2 + vanilla CSS/JS, repo https://github.com/campusx-official/spendly), matching its existing design system. Use this skill whenever the user asks to design, create, build, redesign, improve, restyle, or polish any Spendly page, screen, section, or component — phrasings like "design the ___ page", "create UI for ___", "build a component for ___", "redesign / improve ___", "make ___ look better", or anything about Spendly's frontend, templates, layout, CSS, icons, or visual polish. Also use it for UI work in a Flask/Jinja expense or budgeting app even if Spendly isn't named, whenever the conversation is clearly about this project.
---

# Spendly UI Designer

Spendly is a personal expense tracker built with Flask, server-rendered Jinja2 templates, vanilla CSS, and vanilla JS. Your job is to produce UI that looks like it was always part of Spendly: a calm, editorial, fintech-style product — not a generic Bootstrap page, and not React/Tailwind output that can't be dropped into the codebase.

## Stack constraints (non-negotiable)

These come from the project's own CLAUDE.md. Breaking them produces code the user can't merge.

- **Templates:** every page is a new `templates/<page>.html` that `{% extends "base.html" %}` and fills `title`, `head`, `content`, and optionally `scripts` blocks. Never rewrite the navbar or footer — `base.html` owns them.
- **Links:** use `url_for()` for every internal link and form action. Never hardcode URLs.
- **CSS:** page-specific styles go in a new `static/css/<page>.css`, linked from the `head` block. No inline `<style>` tags, and avoid inline `style=""` except for truly dynamic values (e.g. a bar width from data).
- **JS:** vanilla only, and only when the interaction needs it. No React, Vue, jQuery, Tailwind, Bootstrap, or npm packages.
- **No new dependencies.** Icons are inline SVG (see Icons below), not a CDN script or package.

## Before you design: look at what exists

Consistency is the most important quality bar. If you can see the repo or the user has shared files, open `templates/base.html`, `static/css/style.css`, and the closest existing page (usually `profile.html` + `profile.css` for dashboard-style pages, `add_expense.html` for forms) before writing anything. Reuse their classes instead of inventing parallel ones.

If you can't see the code and the request touches an existing page, ask the user for a screenshot or the relevant template first — one screenshot saves several rounds of revision. For brand-new pages, you can proceed using the design system in `references/design-system.md`, which captures Spendly's actual tokens and component classes.

**Read `references/design-system.md` before writing CSS.** It lists the real CSS variables, existing reusable classes (buttons, cards, forms, tables, badges), and layout patterns. Reuse those; don't redefine them.

## Design language

Spendly's look is warm and editorial rather than cold-corporate:

- Warm off-white page (`--paper`), white cards (`--paper-card`), near-black ink text, deep green accent (`--accent`), amber secondary (`--accent-2`).
- Headings and big numbers in `--font-display` (DM Serif Display); everything else in `--font-body` (DM Sans).
- Cards: white background, `1px solid var(--border)`, `var(--radius-md)`, very soft shadow `0 2px 8px rgba(0,0,0,0.04)`.
- Spacing on an 8px rhythm: prefer `0.5rem` steps (0.5, 1, 1.5, 2, 3rem). Small 4px steps (0.25rem, 0.75rem) are fine inside components.
- Amounts use `₹`, `font-variant-numeric: tabular-nums`, and are right-aligned in tables.
- Small uppercase labels (0.7–0.72rem, weight 600, letter-spacing ~0.08em, `--ink-muted`) above values.
- Primary buttons are ink-black and turn green on hover. Restraint over decoration: no gradients, glows, or heavy shadows on core app pages.

Avoid: generic/dated UI (default blue buttons, heavy borders, cramped tables), random new colors or radii, emoji as icons in app UI, and clutter. If you need a new color (e.g. a new category), add it as a CSS variable in the page's `:root` block next to the existing category tokens.

## UX expectations

Every page should handle its real states, because users actually hit them:

- **Empty state** — friendly message plus the obvious next action (usually "Add expense").
- **Validation errors** — re-fill the form from `form.get(...)` and show errors with the existing `.auth-error` or flash styles.
- **Destructive actions** — confirm before delete (the project uses a POST form with `onsubmit="return confirm(...)"`).
- **Responsive** — stack grids to one column under ~900px; make tables scroll horizontally inside a wrapper under ~600px. Match the existing breakpoints (900px, 600px).
- **Accessibility** — real `<label for>` on inputs, buttons that are `<button>`, icon-only buttons get `aria-label`, decorative SVGs get `aria-hidden="true"`, visible focus states (border to `--accent`).

## Icons

Use Lucide icons (Heroicons outline is an acceptable fallback) as **inline SVG** so there's no new dependency:

```html
<svg class="icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" stroke-width="2" stroke-linecap="round"
     stroke-linejoin="round" aria-hidden="true">
  <!-- Lucide path data, e.g. "plus": -->
  <path d="M5 12h14"/><path d="M12 5v14"/>
</svg>
```

Icons inherit color via `currentColor`, so style them through the parent. Use them where they add meaning — actions (add, edit, delete, filter, download), category markers, stat cards — not as decoration on every line. Name the Lucide icon in a comment so the user can swap it later. Only use path data you're confident is correct; for an icon you're unsure about, pick a simpler one.

## Output format

Structure every response like this:

### 1. UI structure (brief)
A short outline of the layout and key sections, then 2–4 bullets on the important UX decisions and why (e.g. "Totals sit above the table so the answer to 'how much did I spend?' is visible without scrolling"). Keep it scannable — this is a plan, not an essay.

### 2. Code
One clearly labeled block per file, with its path as a heading:

- `templates/<page>.html` — extends `base.html`
- `static/css/<page>.css` — page-specific styles only, reusing global variables and classes
- `static/js/<page>.js` or additions to `static/js/main.js` — only if needed

For a component added to an existing page, show only the new markup and CSS plus exactly where it goes, rather than the whole file. Code should be complete and paste-ready: no "..." placeholders, no lorem ipsum (use realistic Indian-rupee expense data in examples), minimal boilerplate, and short section comments in the CSS matching the existing `/* --- Section --- */` banner style.

### 3. Integration notes
What the template expects from the route: the template variables and their shapes (e.g. `expenses: list of {id, date, description, category, amount}`), any `url_for` endpoints it references that must exist, and anything the user must add to `app.py`. Don't write backend code unless asked — the project builds routes in separate steps — but make the contract explicit.

Keep prose outside these three sections to a sentence or two. The user wants working UI, not an unstructured dump of code or a long design lecture.

## Redesign / improve requests

When asked to improve an existing page: first name the specific problems you see (hierarchy, spacing, missing states, inconsistency with the rest of the app), then deliver the revised code. Keep the existing class names and template variables wherever possible so the backend and other pages keep working; if you must rename something, say so in the integration notes.
