# PlexusChat

## Overview
PlexusChat is a multi-company customer service SaaS platform for WhatsApp, Instagram, Facebook Messenger, Telegram, and RCS. The interface manages high-volume ticket queues, kanban boards, real-time messaging, campaigns, and analytics dashboards — all within a single multi-tenant workspace.

The aesthetic is calm and professional: a distinctive Deep Teal palette conveys trust and focus without sterility. Information density is high but organized — operators handle dozens of simultaneous conversations, so visual hierarchy and quick scanning are critical. Light-mode only. No decorative gradients or illustrations.

## Colors
- **Primary 500** (#31927F): Mid Gradient — main CTAs, active states, links, focus rings, ticket open status
- **Primary 200** (#9CE9CD): Mint Core — success state backgrounds, accent highlights, dark mode accent
- **Primary 800** (#0E4F41): Deep Teal Network — dark accent, badge text on success backgrounds
- **Secondary 500** (#6366F1): Indigo — secondary actions, flow builder queue nodes, info highlights
- **Background** (#F7F7F7): Page background — warm off-white
- **Surface** (#F7F7FF): Cards, panels, modals — slightly cooler white
- **Neutral 50** (#F8FAFC): Subtle section backgrounds
- **Neutral 200** (#E2E8F0): Borders, dividers, input edges
- **Neutral 500** (#64748B): Muted text, placeholders, timestamps, closed ticket status
- **Neutral 800** (#1E293B): Primary text — body, labels, headings
- **Neutral 900** (#0F172A): Display text — near-black for maximum contrast
- **Success** (#31927F / bg rgba(49,146,127,0.12)): Ticket open, CONNECTED, positive indicators
- **Warning** (#F59E0B / bg rgba(245,158,11,0.14)): Ticket pending, qrcode, due-soon states
- **Error** (#EF4444 / bg rgba(239,68,68,0.12)): Destructive actions, DISCONNECTED, hot lead score
- **Info** (#3B82F6 / bg rgba(59,130,246,0.12)): Cold lead score, informational banners

### Channel Colors
- WhatsApp: `#31927F` (matches primary — intentional brand alignment)
- Instagram: `#E1306C`
- Facebook: `#1877F2`
- Telegram: `#2AABEE`
- RCS: `#4285F4`
- Integration/API: `#64748B`

### Lead Score Colors
- Hot: `#EF4444` (error red)
- Warm: `#F59E0B` (warning amber)
- Cold: `#3B82F6` (info blue)

## Typography
- **Font**: Inter — loaded from system or Google Fonts. Fallback: Roboto, Helvetica Neue, Arial.

Inter is used at all scales — a single humanist sans-serif chosen for legibility at small sizes (12–14px), critical in dense ticket lists and message timestamps. No display font, no serif — the product is a tool, not an editorial experience.

Type scale: h1 32px, h2 24px, h3 20px, h4 18px, h5 16px, h6 14px, body1 14px, body2 13px, caption 12px, tiny 11px.

Weights: regular (400) for body, medium (500) for UI labels and metadata, semibold (600) for headings and badge text, bold (700) for display numbers (metric cards, counters).

Line heights: tight 1.2 (headings), snug 1.35 (subheads), normal 1.5 (body), relaxed 1.6 (chat messages), loose 1.8 (long-form content).

## Elevation
Cards rest flat with a 1px `#E2E8F0` border and gain `0 4px 6px -1px rgba(0,0,0,0.07)` on hover with a subtle lift. Modals use `0 20px 25px -5px rgba(0,0,0,0.08)` with a `rgba(15,23,42,0.5)` backdrop overlay. The sidebar is flat — no shadow, only a 1px right border. Dropdowns and popovers use `0 10px 15px -3px rgba(0,0,0,0.07)`. Focus states use a 3px teal ring (`0 0 0 3px rgba(49,146,127,0.35)`) instead of a box shadow. Kanban cards being dragged receive a teal glow: `0 12px 24px -4px rgba(49,146,127,0.22), 0 4px 8px -2px rgba(49,146,127,0.12)` combined with a `-2px` vertical lift — immediately distinguishing the dragged card from resting cards.

## Components
- **Buttons**: Primary uses `#31927F` fill with white text, 8px radius, semibold weight, 20px horizontal padding, 8px vertical padding. Secondary uses transparent bg with 1px `#E2E8F0` border. Danger uses `#EF4444` fill. Ghost has no border or bg. Loading state replaces label with a spinner. Minimum touch target 44px (WCAG 2.5.5). All variants support `startIcon` and `endIcon`.
- **Cards**: `#F7F7FF` surface, 1px `#E2E8F0` border, 14px radius, 20px padding. Kanban ticket cards show a colored left stripe (4px) per ticket channel. Hover lifts 2px with increased shadow. Metric cards display a large bold number (700 weight), a label, and a trend indicator.
- **Inputs**: 1px `#E2E8F0` border, surface background, variable radius (6px default, 12px in filter contexts), Inter 14px, 10px vertical padding. Focus: border turns `#31927F` with a 3px teal ring. Error: border turns `#EF4444` with a red ring (`rgba(239,68,68,0.35)`). Placeholder text in `#94A3B8`.
- **Tags / Chips**: Pill shape (9999px radius), 26px fixed height, 12px horizontal padding, 12px font size, semibold weight, 100px min-width, 180px max-width with ellipsis truncation for long names. Delete icon fixed at 14px. Color is dynamic per tag — text color calculated via YIQ luminance formula to guarantee WCAG AA contrast over any background color.
- **Badges / Status Pills**: Pill shape (9999px), semantic color combos with guaranteed contrast ≥ 4.5:1. Open/connected: teal bg + Deep Teal text. Pending/warning: amber bg + dark orange text. Closed/neutral: slate bg + dark slate text. Error/hot: red bg + dark red text. Info/cold: blue bg + dark blue text. All badge combos tested individually — not derived by formula.
- **Sidebar Navigation**: 256px expanded, 64px collapsed (icon-only). Groups items by section (Tickets, Contacts, Campaigns, Reports, Settings). Active item: 3px teal left bar (`#31927F`) + `rgba(49,146,127,0.08)` background tint. Hover: `rgba(49,146,127,0.05)`. Icons 20px paired with labels on desktop, icons only on collapsed. Notification counts use circular red badges.
- **Tabs (underline style)**: Active tab: `#31927F` text + 2px bottom border in teal. Inactive: `#64748B` text, no underline. Hover: `rgba(49,146,127,0.06)` background. No filled or pill tab style — underline only.
- **Kanban Cards**: 4px colored left stripe per channel (channel color from `tokens.colors.channels.*`). Column gap 16px. Drag state: teal glow shadow (`0 12px 24px -4px rgba(49,146,127,0.22)`) + `-2px` translateY lift. Cards support drag-and-drop reorder within and between columns.
- **Chat Bubbles**: Outgoing messages right-aligned, teal bg (`#31927F`), white text. Incoming left-aligned, surface bg, neutral text. Timestamps in caption (12px), neutral 400. Media messages show inline preview with a download affordance. Read receipts use double-checkmark icons with teal fill when seen.
- **Data Tables**: Sortable headers, alternating row hover, sticky first column for contact name. Pagination below. Empty state uses an inline illustration variant (search, error, or generic empty).
- **Channel Icons**: Fixed icon per channel. WhatsApp: filled circle green. Instagram: gradient pink-purple. Facebook: blue F. Telegram: paper plane blue. RCS: Google-blue diamond. All 20px default, scaling to 16px in compact contexts.
- **Flow Builder Nodes**: Each node type has a fixed color: Start (teal), Message (blue), Menu (amber), Queue (indigo), User (deep teal), End (red). Node bg is a 10% opacity tint of the border color.

## Spacing
- Base unit: 8px
- Scale: 0, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 64, 80, 96px
- Component padding (buttons): 8px vertical, 20px horizontal
- Component padding (cards): 20px all sides
- Filter bar padding: 4px
- Section spacing: 16px mobile, 24px tablet, 32px desktop
- Card grid gap: 16px mobile, 24px desktop

## Border Radius
- 4px: Inline code, small badges, tiny chips
- 6px: Default inputs, selects, buttons (inner)
- 8px: Buttons, dropdowns, action menus
- 10px: Standard MUI components (inherited baseline)
- 12px: Filter input fields
- 14px: Cards, kanban columns
- 16px: Modals, dialogs
- 20px: Large surface panels
- 9999px: Tags, chips, status pills, avatars, progress bars

## Accessibility
- Focus ring: `0 0 0 3px rgba(49,146,127,0.35)` — teal, 3px, applied to all interactive elements
- Danger focus ring: `0 0 0 3px rgba(239,68,68,0.35)` — red, for destructive actions
- Minimum touch target: 44×44px (WCAG 2.5.5) — applied to all icon buttons
- All badge color combinations have contrast ratio ≥ 4.5:1 (WCAG AA) — verified individually
- Decorative icons carry `aria-hidden="true"`. Informational icons use `role="img"` + `aria-label`
- All modals use `aria-labelledby` and `aria-describedby` with unique per-instance IDs
- Skeleton loaders carry `role="status" aria-busy="true" aria-live="polite"`
- Animations respect `prefers-reduced-motion: reduce`

## Component Token Reference

Key values from `tokens.js` for implementation reference:

```
// Shadows
tokens.shadows.drag        → 0 12px 24px -4px rgba(49,146,127,0.22), 0 4px 8px -2px rgba(49,146,127,0.12)

// Sidebar
tokens.components.sidebar.widthExpanded   → 256px
tokens.components.sidebar.widthCollapsed  → 64px
tokens.components.sidebar.activeBarWidth  → 3px
tokens.components.sidebar.activeBarColor  → #31927F
tokens.components.sidebar.activeBg        → rgba(49,146,127,0.08)
tokens.components.sidebar.hoverBg         → rgba(49,146,127,0.05)

// Tabs
tokens.components.tabs.activeBarHeight → 2px
tokens.components.tabs.activeColor     → #31927F
tokens.components.tabs.inactiveColor   → #64748B
tokens.components.tabs.hoverBg         → rgba(49,146,127,0.06)

// Kanban
tokens.components.kanban.cardStripeWidth → 4px
tokens.components.kanban.columnGap       → 16px
tokens.components.kanban.dragShadow      → (same as shadows.drag)
tokens.components.kanban.dragTranslateY  → -2px

// Cards / Modal / Button / Tag
tokens.components.card.radius    → 14px
tokens.components.card.padding   → 20px
tokens.components.modal.radius   → 16px
tokens.components.button.radius  → 8px
tokens.components.tag.height     → 26px
tokens.components.tag.minWidth   → 100px
tokens.components.tag.maxWidth   → 180px
```

## Do's and Don'ts
- Do use `#31927F` only for interactive and active states — never as a decorative fill
- Do maintain the 8px spacing grid for all component padding, margins, and gaps
- Do use Inter at all scales — never introduce a second typeface
- Do use the pre-defined badge combos from `tokens.badges` — never compose your own color pairs without WCAG testing
- Do use the `getContrastText(bgColor)` YIQ utility for any element with a dynamic background color (tags, avatars, custom color indicators)
- Do filter every database query by `companyId` — this is a multi-tenant product
- Don't use pure black (#000000) or pure white (#FFFFFF) — always reference the neutral palette
- Don't add shadows to static elements — reserve elevation for hover, focus, and overlays
- Don't use more than two font weights on a single screen
- Don't place more than one primary (teal filled) button in the same view section
- Don't use `useMediaQuery` directly — always use the `useResponsive()` hook for consistent breakpoints
- Don't hardcode hex values in component files — always reference `tokens.colors.*`