# prop_altar_candle — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../prop_altar_candle.md § Reference image](../prop_altar_candle.md#reference-image)** for the full spec. Summary:

A short cylindrical white wax candle stub (~5 cm × ~12 cm), standalone on a neutral matte surface. Hardened drip-trails on one side, off-centre wick crater on top, dark twisted cotton wick (~2 cm) — **unlit**. Hardened wax-pool collar at the base. Slight angle.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Wax reads cream, not bright white.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py prop_altar_candle --kind mesh \
      --image prompts/asset-templates/prop_altar_candle/ref.png \
      --era past
