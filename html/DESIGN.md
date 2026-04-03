# Design System Specification: The Intelligence Command Center

## 1. Overview & Creative North Star: "The Digital Curator"
This design system is built to transform complex marketing data into an authoritative, editorial experience. Our Creative North Star is **"The Digital Curator."** 

Unlike standard dashboards that feel like a collection of disparate widgets, this system treats data as a high-end publication. We move beyond the "template" look by utilizing **intentional asymmetry** and **tonal depth**. The UI should feel like a high-performance mission control center—precise, fast, and undeniably premium. We replace rigid, boxy structures with a "layered glass" philosophy, where information density is balanced by sophisticated breathing room and a strict rejection of traditional structural lines.

---

## 2. Colors: Tonal Depth & The No-Line Rule
We utilize a deep, charcoal-based palette to reduce eye strain and establish a professional "late-night" command center atmosphere.

### The "No-Line" Rule
**1px solid borders are strictly prohibited for sectioning.** To define boundaries, designers must use background color shifts or tonal nesting. 
- **Surface Hierarchy:** Use `surface_container_lowest` for the base canvas.
- **Nesting:** Place `surface_container` modules on top of the base. For inner-module nesting (like a search bar inside a header), use `surface_container_high`.
- **Glass & Gradient:** Floating panels (modals, dropdowns) must use a semi-transparent `surface_bright` with a `backdrop-filter: blur(20px)`. Main CTAs should utilize a subtle linear gradient from `primary` (#ffb693) to `primary_container` (#f56600) to add a "liquid" premium feel.

### Key Tokens:
- **Primary (The Pulse):** `#ffb693` (A sophisticated, vibrant orange for action and attention).
- **Surface Base:** `#121315` (The charcoal foundation).
- **Accent (Tertiary):** `#4cd6ff` (Used sparingly for secondary data streams or "Cool" metrics).

---

## 3. Typography: Precision Editorial
We pair **Manrope** (Display/Headline) with **Inter** (Body/Labels) to create a balance between brand character and technical precision.

- **Display & Headlines (Manrope):** These should feel authoritative. Use `headline-lg` for major section titles with a slightly tighter letter-spacing (-0.02em) to mimic high-end print.
- **Body & Labels (Inter):** Designed for maximum legibility in data-dense environments. `label-sm` is your workhorse for metadata and sparkline captions.
- **French Context:** Given the longer average word length in French, ensure `title-sm` and `body-md` have generous line-heights (1.5x) to maintain vertical rhythm.

---

## 4. Elevation & Depth: Tonal Layering
Depth is not achieved through shadows alone, but through the physical "stacking" of color values.

- **The Layering Principle:** 
    1. Base: `surface_dim`
    2. Content Blocks: `surface_container_low`
    3. Interactive Elements: `surface_container_high`
- **Ambient Shadows:** Shadows are reserved for floating elements only. Use a 24px blur, 0px offset, at 6% opacity using a tint of `on_surface`. It should feel like a soft glow rather than a drop shadow.
- **The "Ghost Border" Fallback:** If accessibility requires a stroke (e.g., in high-contrast modes), use `outline_variant` at **15% opacity**. Never use a 100% opaque border.

---

## 5. Components: Professional Primitives

### Buttons
- **Primary:** Gradient fill (`primary` to `primary_container`). White text (`on_primary_fixed`). 4px corner radius (`sm`).
- **Secondary:** Ghost style. No background, `outline_variant` (20% opacity) border.
- **Tertiary:** Text-only, `primary` color, bold weight.

### Input Fields
- **State:** No border. Use `surface_container_highest` for the background.
- **Focus:** Transition the background to `surface_bright` and add a subtle 1px "Ghost Border" of `primary` at 40% opacity.

### Data Visualization (The Pulse Components)
- **Sparklines:** Use `primary` for growth and `error` (#ffb4ab) for decline. Fill the area under the line with a 5% opacity gradient of the same color.
- **Status Indicators:** Small, 6px circular pips. Use `tertiary` (#4cd6ff) for "Active/Running" to distinguish from "Success."
- **Gauges:** Semi-circular, using `surface_container_highest` as the track and `primary` as the indicator.

### Cards & Lists
- **No Dividers:** Prohibit the use of horizontal lines between list items. Use 8px of vertical white space or a hover state change to `surface_container_highest`.
- **Anatomy:** Every card must have a `label-sm` category header in `on_surface_variant` (French: "CATÉGORIE") before the main `title-md` data point.

---

## 6. Do's and Don'ts

### Do:
- **Use "Space as Structure":** Rely on the 4px/8px grid to align elements rather than boxes.
- **Contextual French:** Ensure buttons like "En savoir plus" or "Télécharger le rapport" have enough horizontal padding (minimum 24px) for longer text.
- **Subtle Motion:** Use 200ms "Ease-Out" transitions for hover states to reinforce the "Fast" mission-control feel.

### Don't:
- **Don't use pure black (#000):** It destroys the depth of the charcoal `surface` tokens.
- **Don't use high-contrast dividers:** They clutter the "data-dense" environment. If you need a break, use a 1px gap showing the background `surface` color.
- **Don't use rounded corners over 12px:** Stay within the `sm` (4px) to `md` (6px) range for a technical, precise aesthetic. Large rounds feel too consumer-focused.

### "Mission Control" Checklist
- [ ] Is the data readable without squinting?
- [ ] Does the screen feel like a single cohesive layer or a mess of boxes?
- [ ] Is the `primary` orange used only for the most important actions?
- [ ] Are the "Ghost Borders" invisible at a glance but visible when searching for them?