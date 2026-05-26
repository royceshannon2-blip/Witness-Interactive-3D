# structure_well_stone_ring — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../structure_well_stone_ring.md § Reference image](../structure_well_stone_ring.md#reference-image)** for the full spec. Summary:

The above-ground portion of a hand-dug rural well — a roughly circular ring of irregular field stones with visible mortar joints, ~1.2 m outer diameter, ~0.7 m tall. ¾ angle showing inside curvature, the worn rope-groove on the inside lip, and lichen patches on the upper north face. No bucket, no plank cover.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Lichen, mortar wash, drip-stains are the surface stories.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py structure_well_stone_ring --kind mesh \
      --image prompts/asset-templates/structure_well_stone_ring/ref.png \
      --era shared
