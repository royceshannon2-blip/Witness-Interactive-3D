# figure_investigator_hands — reference image dropoff

Drop a single `ref.png` (or `ref.jpg`) into this directory.

## What the image must depict

See **[../figure_investigator_hands.md § Reference image](../figure_investigator_hands.md#reference-image)** for the full spec. Summary:

A pair of bare hands + forearms framed as a first-person view (camera at ~1.65 m eye-height, looking down at the hands resting in front of the chest). Young-adult skin, warm mid-brown, clean — no scars, no jewellery, no watch. Long-sleeved mid-grey cotton shirt rolled to mid-forearm. Fingers slightly curled in a neutral resting pose.

## Style + dropoff specs

Apply **[../_STYLE_GUIDE.md](../_STYLE_GUIDE.md)**. Image ≥ 1024², overcast ~5000 K. Photograph or 3D render acceptable; a render gives more pose control.

## Run the pipeline

    cd /home/royce3/Desktop/Witness-Interactive-3D
    python tools/asset_pipeline.py figure_investigator_hands --kind animated \
      --image prompts/asset-templates/figure_investigator_hands/ref.png \
      --rig <path-to-rig>.blend \
      --era present
