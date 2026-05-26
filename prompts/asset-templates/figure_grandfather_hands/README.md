# figure_grandfather_hands — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../figure_grandfather_hands.md § Reference image](../figure_grandfather_hands.md#reference-image)** for the full spec. Summary:

Same staging as the investigator hands reference (first-person view, same resting pose). The hands belong to an older Rwandan man — weathered warm deep-brown skin, broadened knuckles, a thin pale ~3 cm scar on the back of the right hand. Faded khaki/olive cotton sleeve rolled to mid-forearm with slight fraying and a small uneven repair patch on one inner forearm. **No jewellery, no militaria, no weapons**.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Photograph or 3D render. Subsurface scatter, fine micro-folds.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py figure_grandfather_hands --kind animated \
      --image prompts/asset-templates/figure_grandfather_hands/ref.png \
      --rig <path-to-rig>.blend \
      --era past
