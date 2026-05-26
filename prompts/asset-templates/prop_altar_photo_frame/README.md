# prop_altar_photo_frame — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../prop_altar_photo_frame.md § Reference image](../prop_altar_photo_frame.md#reference-image)** for the full spec. Summary:

A simple rectangular wooden picture frame (~42 × 32 cm) standing upright on its back-stand. The photograph inside must be **deliberately neutral** — a soft pale grey-buff rectangle, **no recognisable likeness, no real person**. No glass plane. Slight angle so the back-stand kick-out reads.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Worn mid-brown wood, age-yellowed paper.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py prop_altar_photo_frame --kind mesh \
      --image prompts/asset-templates/prop_altar_photo_frame/ref.png \
      --era shared
