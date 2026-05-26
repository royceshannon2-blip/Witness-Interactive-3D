# structure_family_shrine_slab — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../structure_family_shrine_slab.md § Reference image](../structure_family_shrine_slab.md#reference-image)** for the full spec. Summary:

A low rectangular household altar / shrine of stone-and-mortar construction. ~0.95 m × ~0.55 m × ~0.32 m. Hand-fitted field stones, mortar in joints, flat hand-troweled top with subtle wax/soot mottling from years of household candle use. **The top must be empty in the reference** — no candle, no frame, no ledger.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Filmic warm-grey palette; lichen-shadow on mortar is acceptable.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py structure_family_shrine_slab --kind mesh \
      --image prompts/asset-templates/structure_family_shrine_slab/ref.png \
      --era shared
