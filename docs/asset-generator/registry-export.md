# Asset Registry & Export — Stage 6

> Asset registration, versioning, public export system for runtime loading.
> See [@claude.md](claude.md), [@architecture.md](architecture.md), [@generation-stages.md](generation-stages.md).

---

## Registry System: docs/asset-index.md

**Location:** `docs/asset-index.md`
**Format:** Markdown table (append-only)
**Owner:** `tools/register_asset.py` (automated via `asset_pipeline.py`)
**Manual editing:** NOT RECOMMENDED (breaks tooling)

### Registry Structure

```markdown
# Asset Index

Auto-managed by `tools/asset_pipeline.py`. Do not hand-edit rows
— re-run the pipeline to refresh metadata.

| Asset ID | Kind | Path | Era | Source | Registered | Faces | Gates |
|---|---|---|---|---|---|---|---|
| prop_ledger_book | mesh | processed/glb/prop_ledger_book.glb | shared | stage 1 raw output | 2026-05-25 | 8,000 | ✅ 6/6 |
| vegetation_eucalyptus_mature | mesh | processed/glb/vegetation_eucalyptus_mature.glb | shared | ComfyUI stage 0 | 2026-05-24 | 15,234 | ✅ 6/6 |
| my_splat | splat | processed/splats/my_splat.spz | present | captures/site.spz | 2026-05-23 | n/a | n/a |
| terrain | tileset | processed/tilesets/terrain.tileset.json | shared | https://example.com/3d/tileset.json | 2026-05-23 | n/a | n/a |
```

### Column Definitions

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| Asset ID | string | prop_ledger_book | Unique identifier, snake_case |
| Kind | string | mesh, splat, tileset, navmesh, nme, animated | Asset kind (see [@asset-kinds.md](asset-kinds.md)) |
| Path | string | processed/glb/prop_ledger_book.glb | Relative to repo root (or URL for tilesets) |
| Era | string | shared, present (2026), past (1994) | Temporal scope for era switching |
| Source | string | ComfyUI stage 0, captures/file.spz, URL | Provenance (human-readable) |
| Registered | date | YYYY-MM-DD | Registration date (ISO 8601) |
| Faces | int or "n/a" | 8,000 or n/a | Face count for mesh/animated, "n/a" for others |
| Gates | status | ✅ 6/6 or ❌ 5/6 (geometry) | Validation gate summary |

### Gate Status Format

- **`✅ 6/6`** — all 6 gates passed
- **`❌ 5/6 (geometry)`** — 5 passed, 1 failed (geometry); lists failed gate name
- **`n/a`** — asset kind doesn't run gates (splat, tileset, etc.)

### Querying the Registry

```bash
# View all registered assets
cat docs/asset-index.md

# Count assets by kind
grep "| mesh |" docs/asset-index.md | wc -l

# Filter by era
grep "shared" docs/asset-index.md

# Check for failed gates
grep "❌" docs/asset-index.md
```

---

## Stage 6a: Asset Registration (register_asset.py)

**Purpose:** Append a single asset row to the registry
**Invoked by:** `asset_pipeline.py` after validation gates complete
**Exit codes:** 0 (ok), 3 (failed, registry unwritable)

### Process

```python
def register_asset(asset_id: str, era: str, kind: str, glb_path: str):
    # Read diagnostic sidecars
    geom_report = json.load(open(f"processed/diagnostics/{asset_id}.geometry.json"))
    agg_report = json.load(open(f"processed/diagnostics/{asset_id}.aggregate.json"))
    
    # Extract metadata
    faces = geom_report.get("metrics", {}).get("face_count", "n/a")
    gates_ran = agg_report.get("gates_ran", [])
    gates_failed = agg_report.get("gates_failed", [])
    
    if not gates_ran:
        gates_summary = "n/a"
    elif not gates_failed:
        gates_summary = f"✅ {len(gates_ran)}/{len(gates_ran)}"
    else:
        failed_names = ", ".join(gates_failed)
        gates_summary = f"❌ {len(gates_ran) - len(gates_failed)}/{len(gates_ran)} ({failed_names})"
    
    # Format row
    date_str = datetime.now().strftime("%Y-%m-%d")
    rel_path = Path(glb_path).relative_to(REPO_ROOT)
    era_label = {
        "present": "present (2026)",
        "past": "past (1994)",
        "shared": "shared"
    }[era]
    
    row = (
        f"| {asset_id} | {kind} | {rel_path} | {era_label} | "
        f"stage 1 raw output | {date_str} | {faces} | {gates_summary} |"
    )
    
    # Append to registry (atomic write)
    try:
        with open(ASSET_INDEX, "a") as f:
            f.write(row + "\n")
        return 0
    except IOError:
        print(f"ERROR: cannot write {ASSET_INDEX}")
        return 3
```

### Diagnostics Lookup

**Face count** (`gates` column):
- Source: `processed/diagnostics/<id>.geometry.json` (Gate 2 report)
- Field: `metrics.face_count`
- Fallback: "n/a" if report missing or face count absent

**Gate status** (`gates` column):
- Source: `processed/diagnostics/<id>.aggregate.json` (Gate 4 report)
- Fields: `gates_ran`, `gates_failed`
- Format: `✅ N/N` (all passed) or `❌ N/N (failed_1, failed_2, ...)` (some failed)

### Era Label Resolution

```python
era_labels = {
    "present": "present (2026)",  # investigator era
    "past": "past (1994)",        # witness era
    "shared": "shared",           # both eras
}
```

---

## Stage 6b: Public Export (export_babylon.py)

**Purpose:** Copy optimized GLBs to runtime directory (`witness-interactive-vite/public/assets/`)
**Invoked by:** `asset_pipeline.py` after stage 6a (registration)
**Exit codes:** 0 (ok), 3 (failed, export dir unwritable)

### Export Targets

**For mesh & animated kinds:**
- LOD0: `processed/glb/<id>.glb` → `witness-interactive-vite/public/assets/<id>.glb`
- LOD1: `processed/glb/<id>.lod1.glb` → `witness-interactive-vite/public/assets/<id>.lod1.glb`
- LOD2: `processed/glb/<id>.lod2.glb` → `witness-interactive-vite/public/assets/<id>.lod2.glb`
- Collision: `processed/glb/<id>.collision.glb` → `witness-interactive-vite/public/assets/<id>.collision.glb` (optional)

**For other kinds (splat, tileset, etc.):**
- Asset file: `processed/<kind>/<id>.*` → `witness-interactive-vite/public/assets/<id>.*`

### Process

```python
def export_babylon(asset_id: str, lod0: Path, lod1: Path, lod2: Path, collision: Path):
    dest_dir = REPO_ROOT / "witness-interactive-vite" / "public" / "assets"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_copy = [
        (lod0, f"{asset_id}.glb"),
        (lod1, f"{asset_id}.lod1.glb"),
        (lod2, f"{asset_id}.lod2.glb"),
        (collision, f"{asset_id}.collision.glb"),
    ]
    
    for src, dest_name in files_to_copy:
        if src.exists():
            dest_path = dest_dir / dest_name
            shutil.copy2(src, dest_path)  # Preserve timestamp
            print(f"  Exported: {dest_name}")
        else:
            print(f"  Skipped (not found): {dest_name}")
    
    return 0 if any(src.exists() for src, _ in files_to_copy) else 3
```

### Runtime Path Resolution

**AssetLibrary contract** (from `witness-interactive-vite/src/io/AssetLibrary.ts`):

```typescript
async instantiate(assetId: string): Promise<AssetContainer> {
    const baseUrl = "/assets";
    const paths = {
        lod0: `${baseUrl}/${assetId}.glb`,
        lod1: `${baseUrl}/${assetId}.lod1.glb`,
        lod2: `${baseUrl}/${assetId}.lod2.glb`,
    };
    // AssetLibrary resolves these paths and loads in parallel
}
```

**Runtime expects files at:**
```
witness-interactive-vite/public/assets/
├── prop_ledger_book.glb
├── prop_ledger_book.lod1.glb
├── prop_ledger_book.lod2.glb
├── prop_ledger_book.collision.glb
├── vegetation_eucalyptus_mature.glb
├── vegetation_eucalyptus_mature.lod1.glb
├── vegetation_eucalyptus_mature.lod2.glb
├── structure_rugo_main_house.glb
├── structure_rugo_main_house.lod1.glb
├── structure_rugo_main_house.lod2.glb
└── ... (all generated assets)
```

### Failure Recovery

If export fails (exit 3):
1. Check that `witness-interactive-vite/public/assets/` exists and is writable
2. Verify source GLBs exist in `processed/glb/`
3. Check file permissions: `ls -la witness-interactive-vite/public/assets/`
4. Retry: `python tools/export_babylon.py <asset_id>`

---

## Asset Versioning & Rollback

**No explicit versioning in the registry.** Assets are point-in-time snapshots:
- Date-stamped at registration (Registered column)
- Deterministic generation (seed stored in template YAML)
- Reproducible from template + seed + stage outputs

**To roll back an asset:**
1. Identify last-known-good seed in template YAML
2. Re-run generation with that seed (overrides random seed)
3. Compare output to previous version
4. If acceptable, re-register (updates Registered date)

**To preserve asset versions:**
- Archive stage outputs (processed/glb/raw/, processed/textures/, etc.) separately
- Tag in git if asset is significant
- Record seed + timestamp for reproducibility

---

## Integration with Web App (Babylon.js Runtime)

### AssetLibrary Initialization

See `witness-interactive-vite/src/io/AssetLibrary.ts` for runtime loading contract.

**Expected behavior:**
1. Runtime calls `AssetLibrary.instantiate("prop_ledger_book")`
2. AssetLibrary constructs paths: `/assets/prop_ledger_book.glb`, `/assets/prop_ledger_book.lod1.glb`, etc.
3. Babylon.js fetches from `public/assets/` directory (served by dev server or static hosting)
4. GLBs are Draco-compressed, KTX2-compressed (handled by Babylon decoder)
5. LOD selection is automatic (0–15m: LOD0, 15–50m: LOD1, 50+m: LOD2)

### Asset Not Found Recovery

If `/assets/<id>.glb` returns 404:
- Check: was `export_babylon.py` successful?
- Check: does `witness-interactive-vite/public/assets/<id>.glb` exist?
- Check: is dev server serving static files from `public/`?
- Fallback: runtime may substitute a placeholder box or skip asset

---

## Bulk Operations

### Exporting Phase 1 Assets

```bash
# Re-export all Phase 1 assets (after modifications)
for id in prop_ledger_book vegetation_eucalyptus_mature structure_rugo_main_house ...; do
    python tools/export_babylon.py $id
done
```

### Querying Asset Coverage

```bash
# Count Phase 1 assets currently exported
ls witness-interactive-vite/public/assets/*.glb | wc -l

# Identify missing exports
grep "^|" docs/asset-index.md | awk '{print $2}' | while read id; do
    if [ ! -f "witness-interactive-vite/public/assets/${id}.glb" ]; then
        echo "Missing export: $id"
    fi
done
```

### Registry Cleanup (if needed)

**If a row is incorrect and needs fixing:**
1. Remove the row manually (or re-run asset_pipeline.py to append corrected row)
2. Do NOT hand-edit rows — re-generation is safer and maintains audit trail

---

## Diagnostics & Troubleshooting

### Asset registered but not loading in runtime

**Checklist:**
1. Check registry row exists and gates passed: `grep <id> docs/asset-index.md`
2. Check export files exist: `ls witness-interactive-vite/public/assets/<id>*`
3. Check file sizes are reasonable (> 100 KB): `du -h witness-interactive-vite/public/assets/<id>*`
4. Test with babylonjs-viewer: `npx babylonjs-viewer witness-interactive-vite/public/assets/<id>.glb`
5. Check browser console for 404 or decode errors

### "Asset ID not in registry"

- Asset was generated but `register_asset.py` failed (check stage 6a exit code)
- Registry file corrupted or inaccessible
- Recovery: re-run `asset_pipeline.py` (stage 6a will append row)

### "Public export incomplete" (LODs missing)

- `export_babylon.py` failed early; some LODs not copied
- Check: do LOD1/LOD2 exist in `processed/glb/`? (`generate_lods.py` output)
- Check: did stage 6b exit with success?
- Recovery: `python tools/export_babylon.py <id>` (re-export all files)

---

## Cross-References

- **Registration tool:** [@tools.md](tools.md#register_assetpy--stage-6a-asset-registration)
- **Export tool:** [@tools.md](tools.md#export_babilonpy--stage-6b-public-export)
- **Stage 6 overview:** [@generation-stages.md](generation-stages.md#stage-6a-asset-registration)
- **Runtime integration:** `docs/design-docs/RENDERING.md` (material library + asset loading)
- **Babylon.js API:** `witness-interactive-vite/src/io/AssetLibrary.ts`, `SplatLibrary.ts`, `TilesetMount.ts`

---

**Last updated:** 2026-05-25 | **See also:** [@tools.md](tools.md), [@generation-stages.md](generation-stages.md), [@architecture.md](architecture.md)
