# structure_rugo_tin_roof — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../structure_rugo_tin_roof.md § Reference image](../structure_rugo_tin_roof.md#reference-image)** for the full spec. Summary:

A single corrugated steel roof panel (~6 m × 5 m), photographed from above at a slight angle. ~75 mm corrugation pitch, mild rust streaks in the troughs, rolled long edges, ~20 cm overhang on all sides. No mounting hardware, no surrounding structure.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K, neutral background, no watermarks. Favour matte mineral oxidation over crisp galvanised sheen.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py structure_rugo_tin_roof --kind mesh \
      --image prompts/asset-templates/structure_rugo_tin_roof/ref.png \
      --era shared
