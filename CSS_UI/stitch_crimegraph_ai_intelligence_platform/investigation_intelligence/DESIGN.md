---
name: Investigation Intelligence
colors:
  surface: '#111318'
  surface-dim: '#111318'
  surface-bright: '#37393e'
  surface-container-lowest: '#0c0e12'
  surface-container-low: '#1a1c20'
  surface-container: '#1e2024'
  surface-container-high: '#282a2e'
  surface-container-highest: '#333539'
  on-surface: '#e2e2e8'
  on-surface-variant: '#c2c6d8'
  inverse-surface: '#e2e2e8'
  inverse-on-surface: '#2f3035'
  outline: '#8c90a1'
  outline-variant: '#424656'
  surface-tint: '#b3c5ff'
  primary: '#b3c5ff'
  on-primary: '#002b75'
  primary-container: '#0066ff'
  on-primary-container: '#f8f7ff'
  inverse-primary: '#0054d6'
  secondary: '#d0bcff'
  on-secondary: '#3c0091'
  secondary-container: '#571bc1'
  on-secondary-container: '#c4abff'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#008259'
  on-tertiary-container: '#e1ffec'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dae1ff'
  primary-fixed-dim: '#b3c5ff'
  on-primary-fixed: '#001849'
  on-primary-fixed-variant: '#003fa4'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#111318'
  on-background: '#e2e2e8'
  surface-variant: '#333539'
typography:
  display:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  panel-width: 400px
  sidebar-width: 64px
---

## Brand & Style
The design system is engineered for analytical rigor, objectivity, and precision. It prioritizes the clear presentation of complex relational data over decorative flair. The aesthetic is a refined **Corporate/Modern** interpretation of a high-density intelligence tool, moving away from "sci-fi" cliches toward a functional, authoritative interface.

The brand personality is **Credible and Advanced**, utilizing a high-contrast dark mode to reduce eye strain during prolonged investigative sessions while ensuring critical alerts are immediately visible. The UI remains "out of the way," focusing on the clarity of evidence and the speed of the investigator's workflow.

## Colors
The palette is centered on a deep charcoal and navy foundation to establish a professional, low-light environment. 

- **Primary (Investigation Blue):** Used for active states, primary actions, and key navigation.
- **Insight (Purple/Indigo):** Reserved specifically for AI-generated suggestions, automated summaries, and inferred connections.
- **Semantic Feedback:** Emerald (Confirmed/Success), Amber (Warning/Lead), and Rose (Danger/High Priority) follow standard investigative protocols for risk assessment.
- **Neutrals:** A range of slates from `slate-950` (#0A0C10) for backgrounds to `slate-50` for primary text, ensuring a logical visual hierarchy across surfaces and borders.

## Typography
This design system utilizes a dual-font approach to distinguish between narrative content and technical data.

1. **Inter:** The primary workhorse for all interface labels, headlines, and body text. It provides exceptional legibility at small sizes.
2. **JetBrains Mono:** Used for specialized data points including timestamps, hashes, coordinates, IP addresses, and confidence percentages. The monospaced nature ensures that vertical alignment is maintained in data-heavy tables.

**Hierarchical Rules:**
- Use `label-caps` for section headers in side panels.
- Use `data-mono` for any value extracted from evidence or metadata.
- Headlines should remain concise and objective.

## Layout & Spacing
The layout follows a **Fixed-Fluid Hybrid** model designed for high-density information display.

- **Global Layout:** A persistent slim left sidebar (64px) for navigation, a fluid central "Graph or Map" canvas, and a collapsible right Side Panel (400px) for entity details.
- **Rhythm:** A 4px baseline grid ensures tight, professional spacing. 
- **Density:** Information density is "High." Gutters are kept at 16px to maximize the amount of visible data on a standard 1080p monitor without causing visual clutter.
- **Responsive:** On smaller screens (Tablets), the side panels transition to full-screen overlays; however, the desktop experience is the primary environment for investigation.

## Elevation & Depth
In this dark-mode environment, depth is communicated through **Tonal Layering** and **Low-Contrast Outlines** rather than heavy shadows.

- **Level 0 (Background):** #0A0C10. The primary canvas color.
- **Level 1 (Surfaces):** #161B22. Used for cards, side panels, and header bars.
- **Level 2 (Popovers/Modals):** #1C2128. Slightly lighter to suggest proximity to the user.
- **Borders:** All surfaces use a 1px solid border (#30363D) to define edges clearly against the dark background. 
- **Shadows:** Only used on high-level modals to provide a subtle "glow" effect using a low-opacity navy tint (#000000).

## Shapes
The shape language is **Soft (0.25rem)**, emphasizing a structured and "engineered" feel. 

- **Buttons & Inputs:** Use the standard `rounded` (4px) setting.
- **Graph Nodes:** These are exceptions. Specific shapes correlate to entity types (Circles for people, Rectangles for cases) to aid in rapid visual scanning.
- **Evidence Cards:** Use `rounded-lg` (8px) to subtly group complex metadata chunks.
- **Indicators:** Confidence gauges and status pips use circular (fully rounded) shapes for immediate recognition.

## Components
Consistent implementation of these core components ensures a cohesive investigative experience:

- **Evidence Cards:** Use a Level 1 surface with a 1px border. The top-right corner must always display the "Confidence Percentage" in JetBrains Mono. Source references should be listed as footer tags.
- **Graph Nodes:** Must contain a centered icon. The color of the node's border indicates its status (e.g., primary blue for active selection, amber for a potential lead).
- **Confidence Gauges:** A thin horizontal track with a colored fill (Primary or Insight Purple) indicating the AI's certainty level.
- **Buttons:** 
  - *Primary:* Solid Investigation Blue with white text. 
  - *Secondary:* Ghost style with 1px border (#30363D) and primary blue text.
  - *Action:* Small (28px height) for high-density toolbars.
- **Side Panels:** Use a vertical "Header-Body-Footer" structure. The header contains the Entity Name and Type; the body is a scrollable list of metadata; the footer contains action buttons (e.g., "Add to Case").
- **Timeline Markers:** A vertical 2px line with circular pips. Each pip's color corresponds to the event type (e.g., Rose for a high-priority incident).
- **Input Fields:** Dark background (#0A0C10) with a subtle inset border. Active focus state uses a 1px Investigation Blue glow.