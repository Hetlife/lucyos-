# LearnRepo UI/UX Stack Shortlist — 2026-09-22

Scope: research/staging only. LucyOS current UI is a small vanilla HTML/CSS/JS surface (`web/`, about 584 lines) with no Node package-manager stack. This materially favors Lucy-native contracts and reuse over adding a framework/toolchain.

## Decision matrix

| Capability | Primary | Classification | Why now | Fallback / deferred |
|---|---|---|---|---|
| Apple platform conventions | Apple Human Interface Guidelines | KEEP as authoritative reference | First-party platform guidance; no runtime dependency | none |
| Design briefs / UX critique / polish | LucyOS Design Packet + UI Audit contracts | KEEP / BUILD NATIVE | Cross-model, deterministic evidence format; no second state system | model-specific prompts only as adapters |
| Accessibility standard | WCAG 2.2 | KEEP as normative reference | W3C Recommendation; technology-neutral acceptance criteria | Apple Accessibility guidance for Apple-specific behavior |
| Automated accessibility | axe-core | ADAPT, not install yet | Mature WCAG-oriented engine; automated coverage is explicitly partial | Storybook a11y only if a component-story toolchain later exists |
| Design tokens/system | Style Dictionary | ADAPT later | Cross-platform token build model; Apache-2.0 | Lucy-native JSON/CSS token generation while UI remains tiny |
| Screenshot / visual regression | existing `web.browser-kernel` / Playwright | KEEP / REUSE | Already cataloged; deterministic screenshots and comparisons; no duplicate skill | Chromatic deferred |
| Responsive testing | Playwright device/viewport emulation | KEEP / REUSE | Existing browser candidate covers mobile/tablet/desktop emulation | manual browser matrix |
| Figma handoff | Official Figma MCP + Code Connect | ADAPT as connector | Design context/writeback and component mapping without making Figma canonical runtime state | exported Design Packet when connector unavailable |
| Design-to-code drift | Figma Code Connect evidence + Lucy audit | ADAPT | Compare mappings/tokens/components; runtime remains authoritative | deterministic screenshot + token/component diff |
| Motion | Lucy-native HIG/WCAG rules | KEEP / BUILD NATIVE | Current UI does not justify a motion library | evaluate Motion/other library only if product stack needs it |
| UI copy | Lucy-native audit rubric | KEEP / BUILD NATIVE | No external dependency needed; labels/errors must reflect actual state | model critique as non-authoritative suggestion |
| Frontend coding audit | existing repo tests + browser kernel + boundary/security gates | KEEP / REUSE | Fits current stdlib/static architecture | ESLint/Lighthouse only after measurable need |
| Component workbench | Storybook | DEFER | Strong tool, but current LucyOS has no component framework or Node toolchain; disproportionate now | revisit after componentization |
| Cloud visual review | Chromatic | DEFER | Useful with Storybook, but creates cloud/project dependency and is unnecessary before local deterministic screenshots are insufficient | Playwright local baselines |

## Source evidence

- Apple HIG: https://developer.apple.com/design/human-interface-guidelines
- Apple accessibility: https://developer.apple.com/design/human-interface-guidelines/accessibility
- Apple motion: https://developer.apple.com/design/human-interface-guidelines/motion
- W3C WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Playwright visual comparisons: https://playwright.dev/docs/test-snapshots
- Playwright emulation: https://playwright.dev/docs/emulation
- Playwright repository/license: https://github.com/microsoft/playwright — Apache-2.0 verified in repository LICENSE during this research pass.
- Figma MCP: https://developers.figma.com/docs/figma-mcp-server/
- Figma MCP tools/Code Connect: https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/
- Style Dictionary: https://github.com/style-dictionary/style-dictionary — Apache-2.0 verified in repository LICENSE during this research pass.
- axe-core: https://github.com/dequelabs/axe-core — MPL-2.0 stated by the project; automated checks do not replace manual accessibility review.
- Storybook accessibility: https://storybook.js.org/docs/writing-tests/accessibility-testing
- Storybook visual testing: https://storybook.js.org/docs/writing-tests/visual-testing

## Gate state

No new external dependency is approved for installation by this research pass.

- Apple HIG / WCAG: reference material only; no software install.
- Playwright: existing LucyOS catalog candidate; reuse rather than duplicate.
- Figma: connector/handoff candidate; credentials/account permissions remain external and owner-controlled.
- Style Dictionary and axe-core: research/license evidence exists, but SECURITY, SANDBOX, BENCHMARK, and ARCHITECTURE evidence must be recorded before install or activation.
- Storybook/Chromatic: deferred for current architecture; do not install merely to satisfy this task.

## Next staged experiments

1. Produce one Design Packet for the existing phone interface with no code change.
2. Use the existing browser-kernel candidate to define a deterministic responsive screenshot matrix; do not add a second browser framework.
3. Run a no-install architecture proposal for optional axe-core accessibility checks and a separate one for Style Dictionary; only advance if the benefit exceeds the dependency/toolchain cost.
4. Use the connected Figma workflow only when a concrete design file is selected; store node/component mappings in the Design Packet, not as canonical LucyOS state.
5. Benchmark manual/static-token workflow versus Style Dictionary on the current small UI before any dependency proposal advances.
