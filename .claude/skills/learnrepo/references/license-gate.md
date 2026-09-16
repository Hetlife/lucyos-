# License and intellectual-property gate

This is an engineering process for avoiding obvious legal problems. It is not
legal advice, and nothing here should be written up as a legal conclusion.

## Establish the license for the exact revision

GitHub's sidebar label is a guess produced by a classifier. It is frequently
wrong for dual-licensed projects, re-licensed projects, and repositories with
per-directory licenses.

Read the actual files at the commit you are evaluating: `LICENSE`,
`COPYING`, `NOTICE`, license headers in the files you would actually use,
the `license` field in package metadata, and any `LICENSES/` directory. Record
where you read it in `license.source_of_truth`.

Watch for:

- **Re-licensing.** A project that was MIT at v2 may be BSL at v4. The license
  that applies is the one at your revision.
- **Mixed licensing.** Vendored subdirectories, bundled fonts, example data,
  model weights and generated assets frequently carry different terms than the
  main codebase.
- **Unlicensed code.** No license file means no grant of rights. "It's on
  GitHub" is not permission.
- **Dependency licenses.** A permissive wrapper around a strong-copyleft
  dependency carries the dependency's obligations into your deployment.

## Determine what you are actually allowed to do

Answer these specifically, for the use LucyOS intends:

| Question | Why it matters for LucyOS |
|---|---|
| Use internally? | Almost always yes; the easy case. |
| Modify? | Needed for any adapter or patch. |
| Redistribute? | Matters if LucyOS is ever shipped, packaged or handed to a client. |
| Network/SaaS use? | AGPL-family terms can trigger on serving users over a network. |
| Commercial use? | Some source-available licenses forbid it outright. |
| Static or dynamic linking? | Changes obligations under LGPL-family terms. |
| Sublicense? | Matters for client deliverables. |

Then record the **obligations**: attribution, license text retention, NOTICE
file, state-changes disclosure, source disclosure, patent grant conditions,
trademark limits, field-of-use restrictions.

## Decision rules

**No license, or a license you cannot determine** → do not copy, vendor,
redistribute, or write an implementation derived from reading the code. You
may still study documented behaviour, public APIs and general ideas, and then
write an independent LucyOS-native implementation. Record that you did this
deliberately and why.

**Permissive** (MIT, BSD, Apache-2.0, ISC) → generally compatible. Preserve
copyright and license notices; Apache-2.0 adds NOTICE handling and a patent
grant worth reading. This is the easy path and should be preferred.

**Weak copyleft** (LGPL, MPL-2.0, EPL) → usually workable when the component
stays a separate, unmodified, dynamically linked dependency. Modifications to
the component itself carry disclosure obligations. Keep it behind an adapter
so the boundary is obvious.

**Strong copyleft** (GPL-2.0/3.0, AGPL-3.0) → can impose obligations on
LucyOS itself, and AGPL can trigger on network use. Do not integrate without
explaining the consequence to the owner and getting an explicit decision.

**Source-available and non-commercial** (BSL, SSPL, Commons Clause,
"fair-code", CC-NC, custom "you may not compete" terms) → these are not open
source. Read the actual grant. Many forbid exactly what a business would want
to do. Requires explicit owner approval, and often specialist review.

**Anything unusual, custom, or modified** → treat as unclear until read
carefully. Flag `requires_legal_review: true`.

## Copying versus learning

There is a real and useful distinction:

- **Protectable expression** — the actual source text, its structure,
  distinctive naming, comments, and close paraphrase. Copying this carries the
  license obligations with it.
- **Ideas, algorithms, protocols, public API shapes, and documented
  behaviour** — you may learn these and implement them independently.

When the license blocks copying but the capability is valuable, the right
outcome is usually: read the documentation and observable behaviour, write a
clean LucyOS-native implementation, and record in the manifest that no code
was copied and why that decision was made.

## Record it

Every proposed integration needs both:

1. A **machine-readable record** in the manifest's `license` object — SPDX id,
   source of truth, obligations list, the permission answers above,
   compatibility verdict, and whether legal review is advised.
2. A **plain-language summary** in the report: what LucyOS must do to comply,
   in sentences the owner can act on. "Keep the LICENSE file and credit the
   author in the docs" is useful. "Apache-2.0" alone is not.

The gate blocks on an unidentified license, on
`compatible_with_lucyos != true`, on a missing source of truth, and on
`requires_legal_review: true` — because self-certifying a legal question is
exactly the kind of decision that belongs to the owner.
