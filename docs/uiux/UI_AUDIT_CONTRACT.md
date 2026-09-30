# LucyOS UI Audit Contract

This contract defines deterministic-first review for a UI change. A model may critique or propose fixes, but it may not declare PASS without the required evidence.

## Gate order

1. **Scope integrity** — identify changed surfaces/files; reject unrelated redesign.
2. **Platform conventions** — apply relevant Apple HIG guidance for Apple-targeted experiences; preserve web conventions elsewhere.
3. **Information hierarchy** — primary action, status, errors, destructive actions, and navigation are unambiguous.
4. **Accessibility** — target WCAG 2.2 AA for web; keyboard reachability; visible focus; names/labels; non-color cues; zoom/text resizing; target size; reduced motion.
5. **Interaction states** — default/hover/focus/active/disabled/loading/empty/error states are represented where applicable.
6. **Responsive behavior** — verify narrow phone, large phone/tablet, and desktop widths; no clipped critical actions or unreadable text.
7. **Motion** — purposeful only; no critical information conveyed solely through animation; reduced-motion path exists.
8. **Tokens/system** — reuse token/component primitives; flag one-off values and duplicated components.
9. **Copy** — concise labels, actionable errors, consistent terminology; no model-generated claims unsupported by system state.
10. **Visual regression** — compare deterministic screenshots in a consistent environment; review diffs rather than auto-accepting baselines.
11. **Design-to-code drift** — where Figma exists, compare component identity, tokens, layout constraints, and states; code/runtime remains authoritative for implemented behavior.
12. **Frontend audit** — semantic HTML, event handling, security boundaries, performance regressions, dead CSS/JS, and test coverage.

## Result packet

Every audit returns exactly:

- `STATUS`: PASS / NEEDS_FIX / BLOCKED
- `SURFACES`: reviewed screens/components
- `EVIDENCE`: commands, screenshot IDs/paths, standards references
- `FINDINGS`: severity + deterministic reproduction
- `ACCESSIBILITY`: automated findings + manual/incomplete checks
- `RESPONSIVE`: tested viewport/device matrix
- `VISUAL_DIFF`: expected/unexpected changes
- `DRIFT`: Figma/design-system differences, if applicable
- `FIXES`: smallest safe ordered changes
- `ROLLBACK`: exact rollback
- `OWNER_GATE`: only actions requiring owner authority

Automated accessibility tools are explicitly partial; unresolved/incomplete checks require human or assistive-technology review rather than a fabricated PASS.
