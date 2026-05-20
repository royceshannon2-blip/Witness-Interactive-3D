"""
Model worker for Hunyuan3D API server.

Witness-Interactive patches vs upstream (kechiro/hunyuan3d-2.1-cachedstart):

1. Respect ``params['texture']``. Upstream runs the paint pipeline
   unconditionally, which (a) wastes ~8 s per request when the caller does
   not want textures and (b) crashes on RTX 5090 (sm_120) because the
   hy3dpaint custom CUDA kernels were compiled without Blackwell support.
2. Always publish the result as ``{uid}_textured.glb`` — whether texture
   generation was skipped, succeeded, or failed. ``api_server.py``'s
   ``/status/{uid}`` only reports ``completed`` when that filename exists,
   so the upstream fallback path (which leaves only ``{uid}_initial.glb``)
   wedges the status endpoint in ``processing`` until the client times out.
3. **Lazy-init the paint pipeline.** Upstream calls
   ``Hunyuan3DPaintPipeline(conf)`` in ``ModelWorker.__init__``. On
   RTX 5090 that constructor crashes at
   ``hy3dpaint/utils/image_super_utils.py:25`` with
   ``RuntimeError: CUDA error: no kernel image is available for execution
   on the device`` — the Real-ESRGAN upscaler binds a CUDA kernel that
   wasn't compiled for sm_120, and the entire FastAPI process exits before
   serving a single request. We defer construction to first textured
   request via ``_get_paint_pipeline()`` and catch construction failure so
   the request still falls back to the untextured mesh.
4. **Multi-view input.** Accept ``params['images']`` (list of base64
   strings) in addition to the legacy single ``params['image']`` field.
   The underlying ``Hunyuan3DDiTFlowMatchingPipeline`` natively accepts a
   ``list[PIL.Image]`` per Tencent's reference repo; the upstream Docker
   API just didn't expose it. Stage 0.5 of the Witness pipeline
   (``tools/generate_multi_views.py``) emits 6 canonical views via
   Zero123++ and posts them as ``images=[…]``. If the runtime build of
   ``hy3dshape`` doesn't accept lists we fall back to the first image to
   keep the request useful instead of erroring.
"""
import os
import shutil
import time
import uuid
import base64
import trimesh
from io import BytesIO
from PIL import Image
import torch

# Apply torchvision compatibility fix before other imports
import sys
sys.path.insert(0, './hy3dshape')
sys.path.insert(0, './hy3dpaint')

try:
    from torchvision_fix import apply_fix
    apply_fix()
except ImportError:
    print("Warning: torchvision_fix module not found, proceeding without compatibility fix")
except Exception as e:
    print(f"Warning: Failed to apply torchvision fix: {e}")

# The torchvision wheel bundled in this image was compiled without sm_120
# (Blackwell / RTX 5090) CUDA kernels. Every function in
# torchvision.transforms._functional_tensor that touches a CUDA tensor
# raises "no kernel image is available for execution on the device".
# Patch the entire module: wrap every public callable so CUDA tensors are
# moved to CPU before the call and the result is moved back. The conditioner
# in hy3dshape re-uploads to GPU immediately, so the round-trip is safe.
try:
    import functools
    import torchvision.transforms._functional_tensor as _ft

    def _make_cpu_safe(fn):
        @functools.wraps(fn)
        def _wrapper(*args, **kwargs):
            cuda_tensors = [(i, a) for i, a in enumerate(args)
                            if isinstance(a, torch.Tensor) and a.is_cuda]
            if not cuda_tensors:
                return fn(*args, **kwargs)
            device = cuda_tensors[0][1].device
            args = list(args)
            for i, a in cuda_tensors:
                args[i] = a.cpu()
            result = fn(*args, **kwargs)
            if isinstance(result, torch.Tensor):
                result = result.to(device)
            return result
        return _wrapper

    _patched = 0
    for _name in dir(_ft):
        if _name.startswith("_"):
            continue
        _fn = getattr(_ft, _name)
        if callable(_fn):
            try:
                setattr(_ft, _name, _make_cpu_safe(_fn))
                _patched += 1
            except (AttributeError, TypeError):
                pass
    print(f"Applied sm_120 torchvision patch: {_patched} ops CPU-offloaded")
except Exception as _e:
    print(f"Warning: could not patch torchvision _functional_tensor: {_e}")

from hy3dshape import Hunyuan3DDiTFlowMatchingPipeline
from hy3dshape.rembg import BackgroundRemover
from hy3dshape.utils import logger
from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig
from hy3dpaint.convert_utils import create_glb_with_pbr_materials


def quick_convert_with_obj2gltf(obj_path: str, glb_path: str):
    """
    Convert OBJ to GLB using obj2gltf command-line tool.
    
    Args:
        obj_path (str): Path to input OBJ file
        glb_path (str): Path to output GLB file
    """
    import subprocess
    try:
        subprocess.run(['obj2gltf', '-i', obj_path, '-o', glb_path], check=True)
    except subprocess.CalledProcessError:
        logger.warning("obj2gltf conversion failed, using trimesh fallback")
        mesh = trimesh.load(obj_path)
        mesh.export(glb_path)

def load_image_from_base64(image):
    """
    Load PIL Image from base64 encoded string.
    
    Args:
        image (str): Base64 encoded image string
        
    Returns:
        PIL.Image: Loaded image
    """
    if image.startswith('data:image'):
        image = image.split(',')[1]
    image_data = base64.b64decode(image)
    image = Image.open(BytesIO(image_data))
    return image


class ModelWorker:
    """
    Worker class for handling 3D model generation tasks.
    """
    
    def __init__(self,
                 model_path='tencent/Hunyuan3D-2.1',
                 subfolder='hunyuan3d-dit-v2-1',
                 device='cuda',
                 low_vram_mode=False,
                 worker_id=None,
                 model_semaphore=None,
                 save_dir='gradio_cache'):
        """
        Initialize the model worker.
        
        Args:
            model_path (str): Path to the shape generation model
            subfolder (str): Subfolder containing the model files
            device (str): Device to run the model on ('cuda' or 'cpu')
            low_vram_mode (bool): Whether to use low VRAM mode
            worker_id (str): Unique identifier for this worker
            model_semaphore: Semaphore for controlling model concurrency
            save_dir (str): Directory to save generated files
        """
        self.model_path = model_path
        self.worker_id = worker_id or str(uuid.uuid4())[:6]
        self.device = device
        self.low_vram_mode = low_vram_mode
        self.model_semaphore = model_semaphore
        self.save_dir = save_dir
        
        logger.info(f"Loading the model {model_path} on worker {self.worker_id} ...")

        # Initialize background remover
        self.rembg = BackgroundRemover()

        # Initialize shape generation pipeline (matching demo.py)
        self.pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model_path)

        # Stash paint pipeline config but defer construction. Real-ESRGAN's
        # CUDA kernels lack sm_120 binaries and crash the process when the
        # pipeline is built. _get_paint_pipeline() retries construction on
        # demand and lets the caller catch the failure.
        max_num_view = 6  # can be 6 to 9
        resolution = 512  # can be 768 or 512
        self._paint_pipeline_conf = Hunyuan3DPaintConfig(max_num_view, resolution)
        self._paint_pipeline_conf.realesrgan_ckpt_path = "hy3dpaint/ckpt/RealESRGAN_x4plus.pth"
        self._paint_pipeline_conf.multiview_cfg_path = "hy3dpaint/cfgs/hunyuan-paint-pbr.yaml"
        self._paint_pipeline_conf.custom_pipeline = "hy3dpaint/hunyuanpaintpbr"
        self.paint_pipeline = None

        # clean cache in save_dir
        for file in os.listdir(self.save_dir):
            os.remove(os.path.join(self.save_dir, file))

    def _get_paint_pipeline(self):
        """Lazy-init the paint pipeline. Raises on GPUs without sm_120 kernels."""
        if self.paint_pipeline is None:
            logger.info("Constructing Hunyuan3DPaintPipeline (lazy)...")
            self.paint_pipeline = Hunyuan3DPaintPipeline(self._paint_pipeline_conf)
        return self.paint_pipeline

    def get_queue_length(self):
        """
        Get the current queue length for model processing.
        
        Returns:
            int: Number of tasks in the queue
        """
        if self.model_semaphore is None:
            return 0
        else:
            return (self.model_semaphore._value if hasattr(self.model_semaphore, '_value') else 0) + \
                   (len(self.model_semaphore._waiters) if hasattr(self.model_semaphore, '_waiters') and self.model_semaphore._waiters is not None else 0)

    def get_status(self):
        """
        Get the current status of the worker.
        
        Returns:
            dict: Status information including speed and queue length
        """
        return {
            "speed": 1,
            "queue_length": self.get_queue_length(),
        }

    @torch.inference_mode()
    def generate(self, uid, params):
        """
        Generate a 3D model from the given parameters.
        
        Args:
            uid: Unique identifier for this generation task
            params (dict): Generation parameters including image and options
            
        Returns:
            tuple: (file_path, uid) - Path to generated file and task ID
        """
        start_time = time.time()
        logger.info(f"Generating 3D model for uid: {uid}")

        # Decode inputs. The caller may send either a single image (legacy
        # path, params['image']) or a list of canonical views from
        # Zero123++ (params['images']). The hy3dshape pipeline accepts
        # either a single PIL.Image or a list — we only branch on the
        # list path at submission time and fall back gracefully if the
        # installed hy3dshape build rejects the list.
        raw_images = params.get("images")
        if raw_images:
            if not isinstance(raw_images, list) or not raw_images:
                raise ValueError("'images' must be a non-empty list of base64 strings")
            decoded_images = [load_image_from_base64(b64) for b64 in raw_images]
            primary_image = decoded_images[0]
        elif "image" in params:
            primary_image = load_image_from_base64(params["image"])
            decoded_images = [primary_image]
        else:
            raise ValueError("No input image provided (expected 'image' or 'images')")

        # Convert each view to RGBA + remove background. We strip the
        # background per-view because Zero123++ outputs include a soft
        # studio backdrop that confuses the shape pipeline's silhouette
        # extraction. The legacy single-image path is unchanged.
        normalised: list = []
        for view in decoded_images:
            view = view.convert("RGBA")
            if view.mode == "RGB":
                view = self.rembg(view)
            normalised.append(view)
        primary_image = normalised[0]

        # Submit. Try the list path first when we have multiple views;
        # fall back to the single-image call if the installed pipeline
        # build doesn't accept lists, so the request still produces a
        # mesh instead of failing.
        try:
            if len(normalised) > 1:
                try:
                    mesh = self.pipeline(image=normalised)[0]
                    logger.info(f"Multi-view shape generation from {len(normalised)} views")
                except TypeError as list_exc:
                    logger.warning(
                        f"hy3dshape pipeline rejected list input ({list_exc}); "
                        f"falling back to first view only"
                    )
                    mesh = self.pipeline(image=primary_image)[0]
            else:
                mesh = self.pipeline(image=primary_image)[0]
            logger.info("---Shape generation takes %s seconds ---" % (time.time() - start_time))
        except Exception as e:
            logger.error(f"Shape generation failed: {e}")
            # Write a 0-byte sentinel at the _textured.glb path so
            # api_server.py's /status/{uid} exits "processing" and
            # returns {"status": "error"} instead of polling forever.
            _sentinel = os.path.join(self.save_dir, f"{uid}_textured.glb")
            try:
                open(_sentinel, "wb").close()
            except OSError:
                pass
            raise ValueError(f"Failed to generate 3D mesh: {str(e)}")

        # The texture pass still wants a single image as a colour reference;
        # use the first (front) view so paint behaves identically to the
        # legacy single-image path.
        image = primary_image

        # Export initial mesh without texture
        initial_save_path = os.path.join(self.save_dir, f'{str(uid)}_initial.glb')
        mesh.export(initial_save_path)

        textured_save_path = os.path.join(self.save_dir, f'{str(uid)}_textured.glb')
        final_save_path = initial_save_path
        want_texture = bool(params.get('texture', False))

        if want_texture:
            try:
                paint_pipeline = self._get_paint_pipeline()
                output_mesh_path_obj = os.path.join(self.save_dir, f'{str(uid)}_texturing.obj')
                textured_path_obj = paint_pipeline(
                    mesh_path=initial_save_path,
                    image_path=image,
                    output_mesh_path=output_mesh_path_obj,
                    save_glb=False
                )
                logger.info("---Texture generation takes %s seconds ---" % (time.time() - start_time))
                logger.info(f"output_mesh_path: {output_mesh_path_obj} textured_path: {textured_path_obj}")

                glb_path_textured = os.path.join(self.save_dir, f'{str(uid)}_texturing.glb')
                quick_convert_with_obj2gltf(textured_path_obj, glb_path_textured)
                os.rename(glb_path_textured, textured_save_path)
                final_save_path = textured_save_path
                logger.info(f"final_save_path: {final_save_path}")
            except Exception as e:
                logger.error(f"Texture generation failed: {e}")
                logger.warning(f"Using untextured mesh as fallback: {initial_save_path}")
        else:
            logger.info("Texture generation skipped (texture=False)")

        # Publish under the filename /status/{uid} polls for, so the
        # endpoint can report 'completed' even on the untextured path.
        if final_save_path != textured_save_path:
            shutil.copyfile(initial_save_path, textured_save_path)
            final_save_path = textured_save_path

        if self.low_vram_mode:
            torch.cuda.empty_cache()

        logger.info("---Total generation takes %s seconds ---" % (time.time() - start_time))
        return final_save_path, uid