# structure_rugo_main_house — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../structure_rugo_main_house.md § Reference image](../structure_rugo_main_house.md#reference-image)** for the full spec. Summary:

A single-room rural Rwandan mud-brick dwelling, ¾ front angle on overcast morning. Hand-applied plaster, flat top edge (no roof), one window opening, one doorway opening, no door installed. Filmic desaturated palette, neutral background. No people, no roof, no other structures.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)** — Digital Diorama (tactile weathered realism, hyper-realistic PBR, filmic desaturated). Image ≥ 1024², overcast lighting ~5000 K, neutral background, no watermarks.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py structure_rugo_main_house --kind mesh \
      --image prompts/asset-templates/structure_rugo_main_house/ref.png \
      --era shared
