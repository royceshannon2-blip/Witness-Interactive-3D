// Prototype Archive

Files in this directory are preserved for reference per
[`docs/current-state/PROTOTYPE_AUDIT.md §9`](../../docs/current-state/PROTOTYPE_AUDIT.md).

They are excluded from the TypeScript build (their `.ts.bak` extensions are not
matched by `tsconfig.json` `include: ["src"]`). They are not imported by
`index.html`. Treat them as read-only history.

## Contents

- `main-kigali.ts.bak` — the 1029-line procedural Kigali scene that taught the
  team Babylon 9 lighting, materials, and post-fx. Audit recommends salvaging
  patterns (heightfield sampling, three-light rig, post-fx intensities) into
  the new subsystem modules — never copying the file itself.
- `counter.ts.bak` — Vite template leftover. Preserved only because the audit
  asked for the prototype's full state to be retrievable.

## When to consult these

- Lighting tuning: see the three-light rig at original L37–L52.
- Heightfield + footprint sampling pattern: original L162–L207.
- Post-fx stack defaults: original L906–L925 (intensities are too strong; see
  `docs/design-docs/RENDERING.md` for the corrected values).
- PBR base colors for laterite, mud-brick, tin roof: original L59–L150.

## When to delete this directory

After the new `src/engine/Materials.ts` and `src/engine/Lighting.ts` ship with
their values dialed in against real Bisesero reference photos, this archive
becomes redundant. Plan to delete after the Family Compound vertical slice
lands.
