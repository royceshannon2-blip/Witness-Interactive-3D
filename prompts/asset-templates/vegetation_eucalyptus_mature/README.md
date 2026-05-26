# vegetation_eucalyptus_mature — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../vegetation_eucalyptus_mature.md § Reference image](../vegetation_eucalyptus_mature.md#reference-image)** for the full spec. Summary:

A single mature eucalyptus tree (*E. globulus* or *E. camaldulensis*), ~8–10 m tall, standing alone against open sky. Full tree base-to-crown. Characteristic shedding bark — long curling strips peeling away in patches. Sparse irregular crown of drooping long lanceolate leaves.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Filmic desaturated greens; the buff-against-grey peeling bark contrast is the species signature.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py vegetation_eucalyptus_mature --kind mesh \
      --image prompts/asset-templates/vegetation_eucalyptus_mature/ref.png \
      --era shared
