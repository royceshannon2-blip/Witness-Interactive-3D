# Documentation Standards — Babylon.js Reference

## Primary source of truth

All Babylon.js API and feature questions must be answered from the cloned documentation first:

```
docs/reference/Documentation/content/
```

Do not rely on training-data memory of Babylon APIs. The cloned docs are authoritative; training data is a fallback only when the cloned docs have no coverage of a topic.

## Version scope

Focus on **v6.0 / v7.0** features and APIs. Specifically:

- **WebGPU compatibility** — prefer patterns that work under both WebGL 2 and WebGPU. When a class or method has a WebGPU-incompatible usage, flag it.
- Breaking changes are tracked in `docs/reference/Documentation/content/breaking-changes.md` — check it before implementing anything that touches the render pipeline, materials, or engine lifecycle.
- Do not introduce patterns from v4.x or v5.x unless explicitly confirmed to survive in v6+.

## How to use the docs — Actionable Snippets only

**Do not read entire folders.** Use targeted search:

1. Identify the class or feature needed (e.g. `SceneLoader`, `PBRMaterial`, `DefaultRenderingPipeline`).
2. `Grep` for that class name under `docs/reference/Documentation/content/` before writing any implementation code.
3. Read only the matched files (or the matched section within a file).
4. Distill what you find into a minimal, self-contained code snippet — no surrounding prose, no imports that don't apply to this project.

Example workflow:
```
Grep "SceneLoader" in docs/reference/Documentation/content/ → read matched .md → extract relevant snippet → adapt to project conventions
```

Never copy a snippet verbatim. Always verify the method signature matches `@babylonjs/core` v6/v7 (check `witness-interactive-vite/package.json` for the exact installed version).

## Version Conflicts

When you find a conflict between:
- The cloned docs and the installed package version, **or**
- A doc example and the TypeScript types in `@babylonjs/core`, **or**
- A v6 API and a v7 API with incompatible signatures,

record it immediately in the project MEMORY file:

```
/home/royce3/.claude/projects/-home-royce3-Desktop-Witness-Interactive-3D/memory/MEMORY.md
```

Entry format under a `## Version Conflicts` section:

```markdown
- **YYYY-MM-DD** `ClassName.methodName`: [what the doc says] vs [what the type/runtime says]. Installed: vX.Y.Z. Action needed: [upgrade / use alternate API / workaround].
```

Flag the conflict in your response to the user so it is visible before morning review.

## What not to do

- Do not `Read` an entire subdirectory of docs to answer a question about one class.
- Do not assume a Babylon API works the same in WebGL and WebGPU without checking `breaking-changes.md` or the WebGPU section.
- Do not use `StandardMaterial` — always `PBRMaterial` or `PBRMetallicRoughnessMaterial`. This is a project rule, not a doc rule, but the docs will confirm it.
