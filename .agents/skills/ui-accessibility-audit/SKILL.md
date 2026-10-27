---
name: ui-accessibility-audit
description: >-
  Audits, refactors, and enhances web application user interfaces for accessibility (WCAG 2.1 AA/AAA),
  visual hierarchy, typography, color themes, and mobile ergonomics. Use this skill when evaluating
  any dashboard or web application for ease of access, color contrast, responsive layout, font legibility,
  or multi-theme switching.
---

# UI/UX & Accessibility (A11y) Audit and Enhancement Skill

This skill provides a systematic methodology and implementation playbook for auditing and enhancing web applications, dashboards, and PWAs to achieve top-tier accessibility (WCAG 2.1 AA/AAA), optimal visual ergonomics, responsive layouts, and robust theming.

---

## 1. The 6-Pillar UI/UX & Accessibility Framework

When reviewing or enhancing any web application interface, evaluate and implement improvements across these six dimensions:

```
+-----------------------------------------------------------------------------------+
|                           6-PILLAR UI/UX AUDIT MATRIX                             |
+-----------------------------------------------------------------------------------+
| 1. Accessibility (a11y)  | WCAG 2.1 AA/AAA, :focus-visible, ARIA, Skip Links      |
| 2. Typography & Numbers  | Tabular numerals (tnum), font hierarchy, >= 12px text  |
| 3. Color & Themes        | Multi-theme CSS vars, 4.5:1+ contrast, dynamic charts  |
| 4. Touch & Ergonomics    | >= 44x44px touch targets, mobile day/strip navigators  |
| 5. Tables & Dense Data   | Sticky headers, instant search, category filters       |
| 6. PWA & Offline State   | Non-intrusive install banner, offline indicators       |
+-----------------------------------------------------------------------------------+
```

---

## 2. Detailed Audit Criteria & Remediation Patterns

### Pillar 1: Accessibility (a11y) & Keyboard Navigation
- **Skip-to-Content Link**: Ensure keyboard users and screen readers can immediately skip repetitive navigation or headers.
  ```html
  <a href="#main-content" class="skip-link">Skip to main content</a>
  ```
  ```css
  .skip-link {
    position: absolute;
    top: -50px;
    left: 12px;
    background: var(--accent-primary);
    color: #000;
    padding: 8px 16px;
    font-weight: 700;
    border-radius: 6px;
    z-index: 99999;
    text-decoration: none;
    transition: top 0.2s ease-in-out;
  }
  .skip-link:focus {
    top: 12px;
  }
  ```
- **Visible Focus States (`:focus-visible`)**: Never hide focus outlines without replacement. Apply high-contrast focus rings:
  ```css
  *:focus-visible {
    outline: 2px solid var(--accent-primary) !important;
    outline-offset: 2px !important;
  }
  ```
- **Semantic ARIA Labels**: Add `aria-label`, `role="region"`, `role="radiogroup"`, `aria-checked`, and `aria-hidden="true"` on decorative icons.

### Pillar 2: Typography & Numeric Data Alignment
- **Tabular Numerals for Clocks, Metrics & Paces**:
  Avoid raw unstyled monospace that looks ragged on different operating systems. Use modern tabular typography:
  ```css
  :root {
    --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    --font-mono: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", Consolas, "Liberation Mono", Menlo, monospace;
  }
  .tabular-num {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum" 1;
  }
  ```
- **Font Size Minimums**: Ensure no body or secondary labels fall below `0.75rem` (12px) to prevent eye strain and comply with accessibility benchmarks.

### Pillar 3: Dynamic Theme System & Color Contrast
- **WCAG Contrast Requirement**: Normal text requires at least **4.5:1** contrast ratio against its background; large text requires at least **3:1**.
- **Multi-Theme Implementation with CSS Custom Properties**:
  Support multiple live themes (e.g. Carbon, Midnight Athletic, High-Contrast Arctic) that seamlessly synchronize with data charts and system preferences.
  ```javascript
  function setTheme(themeName) {
    document.documentElement.setAttribute('data-theme', themeName);
    localStorage.setItem('app_theme', themeName);
    updateThemeButtons(themeName);
    if (typeof updateChartsTheme === 'function') {
      updateChartsTheme(themeName);
    }
  }
  ```

### Pillar 4: Mobile Ergonomics & Responsive Components
- **Touch Targets**: All interactive elements (buttons, filters, dismiss icons, chips) must provide a touch target of at least **44x44px** (or minimum 36px with 8px margin).
- **Week / Calendar Strips**: On small screens, avoid awkward wrapped grids (such as 4+3 for 7 days). Use a flexible 7-day strip with horizontal overflow or auto-scaling chips so the full weekly cycle remains intuitive.

### Pillar 5: Dense Data Tables & Filterability
- **Sticky Table Headers**:
  ```css
  .table-container {
    overflow-x: auto;
    max-height: 520px;
  }
  th {
    position: sticky;
    top: 0;
    background: var(--card-bg);
    z-index: 10;
  }
  ```
- **Instant Client-Side Filtering**: Provide category pills and search inputs to allow rapid lookup without reloading the application.

### Pillar 6: Progressive Web App (PWA) & Offline Readiness
- Non-modal, dismissible install banners that respect user dismissal (`localStorage`).
- Instant online/offline status detection to reassure users their local cache is active.

---

## 3. Automated Verification Checklist

When concluding a UI/UX audit, verify:
- [ ] No hardcoded accent colors conflict with the active theme variables.
- [ ] Keyboard navigation: `Tab` traverses all interactive controls with clear focus rings.
- [ ] `Shift + Tab` moves focus backward cleanly.
- [ ] Screen contrast passes WCAG AA across all theme variants.
- [ ] Table horizontal scrolling has smooth scrolling and visible scrollbars.
- [ ] PWA manifest and theme meta tags synchronize with the theme switcher.
- [ ] Charts dynamically re-render or adjust colors upon theme switch.
