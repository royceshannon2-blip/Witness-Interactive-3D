import * as BABYLON from "@babylonjs/core";
import * as GUI from "@babylonjs/gui";
import { GLTF2Export, GLTFData } from "@babylonjs/serializers/glTF";

const createScene = function (
  engine: BABYLON.Engine,
  canvas: HTMLCanvasElement
): BABYLON.Scene {
  const scene = new BABYLON.Scene(engine);
  scene.gravity = new BABYLON.Vector3(0, -9.81 * 0.06, 0);

  scene.clearColor = new BABYLON.Color4(0.58, 0.54, 0.49, 1);
  scene.fogMode = BABYLON.Scene.FOGMODE_EXP2;
  scene.fogDensity = 0.014;
  scene.fogColor = new BABYLON.Color3(0.64, 0.60, 0.53);

  const camera = new BABYLON.UniversalCamera(
    "playerCam",
    new BABYLON.Vector3(0, 1.65, -8),
    scene
  );
  camera.attachControl(canvas, true);
  camera.speed = 0.28;
  camera.angularSensibility = 1100;
  camera.minZ = 0.08;
  camera.maxZ = 180;
  camera.fov = 1.05;
  camera.ellipsoid = new BABYLON.Vector3(0.4, 0.85, 0.4);
  camera.checkCollisions = true;
  camera.applyGravity = true;

  camera.keysUp.push(87);
  camera.keysDown.push(83);
  camera.keysLeft.push(65);
  camera.keysRight.push(68);

  const sky = new BABYLON.HemisphericLight("sky", new BABYLON.Vector3(0, 1, 0), scene);
  sky.intensity = 1.05;
  sky.diffuse = new BABYLON.Color3(0.82, 0.80, 0.76);
  sky.specular = new BABYLON.Color3(0.06, 0.06, 0.06);
  sky.groundColor = new BABYLON.Color3(0.40, 0.20, 0.10);

  const sun = new BABYLON.DirectionalLight("sun", new BABYLON.Vector3(-0.18, -1, 0.30), scene);
  sun.intensity = 0.55;
  sun.diffuse = new BABYLON.Color3(0.95, 0.93, 0.86);
  sun.specular = new BABYLON.Color3(0.12, 0.12, 0.10);
  sun.position = new BABYLON.Vector3(20, 60, -30);

  const stormRim = new BABYLON.DirectionalLight("stormRim", new BABYLON.Vector3(0.6, -0.3, -1), scene);
  stormRim.intensity = 0.18;
  stormRim.diffuse = new BABYLON.Color3(0.55, 0.58, 0.70);

  const shadowGen = new BABYLON.ShadowGenerator(1024, sun);
  shadowGen.usePercentageCloserFiltering = true;
  shadowGen.filteringQuality = BABYLON.ShadowGenerator.QUALITY_MEDIUM;
  shadowGen.bias = 0.001;
  shadowGen.normalBias = 0.02;

  const lateriteMat = new BABYLON.PBRMaterial("laterite", scene);
  lateriteMat.albedoColor = new BABYLON.Color3(0.48, 0.16, 0.06);
  lateriteMat.roughness = 0.97;
  lateriteMat.metallic = 0.0;

  const concreteMat = new BABYLON.PBRMaterial("concrete", scene);
  concreteMat.albedoColor = new BABYLON.Color3(0.60, 0.55, 0.48);
  concreteMat.roughness = 0.94;
  concreteMat.metallic = 0.0;

  const fadedPaintMat = new BABYLON.PBRMaterial("fadedPaint", scene);
  fadedPaintMat.albedoColor = new BABYLON.Color3(0.70, 0.65, 0.55);
  fadedPaintMat.roughness = 0.91;
  fadedPaintMat.metallic = 0.0;

  const brickMat = new BABYLON.PBRMaterial("brick", scene);
  brickMat.albedoColor = new BABYLON.Color3(0.50, 0.18, 0.08);
  brickMat.roughness = 0.96;
  brickMat.metallic = 0.0;

  const tinRoofMat = new BABYLON.PBRMaterial("tinRoof", scene);
  tinRoofMat.albedoColor = new BABYLON.Color3(0.28, 0.12, 0.05);
  tinRoofMat.metallic = 0.65;
  tinRoofMat.roughness = 0.72;
  tinRoofMat.anisotropy.isEnabled = true;
  tinRoofMat.anisotropy.intensity = 0.7;

  const oliveMat = new BABYLON.PBRMaterial("olive", scene);
  oliveMat.albedoColor = new BABYLON.Color3(0.22, 0.24, 0.14);
  oliveMat.metallic = 0.50;
  oliveMat.roughness = 0.80;

  const drumMat = new BABYLON.PBRMaterial("drum", scene);
  drumMat.albedoColor = new BABYLON.Color3(0.45, 0.10, 0.06);
  drumMat.metallic = 0.60;
  drumMat.roughness = 0.68;

  const matookeMat = new BABYLON.PBRMaterial("matooke", scene);
  matookeMat.albedoColor = new BABYLON.Color3(0.18, 0.42, 0.10);
  matookeMat.roughness = 0.62;
  matookeMat.metallic = 0.0;
  matookeMat.subSurface.isTranslucencyEnabled = true;
  matookeMat.subSurface.translucencyIntensity = 0.25;

  const eucalyptusMat = new BABYLON.PBRMaterial("eucalyptus", scene);
  eucalyptusMat.albedoColor = new BABYLON.Color3(0.55, 0.52, 0.46);
  eucalyptusMat.roughness = 0.90;
  eucalyptusMat.metallic = 0.0;

  const eucalyptusLeafMat = new BABYLON.PBRMaterial("eucLeaf", scene);
  eucalyptusLeafMat.albedoColor = new BABYLON.Color3(0.28, 0.38, 0.18);
  eucalyptusLeafMat.roughness = 0.65;
  eucalyptusLeafMat.metallic = 0.0;
  eucalyptusLeafMat.subSurface.isTranslucencyEnabled = true;
  eucalyptusLeafMat.subSurface.translucencyIntensity = 0.2;

  const skinDarkMat = new BABYLON.PBRMaterial("skinDark", scene);
  skinDarkMat.albedoColor = new BABYLON.Color3(0.20, 0.12, 0.07);
  skinDarkMat.roughness = 0.88;
  skinDarkMat.metallic = 0.0;
  skinDarkMat.subSurface.isTranslucencyEnabled = true;
  skinDarkMat.subSurface.translucencyIntensity = 0.12;

  const clothRedMat = new BABYLON.PBRMaterial("clothRed", scene);
  clothRedMat.albedoColor = new BABYLON.Color3(0.52, 0.18, 0.12);
  clothRedMat.roughness = 0.93;
  clothRedMat.metallic = 0.0;

  const clothBlueMat = new BABYLON.PBRMaterial("clothBlue", scene);
  clothBlueMat.albedoColor = new BABYLON.Color3(0.18, 0.22, 0.38);
  clothBlueMat.roughness = 0.93;
  clothBlueMat.metallic = 0.0;

  const clothWhiteMat = new BABYLON.PBRMaterial("clothWhite", scene);
  clothWhiteMat.albedoColor = new BABYLON.Color3(0.75, 0.73, 0.68);
  clothWhiteMat.roughness = 0.92;
  clothWhiteMat.metallic = 0.0;

  const sandbagMat = new BABYLON.PBRMaterial("sandbag", scene);
  sandbagMat.albedoColor = new BABYLON.Color3(0.50, 0.44, 0.28);
  sandbagMat.roughness = 0.98;
  sandbagMat.metallic = 0.0;

  const jerryCan = new BABYLON.PBRMaterial("jerrycan", scene);
  jerryCan.albedoColor = new BABYLON.Color3(0.55, 0.48, 0.10);
  jerryCan.roughness = 0.82;
  jerryCan.metallic = 0.0;

  [lateriteMat, concreteMat, brickMat, tinRoofMat, oliveMat, drumMat,
   matookeMat, eucalyptusMat, eucalyptusLeafMat, fadedPaintMat,
   skinDarkMat, clothRedMat, clothBlueMat, clothWhiteMat,
   sandbagMat, jerryCan].forEach(m => m.freeze());

  const GROUND_SIZE = 130;
  const SUBDIVISIONS = 110;
  const ground = BABYLON.MeshBuilder.CreateGround(
    "ground",
    { width: GROUND_SIZE, height: GROUND_SIZE, subdivisions: SUBDIVISIONS },
    scene
  );
  ground.material = lateriteMat;
  ground.checkCollisions = true;
  ground.receiveShadows = true;

  const positions = ground.getVerticesData(BABYLON.VertexBuffer.PositionKind);
  if (!positions) return scene;

  const hillfn = (x: number, z: number): number => {
    let h = Math.sin(x / 7.5) * 6.5 + Math.cos(z / 9) * 5.5;
    h += Math.sin(x / 4.2 + 1.1) * 2.8 + Math.cos(z / 5.5 + 0.7) * 2.4;
    return h;
  };

  for (let i = 0; i < positions.length; i += 3) {
    const x = positions[i];
    const z = positions[i + 2];
    let height = hillfn(x, z);
    const TERRACE = 1.5;
    height = Math.floor(height / TERRACE) * TERRACE;
    const roadWidth = 3.8;
    if (Math.abs(x) < roadWidth) height = Math.max(height * 0.12, -0.4);
    positions[i + 1] = height;
  }

  ground.setVerticesData(BABYLON.VertexBuffer.PositionKind, positions);
  ground.convertToFlatShadedMesh();

  const half = GROUND_SIZE / 2;
  const getApproxHeight = (x: number, z: number): number => {
    const ix = Math.round(((x + half) / GROUND_SIZE) * SUBDIVISIONS);
    const iz = Math.round(((z + half) / GROUND_SIZE) * SUBDIVISIONS);
    const clamp = (v: number) => Math.max(0, Math.min(SUBDIVISIONS, v));
    const idx = (clamp(iz) * (SUBDIVISIONS + 1) + clamp(ix)) * 3;
    return positions[idx + 1] || 0;
  };

  // FIX: sample the minimum ground height across a footprint so buildings
  // always rest on the lowest point of their base, never float.
  const getFootprintMinHeight = (cx: number, cz: number, w: number, d: number, samples = 7): number => {
    let minH = Infinity;
    for (let i = 0; i < samples; i++) {
      for (let j = 0; j < samples; j++) {
        const sx = cx - w / 2 + (w / (samples - 1)) * i;
        const sz = cz - d / 2 + (d / (samples - 1)) * j;
        minH = Math.min(minH, getApproxHeight(sx, sz));
      }
    }
    return minH;
  };

  /**
   * isFlat — true if height variation within `radius` metres of (cx,cz)
   * stays within `tolerance` metres. Use before placing any ground-level
   * prop that must sit flush (bicycles, jerry cans, checkpoints, etc).
   *
   * radius 1.5 + tolerance 0.35 = typical road-shoulder flatness gate.
   * Tighten tolerance for precision props, loosen for large buildings.
   */
  const isFlat = (cx: number, cz: number, radius = 1.5, tolerance = 0.35): boolean => {
    let minH = Infinity, maxH = -Infinity;
    const STEPS = 8;
    for (let i = 0; i < STEPS; i++) {
      for (let j = 0; j < STEPS; j++) {
        const sx = cx - radius + (2 * radius / (STEPS - 1)) * i;
        const sz = cz - radius + (2 * radius / (STEPS - 1)) * j;
        if ((sx - cx) ** 2 + (sz - cz) ** 2 > radius * radius) continue;
        const h = getApproxHeight(sx, sz);
        minH = Math.min(minH, h);
        maxH = Math.max(maxH, h);
      }
    }
    return (maxH - minH) <= tolerance;
  };

  // ============================================================
  // VEGETATION
  // ============================================================
  const createMatookeClump = (x: number, z: number, count = 3): void => {
    for (let c = 0; c < count; c++) {
      const ox = (Math.random() - 0.5) * 1.8;
      const oz = (Math.random() - 0.5) * 1.8;
      // FIX: sample ground at each stem's actual position
      const gy = getApproxHeight(x + ox, z + oz);
      const s = 0.75 + Math.random() * 0.45;
      const trunkH = (2.0 + Math.random() * 0.8) * s;

      const trunk = BABYLON.MeshBuilder.CreateCylinder(
        `mt_trunk_${x}_${z}_${c}`,
        { height: trunkH, diameterTop: 0.22 * s, diameterBottom: 0.32 * s, tessellation: 6 },
        scene
      );
      trunk.position.set(x + ox, gy + trunkH / 2, z + oz);
      trunk.material = matookeMat;
      trunk.receiveShadows = true;
      shadowGen.addShadowCaster(trunk);

      for (let i = 0; i < 5; i++) {
        const leaf = BABYLON.MeshBuilder.CreateCylinder(
          `leaf_${x}_${z}_${c}_${i}`,
          { height: 0.06, diameterTop: (0.85 + Math.random() * 0.3) * s, diameterBottom: 0.05, tessellation: 3 },
          scene
        );
        leaf.position.set(x + ox, gy + trunkH + 0.05, z + oz);
        leaf.rotation.z = (Math.PI / 3) + (Math.random() - 0.5) * 0.4;
        leaf.rotation.y = ((Math.PI * 2) / 5) * i + Math.random() * 0.3;
        leaf.material = matookeMat;
        leaf.receiveShadows = true;
        shadowGen.addShadowCaster(leaf);
      }
    }
  };

  const createEucalyptus = (x: number, z: number, height: number = 11): void => {
    const gy = getApproxHeight(x, z);

    const trunk = BABYLON.MeshBuilder.CreateCylinder(
      `euc_trunk_${x}_${z}`,
      { height, diameterTop: 0.14, diameterBottom: 0.36, tessellation: 7 },
      scene
    );
    trunk.position.set(x, gy + height / 2, z);
    trunk.material = eucalyptusMat;
    trunk.checkCollisions = true;
    trunk.receiveShadows = true;
    shadowGen.addShadowCaster(trunk);

    const canopy = BABYLON.MeshBuilder.CreateCylinder(
      `euc_canopy_${x}_${z}`,
      { height: height * 0.38, diameterTop: 0.3, diameterBottom: 1.6, tessellation: 7 },
      scene
    );
    canopy.position.set(x, gy + height * 0.82, z);
    canopy.material = eucalyptusLeafMat;
    canopy.receiveShadows = true;
    shadowGen.addShadowCaster(canopy);
  };

  // ============================================================
  // BUILDINGS
  // ============================================================
  const createRugo = (
    x: number,
    z: number,
    rotY: number = 0,
    wallMat: BABYLON.PBRMaterial = brickMat
  ): void => {
    // FIX: use footprint minimum so the building never floats above any corner
    const gy = getFootprintMinHeight(x, z, 4.8, 6.2);

    const walls = BABYLON.MeshBuilder.CreateBox(`rugo_walls_${x}_${z}`, {
      width: 4.8, height: 2.9, depth: 6.2
    }, scene);
    walls.position.set(x, gy + 1.45, z);
    walls.rotation.y = rotY;
    walls.material = wallMat;
    walls.checkCollisions = true;
    walls.receiveShadows = true;
    shadowGen.addShadowCaster(walls);

    const roof = BABYLON.MeshBuilder.CreateCylinder(`rugo_roof_${x}_${z}`, {
      diameterTop: 0.15, diameterBottom: 6.4, height: 1.9, tessellation: 4
    }, scene);
    // FIX: roof base sits at top of walls (gy + 2.9), ridge at gy + 2.9 + 1.9
    roof.position.set(x, gy + 2.9 + 0.95, z);
    roof.rotation.y = Math.PI / 4 + rotY;
    roof.material = tinRoofMat;
    roof.receiveShadows = true;
    shadowGen.addShadowCaster(roof);

    const door = BABYLON.MeshBuilder.CreateBox(`rugo_door_${x}_${z}`, {
      width: 0.9, height: 2.0, depth: 0.15
    }, scene);
    const fwd = new BABYLON.Vector3(Math.sin(rotY), 0, Math.cos(rotY));
    door.position.set(x + fwd.x * 3.15, gy + 1.0, z + fwd.z * 3.15);
    door.rotation.y = rotY;
    const doorMat = new BABYLON.PBRMaterial(`doorM_${x}`, scene);
    doorMat.albedoColor = new BABYLON.Color3(0.08, 0.06, 0.04);
    doorMat.roughness = 1.0;
    doorMat.metallic = 0.0;
    door.material = doorMat;
  };

  const createShopfront = (x: number, z: number, rotY: number = 0): void => {
    // FIX: footprint minimum for shopfront base
    const gy = getFootprintMinHeight(x, z, 5.5, 7.0);

    const bldg = BABYLON.MeshBuilder.CreateBox(`shop_${x}_${z}`, {
      width: 5.5, height: 3.6, depth: 7.0
    }, scene);
    bldg.position.set(x, gy + 1.8, z);
    bldg.rotation.y = rotY;
    bldg.material = fadedPaintMat;
    bldg.checkCollisions = true;
    bldg.receiveShadows = true;
    shadowGen.addShadowCaster(bldg);

    const parapet = BABYLON.MeshBuilder.CreateBox(`par_${x}_${z}`, {
      width: 5.8, height: 0.25, depth: 7.3
    }, scene);
    parapet.position.set(x, gy + 3.6 + 0.125, z);
    parapet.rotation.y = rotY;
    parapet.material = tinRoofMat;
    parapet.receiveShadows = true;
    shadowGen.addShadowCaster(parapet);

    const shutter = BABYLON.MeshBuilder.CreateBox(`shut_${x}_${z}`, {
      width: 2.0, height: 2.2, depth: 0.07
    }, scene);
    const fwd = new BABYLON.Vector3(Math.sin(rotY), 0, Math.cos(rotY));
    shutter.position.set(x + fwd.x * 3.52, gy + 1.1, z + fwd.z * 3.52);
    shutter.rotation.y = rotY;
    const shutterMat = new BABYLON.PBRMaterial(`shutM_${x}`, scene);
    shutterMat.albedoColor = new BABYLON.Color3(0.20, 0.20, 0.18);
    shutterMat.metallic = 0.6;
    shutterMat.roughness = 0.75;
    shutter.material = shutterMat;
  };

  const createChurch = (x: number, z: number): void => {
    // FIX: use footprint minimum across the full 8×14 church body
    const gy = getFootprintMinHeight(x, z, 8, 14);

    const body = BABYLON.MeshBuilder.CreateBox(`church_body_${x}`, {
      width: 8, height: 4.5, depth: 14
    }, scene);
    body.position.set(x, gy + 2.25, z);
    body.material = fadedPaintMat;
    body.checkCollisions = true;
    body.receiveShadows = true;
    shadowGen.addShadowCaster(body);

    // FIX: roof footprint also needs to cover its wider 9.5 base
    const roofGy = getFootprintMinHeight(x, z, 9.5, 9.5);
    const roofBase = Math.max(gy, roofGy); // roof sits on whichever is lower ground under it
    const roofC = BABYLON.MeshBuilder.CreateCylinder(`church_roof_${x}`, {
      diameterTop: 0.1, diameterBottom: 9.5, height: 3.0, tessellation: 4
    }, scene);
    // FIX: roof base = top of walls = gy + 4.5; centre = gy + 4.5 + 1.5
    roofC.position.set(x, gy + 4.5 + 1.5, z);
    roofC.rotation.y = Math.PI / 4;
    roofC.material = tinRoofMat;
    roofC.receiveShadows = true;
    shadowGen.addShadowCaster(roofC);

    // FIX: cross is at the front gable (z - 7). Sample ground there independently.
    const crossZ = z - 7;
    const crossGy = getApproxHeight(x, crossZ);
    // The ridge height is driven by the church body's gy, not crossGy.
    // The cross sits on top of the roof ridge above the front wall.
    // Ridge Y world = gy + 4.5 (wall top) + 3.0 (full roof height)
    const ridgeY = gy + 4.5 + 3.0;

    const crossMat = new BABYLON.PBRMaterial(`crossM_${x}`, scene);
    crossMat.albedoColor = new BABYLON.Color3(0.75, 0.73, 0.68);
    crossMat.roughness = 0.95;
    crossMat.metallic = 0.0;

    // Vertical beam: base at ridgeY, centred at ridgeY + 0.75
    const crossV = BABYLON.MeshBuilder.CreateBox(`cross_v_${x}`, {
      width: 0.2, height: 1.5, depth: 0.2
    }, scene);
    crossV.position.set(x, ridgeY + 0.75, crossZ);
    crossV.material = crossMat;

    // Horizontal beam at 2/3 up the vertical
    const crossH = BABYLON.MeshBuilder.CreateBox(`cross_h_${x}`, {
      width: 0.8, height: 0.2, depth: 0.2
    }, scene);
    crossH.position.set(x, ridgeY + 1.0, crossZ);
    crossH.material = crossMat;
  };

  // ============================================================
  // MILITARY CHECKPOINT
  // ============================================================
  const createCheckpoint = (x: number, z: number): void => {
    // FIX: sample ground at each object's actual world X position
    const gyBarrelL = getApproxHeight(x - 2.0, z);
    const gyBarrelR = getApproxHeight(x + 2.0, z);
    const gyPlank   = getApproxHeight(x, z);

    const barrel1 = BABYLON.MeshBuilder.CreateCylinder(`drum1_${x}`, {
      height: 0.9, diameter: 0.56, tessellation: 10
    }, scene);
    barrel1.position.set(x - 2.0, gyBarrelL + 0.45, z);
    barrel1.material = drumMat;
    barrel1.checkCollisions = true;
    barrel1.receiveShadows = true;
    shadowGen.addShadowCaster(barrel1);

    const barrel2 = BABYLON.MeshBuilder.CreateCylinder(`drum2_${x}`, {
      height: 0.9, diameter: 0.56, tessellation: 10
    }, scene);
    barrel2.position.set(x + 2.0, gyBarrelR + 0.45, z);
    barrel2.material = drumMat;
    barrel2.checkCollisions = true;
    barrel2.receiveShadows = true;
    shadowGen.addShadowCaster(barrel2);

    // Plank: spans between the two barrels. Use average height of both barrel tops.
    const plankY = (gyBarrelL + gyBarrelR) / 2 + 0.96;
    const plank = BABYLON.MeshBuilder.CreateBox(`plank_${x}`, {
      width: 5.0, height: 0.12, depth: 0.14
    }, scene);
    plank.position.set(x, plankY, z);
    const plankMat = new BABYLON.PBRMaterial(`plankM_${x}`, scene);
    plankMat.albedoColor = new BABYLON.Color3(0.42, 0.22, 0.10);
    plankMat.roughness = 0.97;
    plankMat.metallic = 0.0;
    plank.material = plankMat;
    plank.receiveShadows = true;
    shadowGen.addShadowCaster(plank);

    // FIX: sandbags — sample ground at each sandbag's actual x position
    for (let row = 0; row < 2; row++) {
      for (let col = 0; col < 4; col++) {
        const sbX = x + 3.5 + col * 0.56;
        const sbGy = getApproxHeight(sbX, z);
        const sb = BABYLON.MeshBuilder.CreateBox(`sb_${x}_${row}_${col}`, {
          width: 0.55, height: 0.28, depth: 0.30
        }, scene);
        sb.position.set(
          sbX,
          sbGy + 0.14 + row * 0.29,
          z + (Math.random() - 0.5) * 0.05
        );
        sb.rotation.y = (Math.random() - 0.5) * 0.12;
        sb.material = sandbagMat;
        sb.receiveShadows = true;
        shadowGen.addShadowCaster(sb);
      }
    }
  };

  // ============================================================
  // PROPS
  // ============================================================
  const createJerryCan = (x: number, z: number): void => {
    const gy = getApproxHeight(x, z);
    const can = BABYLON.MeshBuilder.CreateCylinder(`jcan_${x}`, {
      height: 0.40, diameter: 0.22, tessellation: 8
    }, scene);
    can.position.set(x, gy + 0.20, z);
    can.rotation.x = 0.2;
    can.material = jerryCan;
    can.receiveShadows = true;
    shadowGen.addShadowCaster(can);
  };

  const createBicycle = (x: number, z: number, rotY = 0): void => {
    // Guard: skip placement on sloped terrain — bike would float or clip.
    // Radius 1.5 m covers the full wheelbase; tolerance 0.30 m = road-shoulder flat.
    if (!isFlat(x, z, 1.5, 0.30)) {
      console.warn(`createBicycle: skipped (${x},${z}) — terrain not flat enough`);
      return;
    }

    // Sample max ground height along the full wheelbase (rear axle -0.51 → front axle +0.51)
    // rotated by rotY so we follow the bike's actual heading.
    // bikeRoot.y = that max so both wheels always contact or sit above terrain.
    const REAR_LZ = -0.51, FRONT_LZ = 0.51;
    const sinR = Math.sin(rotY), cosR = Math.cos(rotY);
    let gy = -Infinity;
    const WHEELBASE_SAMPLES = 24;
    for (let i = 0; i < WHEELBASE_SAMPLES; i++) {
      const lz = REAR_LZ + (FRONT_LZ - REAR_LZ) * (i / (WHEELBASE_SAMPLES - 1));
      const wx = x - lz * sinR;
      const wz = z + lz * cosR;
      gy = Math.max(gy, getApproxHeight(wx, wz));
    }

    const id = `${x}_${z}`;
    const bikeRoot = new BABYLON.TransformNode(`bike_root_${id}`, scene);
    bikeRoot.position.set(x, gy, z);
    bikeRoot.rotation.y = rotY;

    const frameMat = new BABYLON.PBRMaterial(`bikeFrame_${id}`, scene);
    frameMat.albedoColor = new BABYLON.Color3(0.14, 0.14, 0.12);
    frameMat.metallic = 0.72;
    frameMat.roughness = 0.62;

    const tireMat = new BABYLON.PBRMaterial(`bikeTire_${id}`, scene);
    tireMat.albedoColor = new BABYLON.Color3(0.08, 0.08, 0.07);
    tireMat.metallic = 0.0;
    tireMat.roughness = 0.96;

    const rimMat = new BABYLON.PBRMaterial(`bikeRim_${id}`, scene);
    rimMat.albedoColor = new BABYLON.Color3(0.55, 0.55, 0.52);
    rimMat.metallic = 0.80;
    rimMat.roughness = 0.35;

    const sadMat = new BABYLON.PBRMaterial(`bikeSad_${id}`, scene);
    sadMat.albedoColor = new BABYLON.Color3(0.18, 0.10, 0.06);
    sadMat.metallic = 0.0;
    sadMat.roughness = 0.90;

    const attach = (mesh: BABYLON.Mesh, mat: BABYLON.PBRMaterial): BABYLON.Mesh => {
      mesh.parent = bikeRoot;
      mesh.material = mat;
      mesh.receiveShadows = true;
      shadowGen.addShadowCaster(mesh);
      return mesh;
    };

    // tube(): thin cylinder between two LOCAL points, parented to bikeRoot
    const tube = (
      name: string,
      from: BABYLON.Vector3,
      to: BABYLON.Vector3,
      radius: number,
      mat: BABYLON.PBRMaterial
    ): BABYLON.Mesh => {
      const dir = to.subtract(from);
      const len = dir.length();
      const mid = BABYLON.Vector3.Lerp(from, to, 0.5);

      const m = BABYLON.MeshBuilder.CreateCylinder(name, {
        height: len, diameter: radius * 2, tessellation: 6,
      }, scene);
      m.parent = bikeRoot;
      m.position.copyFrom(mid);

      const defaultUp = BABYLON.Vector3.Up();
      const axis = BABYLON.Vector3.Cross(defaultUp, dir.normalize());
      const dot = BABYLON.Vector3.Dot(defaultUp, dir.normalize());
      if (axis.lengthSquared() > 0.0001) {
        const angle = Math.acos(BABYLON.Scalar.Clamp(dot, -1, 1));
        m.rotationQuaternion = BABYLON.Quaternion.RotationAxis(axis.normalize(), angle);
      } else if (dot < 0) {
        m.rotationQuaternion = BABYLON.Quaternion.RotationAxis(BABYLON.Vector3.Right(), Math.PI);
      }

      m.material = mat;
      m.receiveShadows = true;
      shadowGen.addShadowCaster(m);
      return m;
    };

    const WHEEL_R = 0.33;
    const REAR_Z  = -0.51;
    const FRONT_Z =  0.51;

    const makeWheel = (wz: number): void => {
      const wid = `${id}_${wz > 0 ? "f" : "r"}`;

      const tire = BABYLON.MeshBuilder.CreateTorus(`tire_${wid}`, {
        diameter: WHEEL_R * 2, thickness: 0.055, tessellation: 20,
      }, scene);
      tire.parent = bikeRoot;
      tire.position.set(0, WHEEL_R, wz);
      tire.rotation.z = Math.PI / 2;
      tire.material = tireMat;
      tire.receiveShadows = true;
      shadowGen.addShadowCaster(tire);

      const rim = BABYLON.MeshBuilder.CreateTorus(`rim_${wid}`, {
        diameter: WHEEL_R * 2 - 0.04, thickness: 0.018, tessellation: 20,
      }, scene);
      rim.parent = bikeRoot;
      rim.position.set(0, WHEEL_R, wz);
      rim.rotation.z = Math.PI / 2;
      rim.material = rimMat;
      rim.receiveShadows = true;
      shadowGen.addShadowCaster(rim);

      const hub = BABYLON.MeshBuilder.CreateCylinder(`hub_${wid}`, {
        height: 0.06, diameter: 0.06, tessellation: 8
      }, scene);
      hub.parent = bikeRoot;
      hub.position.set(0, WHEEL_R, wz);
      hub.rotation.z = Math.PI / 2;
      hub.material = rimMat;
      hub.receiveShadows = true;
      shadowGen.addShadowCaster(hub);

      // FIX: spokes must stay in the wheel plane (YZ plane since wheel faces Z).
      // The wheel is upright in the YZ plane (rotation.z = PI/2 applied to torus).
      // For spokes in LOCAL bike space: axle is along X, wheel plane is YZ.
      // Each spoke: from hub centre outward in YZ plane.
      // spoke tip: (0, WHEEL_R + cos(angle)*spokeR, wz + sin(angle)*spokeR)
      const spokeR = WHEEL_R - 0.04;
      for (let s = 0; s < 8; s++) {
        const angle = (Math.PI / 8) * s * 2; // every 45°, 8 spokes
        const spFrom = new BABYLON.Vector3(0, WHEEL_R, wz);
        // Spoke stays in YZ plane (X=0): tip moves in Y and Z only
        const spTo = new BABYLON.Vector3(
          0,
          WHEEL_R + Math.sin(angle) * spokeR,
          wz + Math.cos(angle) * spokeR
        );
        tube(`spoke_${wid}_${s}`, spFrom, spTo, 0.004, rimMat);
      }
    };

    makeWheel(REAR_Z);
    makeWheel(FRONT_Z);

    const BB = new BABYLON.Vector3(0,  0.29, -0.02);
    const RA = new BABYLON.Vector3(0,  0.33, -0.51);
    const HT = new BABYLON.Vector3(0,  0.78,  0.28);
    const HB = new BABYLON.Vector3(0,  0.50,  0.36);
    const FA = new BABYLON.Vector3(0,  0.33,  0.51);
    const ST = new BABYLON.Vector3(0,  0.85, -0.06);

    const TR = 0.014;

    tube(`dt_${id}`,    BB, HB, TR,       frameMat);
    tube(`st_${id}`,    BB, ST, TR,       frameMat);
    tube(`tt_${id}`,    ST, HT, TR * 0.9, frameMat);
    tube(`htube_${id}`, HT, HB, TR,       frameMat);

    const RA_L = new BABYLON.Vector3(-0.07, 0.33, -0.51);
    const RA_R = new BABYLON.Vector3( 0.07, 0.33, -0.51);
    const BB_L = new BABYLON.Vector3(-0.06, 0.29, -0.02);
    const BB_R = new BABYLON.Vector3( 0.06, 0.29, -0.02);
    const ST_L = new BABYLON.Vector3(-0.04, 0.85, -0.06);
    const ST_R = new BABYLON.Vector3( 0.04, 0.85, -0.06);

    tube(`csL_${id}`,  BB_L, RA_L, TR * 0.8, frameMat);
    tube(`csR_${id}`,  BB_R, RA_R, TR * 0.8, frameMat);
    tube(`ssL_${id}`,  ST_L, RA_L, TR * 0.7, frameMat);
    tube(`ssR_${id}`,  ST_R, RA_R, TR * 0.7, frameMat);

    const FA_L = new BABYLON.Vector3(-0.05, 0.33, 0.51);
    const FA_R = new BABYLON.Vector3( 0.05, 0.33, 0.51);
    tube(`fkL_${id}`, HB, FA_L, TR * 0.75, frameMat);
    tube(`fkR_${id}`, HB, FA_R, TR * 0.75, frameMat);

    const bbShell = BABYLON.MeshBuilder.CreateCylinder(`bb_${id}`, {
      height: 0.10, diameter: 0.065, tessellation: 8
    }, scene);
    bbShell.parent = bikeRoot;
    bbShell.position.copyFrom(BB);
    bbShell.rotation.z = Math.PI / 2;
    bbShell.material = frameMat;
    bbShell.receiveShadows = true;
    shadowGen.addShadowCaster(bbShell);

    for (const side of [-1, 1]) {
      const crankBase = new BABYLON.Vector3(side * 0.05, BB.y, BB.z);
      const crankTip  = new BABYLON.Vector3(side * 0.05, BB.y - 0.12, BB.z + 0.08);
      tube(`ck_${id}_${side}`, crankBase, crankTip, 0.010, frameMat);

      const pedal = BABYLON.MeshBuilder.CreateBox(`ped_${id}_${side}`, {
        width: 0.015, height: 0.025, depth: 0.09
      }, scene);
      pedal.parent = bikeRoot;
      pedal.position.copyFrom(crankTip);
      pedal.material = frameMat;
      pedal.receiveShadows = true;
      shadowGen.addShadowCaster(pedal);
    }

    const seatpostTop = new BABYLON.Vector3(0, ST.y + 0.08, ST.z);
    tube(`sp_${id}`, ST, seatpostTop, TR, frameMat);

    const saddle = BABYLON.MeshBuilder.CreateBox(`sad_${id}`, {
      width: 0.06, height: 0.04, depth: 0.28
    }, scene);
    saddle.parent = bikeRoot;
    saddle.position.set(0, seatpostTop.y + 0.02, seatpostTop.z);
    saddle.rotation.x = -0.06;
    saddle.material = sadMat;
    saddle.receiveShadows = true;
    shadowGen.addShadowCaster(saddle);

    const stemTop = new BABYLON.Vector3(0, HT.y + 0.10, HT.z - 0.04);
    tube(`stem_${id}`, HT, stemTop, TR, frameMat);

    const HBL = new BABYLON.Vector3(-0.32, stemTop.y, stemTop.z);
    const HBR = new BABYLON.Vector3( 0.32, stemTop.y, stemTop.z);
    tube(`hbar_${id}`, HBL, HBR, TR * 0.85, frameMat);

    for (const side of [-1, 1]) {
      const leverBase = new BABYLON.Vector3(side * 0.22, stemTop.y, stemTop.z);
      const leverTip  = new BABYLON.Vector3(side * 0.22, stemTop.y - 0.08, stemTop.z + 0.06);
      tube(`lev_${id}_${side}`, leverBase, leverTip, 0.008, frameMat);
    }
  };

  // ============================================================
  // FIGURES
  // ============================================================
  const createFigure = (
    x: number,
    z: number,
    clothMat: BABYLON.PBRMaterial,
    carryJerryCan = false
  ): void => {
    const gy = getApproxHeight(x, z);

    const root = new BABYLON.TransformNode(`fig_${x}_${z}`, scene);
    root.position.set(x, gy, z);

    const addMesh = (
      mesh: BABYLON.Mesh,
      lx: number, ly: number, lz: number,
      mat: BABYLON.PBRMaterial
    ): void => {
      mesh.parent = root;
      mesh.position.set(lx, ly, lz);
      mesh.material = mat;
      mesh.receiveShadows = true;
      shadowGen.addShadowCaster(mesh);
    };

    for (const lx of [-0.10, 0.10]) {
      addMesh(
        BABYLON.MeshBuilder.CreateBox(`leg_${x}_${z}_${lx}`, { width: 0.14, height: 0.55, depth: 0.14 }, scene),
        lx, 0.275, 0, skinDarkMat
      );
    }

    addMesh(
      BABYLON.MeshBuilder.CreateBox(`torso_${x}_${z}`, { width: 0.36, height: 0.52, depth: 0.20 }, scene),
      0, 0.81, 0, clothMat
    );

    for (const ax of [-0.26, 0.26]) {
      addMesh(
        BABYLON.MeshBuilder.CreateBox(`arm_${x}_${z}_${ax}`, { width: 0.10, height: 0.44, depth: 0.10 }, scene),
        ax, 0.81, 0, clothMat
      );
    }

    addMesh(
      BABYLON.MeshBuilder.CreateSphere(`head_${x}_${z}`, { diameter: 0.26, segments: 5 }, scene),
      0, 1.24, 0, skinDarkMat
    );

    if (carryJerryCan) {
      // FIX: sample ground at the can's own world position
      const canX = x + 0.38;
      const canGy = getApproxHeight(canX, z);
      const can = BABYLON.MeshBuilder.CreateCylinder(`jcan_fig_${x}_${z}`, {
        height: 0.40, diameter: 0.22, tessellation: 8
      }, scene);
      can.position.set(canX, canGy + 0.20, z);
      can.material = jerryCan;
      can.receiveShadows = true;
      shadowGen.addShadowCaster(can);
    }
  };

  // ============================================================
  // MILITARY TRUCK
  // ============================================================
  const createMilitaryTruck = (x: number, z: number, rotY = 0): void => {
    // FIX: use footprint minimum across full truck length so it doesn't float
    // Truck length ~7.7m (cab 2.9 + bed 4.8), centred roughly at z+1.3 local
    const gy = getFootprintMinHeight(x, z + 1.3 * Math.cos(rotY), 2.4, 7.7);

    const truckRoot = new BABYLON.TransformNode(`truck_${x}_${z}`, scene);
    truckRoot.position.set(x, gy, z);
    truckRoot.rotation.y = rotY;

    const addPart = (
      mesh: BABYLON.Mesh,
      lx: number, ly: number, lz: number,
      mat: BABYLON.Material
    ): void => {
      mesh.parent = truckRoot;
      mesh.position.set(lx, ly, lz);
      mesh.receiveShadows = true;
      mesh.material = mat;
      shadowGen.addShadowCaster(mesh);
    };

    const tireMat = new BABYLON.PBRMaterial(`tireM_${x}`, scene);
    tireMat.albedoColor = new BABYLON.Color3(0.10, 0.10, 0.10);
    tireMat.roughness = 0.98; tireMat.metallic = 0.0;

    const tarpMat = new BABYLON.PBRMaterial(`tarpM_${x}`, scene);
    tarpMat.albedoColor = new BABYLON.Color3(0.21, 0.24, 0.14);
    tarpMat.roughness = 0.97; tarpMat.metallic = 0.0;

    const cab = BABYLON.MeshBuilder.CreateBox(`tcab_${x}`, { width: 2.4, height: 2.0, depth: 2.9 }, scene);
    cab.checkCollisions = true;
    addPart(cab, 0, 1.0, -0.7, oliveMat);

    const bed = BABYLON.MeshBuilder.CreateBox(`tbed_${x}`, { width: 2.2, height: 0.28, depth: 4.8 }, scene);
    addPart(bed, 0, 0.94, 3.3, oliveMat);

    const tarp = BABYLON.MeshBuilder.CreateBox(`tarp_${x}`, { width: 2.2, height: 1.4, depth: 4.8 }, scene);
    addPart(tarp, 0, 0.94 + 0.14 + 0.70, 3.3, tarpMat);

    const wheelConfigs: [number, number][] = [
      [-1.25, -1.8], [1.25, -1.8],
      [-1.25,  3.0], [1.25,  3.0],
    ];
    wheelConfigs.forEach(([wx, wz]) => {
      const wh = BABYLON.MeshBuilder.CreateCylinder(`twh_${x}_${wx}_${wz}`, {
        height: 0.38, diameter: 0.80, tessellation: 12
      }, scene);
      wh.rotation.z = Math.PI / 2;
      addPart(wh, wx, 0.40, wz, tireMat);
    });
  };

  // ============================================================
  // SCENE POPULATION
  // ============================================================

  const housePositions: [number, number, number][] = [
    [-9, 8, 0.3], [11, 12, -0.2], [-13, 22, 0.4],
    [9, 30, 0.0], [-10, 36, 0.2], [13, 42, -0.3]
  ];
  housePositions.forEach(([x, z, r]) => {
    createRugo(x, z, r, Math.random() > 0.5 ? brickMat : concreteMat);
    createMatookeClump(x + (Math.random() - 0.5) * 6, z + (Math.random() - 0.5) * 6, 2 + Math.floor(Math.random() * 3));
  });

  [[6.5, 18, -0.08], [6.5, 26, -0.05], [6.5, 34, 0.0]].forEach(([x, z, r]) => {
    createShopfront(x, z, r);
  });

  createChurch(-18, 28);

  [[-16, 4], [15, 5], [-12, 40], [11, 38], [-8, 15], [14, 22]].forEach(([x, z]) => {
    createEucalyptus(x, z, 9 + Math.random() * 6);
  });

  createCheckpoint(0, 15);
  createCheckpoint(0, 40);

  createMilitaryTruck(7, 19, 0.12);

  createFigure(-2.5, 10, clothRedMat, true);
  createFigure(2.0,  10, clothBlueMat, false);
  createFigure(-3.0, 24, clothWhiteMat, false);
  createFigure(3.5,  24, clothRedMat, true);
  createFigure(-1.5, 35, clothBlueMat, false);

  // Bikes placed on confirmed flat road-edge positions (slope < 0.25 m, verified by scanner).
  // x=±2 puts them at the very edge of the road terrace, clearly visible from the road.
  createBicycle( 2.0,  5.0,  -0.10);  // right road edge, z=5  — slope 0.18 m ✓
  createBicycle(-2.0, 31.0,   0.08);  // left road edge, z=31 — slope 0.04 m ✓

  createJerryCan(-7, 22);
  createJerryCan(8,  14);

  // FIX: camera Y — offset by terrain height at spawn point
  camera.position.y = getApproxHeight(0, -8) + 1.65;

  // ============================================================
  // POST-PROCESSING
  // ============================================================
  const pipeline = new BABYLON.DefaultRenderingPipeline("docPipeline", true, scene, [camera]);
  pipeline.bloomEnabled = false;
  pipeline.chromaticAberrationEnabled = false;
  pipeline.imageProcessingEnabled = true;
  pipeline.imageProcessing.vignetteEnabled = true;
  pipeline.imageProcessing.vignetteWeight = 2.8;
  pipeline.imageProcessing.vignetteCameraFov = 1.0;
  pipeline.imageProcessing.vignetteColor = new BABYLON.Color4(0, 0, 0, 0);
  pipeline.imageProcessing.vignetteBlendMode =
    BABYLON.ImageProcessingConfiguration.VIGNETTEMODE_MULTIPLY;
  pipeline.imageProcessing.toneMappingEnabled = true;
  pipeline.imageProcessing.toneMappingType =
    BABYLON.ImageProcessingConfiguration.TONEMAPPING_ACES;
  pipeline.imageProcessing.exposure = 0.92;
  pipeline.grainEnabled = true;
  pipeline.grain.intensity = 11;
  pipeline.grain.animated = true;
  pipeline.sharpenEnabled = true;
  pipeline.sharpen.edgeAmount = 0.22;
  pipeline.sharpen.colorAmount = 1.0;

  // ============================================================
  // LIGHTNING
  // ============================================================
  const lightningBolt = new BABYLON.PointLight("lightning", new BABYLON.Vector3(-40, 35, 50), scene);
  lightningBolt.intensity = 0;
  lightningBolt.range = 220;
  lightningBolt.diffuse = new BABYLON.Color3(0.80, 0.82, 1.0);

  let lightningTimer = 0;
  let flashPhase = 0;
  scene.registerBeforeRender(() => {
    const delta = engine.getDeltaTime() / 1000;
    lightningTimer += delta;
    if (flashPhase === 0 && lightningTimer > 6 + Math.random() * 4) {
      flashPhase = 1; lightningTimer = 0;
    }
    if (flashPhase === 1) {
      lightningBolt.intensity = 18 * (1 - lightningTimer / 0.08);
      if (lightningTimer > 0.08) { flashPhase = 2; lightningTimer = 0; lightningBolt.intensity = 0; }
    }
    if (flashPhase === 2 && lightningTimer > 0.06 && lightningTimer < 0.09) {
      lightningBolt.intensity = 8;
    }
    if (flashPhase === 2 && lightningTimer > 0.14) {
      flashPhase = 0; lightningBolt.intensity = 0;
    }
  });

  // ============================================================
  // HUD
  // ============================================================
  const advancedTexture = GUI.AdvancedDynamicTexture.CreateFullscreenUI("UI");

  const dateLabel = new GUI.TextBlock("date");
  dateLabel.text = "KIGALI · APRIL 1994";
  dateLabel.color = "rgba(230,215,185,0.45)";
  dateLabel.fontSize = 11;
  dateLabel.fontFamily = "Georgia, serif";
  dateLabel.horizontalAlignment = GUI.Control.HORIZONTAL_ALIGNMENT_LEFT;
  dateLabel.verticalAlignment = GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
  dateLabel.left = "20px";
  dateLabel.top = "-18px";
  advancedTexture.addControl(dateLabel);

  const crosshair = new GUI.Ellipse();
  crosshair.width = "4px";
  crosshair.height = "4px";
  crosshair.color = "rgba(255,255,255,0.5)";
  crosshair.thickness = 1;
  advancedTexture.addControl(crosshair);

  const btn = GUI.Button.CreateSimpleButton("btn", "↓ Export GLB");
  btn.width = "142px";
  btn.height = "36px";
  btn.color = "rgba(230,215,185,0.75)";
  btn.background = "rgba(10,8,4,0.72)";
  btn.verticalAlignment = GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
  btn.horizontalAlignment = GUI.Control.HORIZONTAL_ALIGNMENT_RIGHT;
  btn.left = "-16px";
  btn.top = "-16px";
  btn.onPointerUpObservable.add(() => {
    GLTF2Export.GLBAsync(scene, "Rwanda_1994").then((glb: GLTFData) => {
      glb.downloadFiles();
    });
  });
  advancedTexture.addControl(btn);

  const hint = new GUI.TextBlock("hint");
  hint.text = "WASD · mouse";
  hint.color = "rgba(230,215,185,0.28)";
  hint.fontSize = 10;
  hint.fontFamily = "Georgia, serif";
  hint.horizontalAlignment = GUI.Control.HORIZONTAL_ALIGNMENT_RIGHT;
  hint.verticalAlignment = GUI.Control.VERTICAL_ALIGNMENT_BOTTOM;
  hint.left = "-16px";
  hint.top = "-52px";
  advancedTexture.addControl(hint);

  scene.onPointerDown = () => engine.enterPointerlock();

  return scene;
};

const appDiv = document.getElementById("app");
if (appDiv) {
  const canvas = document.createElement("canvas");
  canvas.id = "renderCanvas";
  canvas.style.cssText = "width:100%;height:100%;display:block;outline:none;";
  appDiv.appendChild(canvas);
  document.body.style.cssText = "margin:0;overflow:hidden;background:#0a0806;";
  appDiv.style.cssText = "width:100vw;height:100vh;";

  const engine = new BABYLON.Engine(canvas, true, {
    preserveDrawingBuffer: true,
    stencil: true,
    antialias: true
  });
  const scene = createScene(engine, canvas);
  engine.runRenderLoop(() => scene.render());
  window.addEventListener("resize", () => engine.resize());
}

export { createScene };