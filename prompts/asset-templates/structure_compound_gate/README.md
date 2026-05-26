# structure_compound_gate — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../structure_compound_gate.md § Reference image](../structure_compound_gate.md#reference-image)** for the full spec. Summary:

A two-post-and-beam wooden entrance gate at a rural East African compound. Two square-section hand-hewn posts spanned by a horizontal top beam and a single mid-height cross-rail lashed to each post with natural-fibre rope. **No gate-leaf**, no surrounding fence, no signage.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Axe-mark surfaces on the posts are the primary surface story.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py structure_compound_gate --kind mesh \
      --image prompts/asset-templates/structure_compound_gate/ref.png \
      --era shared
