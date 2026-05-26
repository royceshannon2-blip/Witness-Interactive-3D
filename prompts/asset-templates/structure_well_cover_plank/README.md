# structure_well_cover_plank — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../structure_well_cover_plank.md § Reference image](../structure_well_cover_plank.md#reference-image)** for the full spec. Summary:

A square wooden plank cover for a well opening, ~1.3 m × 1.3 m × ~8 cm. Three or four planks butted side-by-side with cross-ledger boards just visible at the edge cross-section, plus a wrought-iron ring countersunk into the top face slightly off-centre. Photographed from slight overhead.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Hand-hewn planks; iron ring is wrought (lightly pitted), not cast.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py structure_well_cover_plank --kind mesh \
      --image prompts/asset-templates/structure_well_cover_plank/ref.png \
      --era shared
