# prop_ledger_book — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../prop_ledger_book.md § Reference image](../prop_ledger_book.md#reference-image)** for the full spec. Summary:

A worn leather-bound A5 notebook (~21 × 15 × 3 cm), **closed**, lying flat on a neutral matte surface. Dark brown leather, hand-stitched spine, **no embossing, no title, no writing visible**. Page block fanned at the right edge with thin ledger ruling; a frayed dark fabric ribbon bookmark trails ~8 cm off the right edge.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. **HERO ASSET** — surface detail matters at close camera distance. Pocket-rub patina on corners, edge-cracking acceptable.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py prop_ledger_book --kind mesh \
      --image prompts/asset-templates/prop_ledger_book/ref.png \
      --era shared
