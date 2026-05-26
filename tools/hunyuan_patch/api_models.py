"""
Pydantic models for Hunyuan3D API server.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    """Request model for 3D generation API"""
    image: str = Field(
        ...,
        description="Base64 encoded input image for 3D generation",
        example="iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAAEElEQVR4nGP8z4AATAxEcQAz0QEHOoQ+uAAAAABJRU5ErkJggg=="
    )
    images: Optional[List[str]] = Field(
        None,
        description="Optional list of base64 encoded view images for multi-view generation (Zero123++ output). When provided, model_worker uses these instead of the single 'image' field."
    )
    remove_background: bool = Field(
        True,
        description="Whether to automatically remove background from input image"
    )
    texture: bool = Field(
        False,
        description="Whether to generate textures for the 3D model"
    )
    seed: int = Field(
        1234,
        description="Random seed for reproducible generation",
        ge=0,
        le=2**32-1
    )
    octree_resolution: int = Field(
        256,
        description="Resolution of the octree for mesh generation. "
                    "512 is the standard cap; 768 is used for hero figures on "
                    "high-VRAM GPUs (RTX 5090 32 GB). Raised to 1024 to allow "
                    "future exploration without another image rebuild.",
        ge=64,
        le=1024
    )
    num_inference_steps: int = Field(
        50,
        description="Number of inference steps for generation. Default raised to 50 for triple-A quality; upstream pipeline supports up to 200.",
        ge=1,
        le=200
    )
    guidance_scale: float = Field(
        5.0,
        description="Guidance scale for generation",
        ge=0.1,
        le=20.0
    )
    num_chunks: int = Field(
        8000,
        description="Number of chunks for processing",
        ge=1000,
        le=20000
    )
    face_count: int = Field(
        40000,
        description="Maximum number of faces for texture generation",
        ge=1000,
        le=100000
    )
    type: Literal["glb", "obj"] = Field(
        "glb",
        description="Output format type (glb or obj)"
    )


class GenerationResponse(BaseModel):
    """Response model for generation status"""
    uid: str = Field(..., description="Unique identifier for the generation task")


class StatusResponse(BaseModel):
    """Response model for status endpoint"""
    status: str = Field(..., description="Status of the generation task")
    model_base64: Optional[str] = Field(
        None,
        description="Base64 encoded generated model file (only when status is 'completed')"
    )
    message: Optional[str] = Field(
        None,
        description="Error message (only when status is 'error')"
    )


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Health status")
    worker_id: str = Field(..., description="Worker identifier")
