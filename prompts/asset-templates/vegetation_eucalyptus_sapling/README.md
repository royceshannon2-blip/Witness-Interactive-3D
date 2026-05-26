# vegetation_eucalyptus_sapling — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../vegetation_eucalyptus_sapling.md § Reference image](../vegetation_eucalyptus_sapling.md#reference-image)** for the full spec. Summary:

A young eucalyptus tree (same species family as the mature reference), ~4–5 m tall, standing alone against an open neutral background. Smoother lighter bark — shedding has just started. Denser, more compact, softer crown than the mature tree.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Slightly brighter green than the mature reference.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py vegetation_eucalyptus_sapling --kind mesh \
      --image prompts/asset-templates/vegetation_eucalyptus_sapling/ref.png \
      --era past
