# vegetation_elephant_grass — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../vegetation_elephant_grass.md § Reference image](../vegetation_elephant_grass.md#reference-image)** for the full spec. Summary:

A single isolated clump of tall tropical grass (*Pennisetum purpureum*) at ground level, ~0.5–0.8 m tall. Long arching blades fanning outward from a tight root base; outer blades drooping. Low-angle photograph, neutral background. No flowers, no seed heads, no other vegetation.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Filmic desaturated olive / blue-green palette.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py vegetation_elephant_grass --kind mesh \
      --image prompts/asset-templates/vegetation_elephant_grass/ref.png \
      --era shared
