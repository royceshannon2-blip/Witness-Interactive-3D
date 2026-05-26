# structure_rugo_door — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../structure_rugo_door.md § Reference image](../structure_rugo_door.md#reference-image)** for the full spec. Summary:

A vertical-plank wooden door, single leaf, in a roughly 30°-open pose so both faces read. Three or four hand-planed planks, two horizontal ledger boards on the inside face, simple iron handle on the outside. No frame structure around the door, no surroundings.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K, neutral background. Hand-hewn, unfinished mid-brown wood with axe marks visible.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py structure_rugo_door --kind mesh \
      --image prompts/asset-templates/structure_rugo_door/ref.png \
      --era past
