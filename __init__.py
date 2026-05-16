"""ZenMux image generation backend.

Exposes image generation models hosted on ZenMux as an
:class:`ImageGenProvider` implementation.

Supported models
----------------
- ``openai/gpt-image-2`` — via OpenAI Images API protocol
  (``POST /v1/images/generations``)
- ``google/gemini-3.1-flash-image-preview`` — via Vertex AI protocol
  (``POST /vertex-ai/v1/models/…:generateContent``)

Both models are accessed through the ZenMux API gateway using the
``ZENMUX_API_KEY`` credential.

Selection precedence (first hit wins):
1. ``ZENMUX_IMAGE_MODEL`` env var
2. ``image_gen.zenmux.model`` in ``config.yaml``
3. ``image_gen.model`` in ``config.yaml`` (when it matches a catalog entry)
4. :data:`DEFAULT_MODEL` — ``openai/gpt-image-2``
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    resolve_aspect_ratio,
    save_b64_image,
    success_response,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZENMUX_OPENAI_BASE = "https://zenmux.ai/api/v1"
ZENMUX_VERTEX_BASE = "https://zenmux.ai/api/vertex-ai"

# ---------------------------------------------------------------------------
# Model catalog
# ---------------------------------------------------------------------------

_MODELS: Dict[str, Dict[str, Any]] = {
    "openai/gpt-image-2": {
        "display": "GPT Image 2 (ZenMux)",
        "speed": "~15-40s",
        "strengths": "OpenAI gpt-image-2 via ZenMux; high quality, text-in-image",
        "protocol": "openai",  # OpenAI Images API
        "quality": "medium",
    },
    "openai/gpt-image-2-high": {
        "display": "GPT Image 2 High (ZenMux)",
        "speed": "~40-120s",
        "strengths": "Highest fidelity gpt-image-2 via ZenMux",
        "protocol": "openai",
        "quality": "high",
    },
    "google/gemini-3.1-flash-image-preview": {
        "display": "Gemini 3.1 Flash Image (ZenMux)",
        "speed": "~10-30s",
        "strengths": "Google Gemini image generation via ZenMux Vertex AI; fast",
        "protocol": "vertex",  # Vertex AI generateContent
    },
}

DEFAULT_MODEL = "openai/gpt-image-2"

# Size mapping for OpenAI protocol
_OPENAI_SIZES = {
    "landscape": "1536x1024",
    "square": "1024x1024",
    "portrait": "1024x1536",
}

# Size mapping for Vertex AI protocol (aspectRatio parameter)
_VERTEX_ASPECT_RATIOS = {
    "landscape": "16:9",
    "square": "1:1",
    "portrait": "9:16",
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _load_zenmux_config() -> Dict[str, Any]:
    """Read ``image_gen.zenmux`` from config.yaml."""
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
        section = cfg.get("image_gen") if isinstance(cfg, dict) else None
        return section if isinstance(section, dict) else {}
    except Exception as exc:
        logger.debug("Could not load image_gen config: %s", exc)
        return {}


def _resolve_model() -> Tuple[str, Dict[str, Any]]:
    """Decide which model to use and return ``(model_id, meta)``."""
    env_override = os.environ.get("ZENMUX_IMAGE_MODEL")
    if env_override and env_override in _MODELS:
        return env_override, _MODELS[env_override]

    cfg = _load_zenmux_config()
    zenmux_cfg = cfg.get("zenmux") if isinstance(cfg.get("zenmux"), dict) else {}
    candidate: Optional[str] = None
    if isinstance(zenmux_cfg, dict):
        value = zenmux_cfg.get("model")
        if isinstance(value, str) and value in _MODELS:
            candidate = value
    if candidate is None:
        top = cfg.get("model")
        if isinstance(top, str) and top in _MODELS:
            candidate = top

    if candidate is not None:
        return candidate, _MODELS[candidate]

    return DEFAULT_MODEL, _MODELS[DEFAULT_MODEL]


def _get_api_key() -> str:
    """Read the ZenMux API key from env."""
    return (os.environ.get("ZENMUX_API_KEY") or "").strip()


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------


def _generate_openai(
    prompt: str,
    model_id: str,
    meta: Dict[str, Any],
    aspect: str,
    api_key: str,
) -> Dict[str, Any]:
    """Generate image via OpenAI Images API (``/v1/images/generations``)."""
    size = _OPENAI_SIZES.get(aspect, _OPENAI_SIZES["square"])
    quality = meta.get("quality", "medium")

    payload: Dict[str, Any] = {
        "model": "openai/gpt-image-2",  # API model ID
        "prompt": prompt,
        "size": size,
        "n": 1,
        "quality": quality,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{ZENMUX_OPENAI_BASE}/images/generations",
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        resp = exc.response
        status = resp.status_code if resp is not None else 0
        try:
            err_msg = resp.json().get("error", {}).get("message", resp.text[:300])
        except Exception:
            err_msg = resp.text[:300] if resp is not None else str(exc)
        logger.error("ZenMux OpenAI image gen failed (%d): %s", status, err_msg)
        return error_response(
            error=f"ZenMux image generation failed ({status}): {err_msg}",
            error_type="api_error",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )
    except requests.Timeout:
        return error_response(
            error="ZenMux image generation timed out (120s)",
            error_type="timeout",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )
    except requests.ConnectionError as exc:
        return error_response(
            error=f"ZenMux connection error: {exc}",
            error_type="connection_error",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )

    try:
        result = response.json()
    except Exception as exc:
        return error_response(
            error=f"ZenMux returned invalid JSON: {exc}",
            error_type="invalid_response",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )

    data = result.get("data", [])
    if not data:
        return error_response(
            error="ZenMux returned no image data",
            error_type="empty_response",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )

    first = data[0]
    b64 = first.get("b64_json")
    url = first.get("url")

    if b64:
        try:
            saved_path = save_b64_image(b64, prefix="zenmux_openai")
        except Exception as exc:
            return error_response(
                error=f"Could not save image to cache: {exc}",
                error_type="io_error",
                provider="zenmux",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )
        image_ref = str(saved_path)
    elif url:
        image_ref = url
    else:
        return error_response(
            error="ZenMux response contained neither b64_json nor URL",
            error_type="empty_response",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )

    extra: Dict[str, Any] = {"size": size, "quality": quality}
    revised_prompt = first.get("revised_prompt")
    if revised_prompt:
        extra["revised_prompt"] = revised_prompt

    return success_response(
        image=image_ref,
        model=model_id,
        prompt=prompt,
        aspect_ratio=aspect,
        provider="zenmux",
        extra=extra,
    )


def _generate_vertex(
    prompt: str,
    model_id: str,
    meta: Dict[str, Any],
    aspect: str,
    api_key: str,
) -> Dict[str, Any]:
    """Generate image via Vertex AI generateContent protocol.

    ZenMux exposes Gemini image models at:
        ``POST /vertex-ai/v1/models/{model}:generateContent``

    The request uses the Google Vertex AI ``generateContent`` format with
    ``responseModalities: ["TEXT", "IMAGE"]`` and an optional aspect ratio.
    The response contains ``inlineData`` with base64-encoded image bytes.
    """
    aspect_ratio_val = _VERTEX_ASPECT_RATIOS.get(aspect, "1:1")

    payload: Dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    # Vertex AI URL format: base/v1/models/{model}:generateContent
    url = f"{ZENMUX_VERTEX_BASE}/v1/models/{model_id}:generateContent"

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        resp = exc.response
        status = resp.status_code if resp is not None else 0
        try:
            err_body = resp.json()
            err_msg = (
                err_body.get("error", {}).get("message", "")
                or resp.text[:300]
            )
        except Exception:
            err_msg = resp.text[:300] if resp is not None else str(exc)
        logger.error("ZenMux Vertex AI image gen failed (%d): %s", status, err_msg)
        return error_response(
            error=f"ZenMux Gemini image generation failed ({status}): {err_msg}",
            error_type="api_error",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )
    except requests.Timeout:
        return error_response(
            error="ZenMux Gemini image generation timed out (120s)",
            error_type="timeout",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )
    except requests.ConnectionError as exc:
        return error_response(
            error=f"ZenMux connection error: {exc}",
            error_type="connection_error",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )

    try:
        result = response.json()
    except Exception as exc:
        return error_response(
            error=f"ZenMux returned invalid JSON: {exc}",
            error_type="invalid_response",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )

    # Parse Vertex AI response: candidates[0].content.parts[] -> inlineData
    candidates = result.get("candidates", [])
    if not candidates:
        return error_response(
            error="ZenMux Vertex AI returned no candidates",
            error_type="empty_response",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )

    # Find the first inlineData part with image
    parts = candidates[0].get("content", {}).get("parts", [])
    image_b64: Optional[str] = None
    text_response: Optional[str] = None

    for part in parts:
        inline_data = part.get("inlineData") or part.get("inline_data")
        if inline_data and inline_data.get("data"):
            image_b64 = inline_data["data"]
            break
        if part.get("text"):
            text_response = part["text"]

    if not image_b64:
        # Some models might return image in generateImages format
        generated_images = result.get("generatedImages", [])
        if generated_images:
            first_img = generated_images[0]
            img_data = first_img.get("image", {})
            image_b64 = img_data.get("imageBytes") or img_data.get("bytesBase64Encoded")

    if not image_b64:
        hint = f" Model text response: {text_response[:200]}" if text_response else ""
        return error_response(
            error=f"ZenMux Vertex AI response contained no image data.{hint}",
            error_type="empty_response",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )

    try:
        saved_path = save_b64_image(image_b64, prefix="zenmux_gemini")
    except Exception as exc:
        return error_response(
            error=f"Could not save image to cache: {exc}",
            error_type="io_error",
            provider="zenmux",
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
        )

    extra: Dict[str, Any] = {"aspect_ratio": aspect_ratio_val}
    if text_response:
        extra["text_response"] = text_response[:500]

    return success_response(
        image=str(saved_path),
        model=model_id,
        prompt=prompt,
        aspect_ratio=aspect,
        provider="zenmux",
        extra=extra,
    )


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class ZenMuxImageGenProvider(ImageGenProvider):
    """ZenMux image generation backend — OpenAI & Gemini models."""

    # Prompt-keyword → model mapping (case-insensitive substring match)
    _PROMPT_HINTS: Dict[str, str] = {
        "gemini": "google/gemini-3.1-flash-image-preview",
        "gpt-image": "openai/gpt-image-2",
        "gpt image": "openai/gpt-image-2",
        "openai": "openai/gpt-image-2",
    }

    def _resolve_model_from_kwargs_or_prompt(
        self,
        prompt: str,
        kwargs: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """Resolve model with full fallback chain.

        Priority (first match wins):
        1. Explicit ``model`` kwarg (from source-level tool parameter)
        2. Prompt keyword hint (e.g. "用 Gemini 画一只猫")
        3. ``ZENMUX_IMAGE_MODEL`` env var
        4. ``image_gen.zenmux.model`` in config.yaml
        5. ``DEFAULT_MODEL``
        """
        # 1. Explicit kwarg from tool parameter
        model_override = kwargs.get("model")
        if model_override and isinstance(model_override, str) and model_override in _MODELS:
            return model_override, _MODELS[model_override]

        # 2. Prompt keyword hints — scan for known model names in the prompt
        prompt_lower = prompt.lower()
        for hint, model_id in self._PROMPT_HINTS.items():
            if hint in prompt_lower and model_id in _MODELS:
                logger.debug("Prompt hint '%s' matched model '%s'", hint, model_id)
                return model_id, _MODELS[model_id]

        # 3-5. Fall back to standard resolution (env > config > default)
        return _resolve_model()

    @property
    def name(self) -> str:
        return "zenmux"

    @property
    def display_name(self) -> str:
        return "ZenMux"

    def is_available(self) -> bool:
        return bool(_get_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": model_id,
                "display": meta.get("display", model_id),
                "speed": meta.get("speed", ""),
                "strengths": meta.get("strengths", ""),
            }
            for model_id, meta in _MODELS.items()
        ]

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "ZenMux",
            "badge": "paid",
            "tag": "OpenAI & Gemini image generation via ZenMux API",
            "env_vars": [
                {
                    "key": "ZENMUX_API_KEY",
                    "prompt": "ZenMux API key",
                    "url": "https://zenmux.ai",
                },
            ],
        }

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate an image using ZenMux-hosted models.

        Accepts an optional ``model`` kwarg (via **kwargs) that overrides
        the default model from config / env. The value must match a key in
        the ``_MODELS`` catalog; unrecognised values are silently ignored
        and the default is used instead.

        As a fallback when no explicit ``model`` kwarg is provided, the
        prompt is scanned for model-hint keywords (e.g. "gemini", "gpt")
        so that prompts like "用 Gemini 画一只猫" automatically route
        to the correct backend even when the source-level model parameter
        is unavailable (e.g. after a Hermes upgrade overwrites the patch).
        """
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)

        if not prompt:
            return error_response(
                error="Prompt is required and must be a non-empty string",
                error_type="invalid_argument",
                provider="zenmux",
                aspect_ratio=aspect,
            )

        api_key = _get_api_key()
        if not api_key:
            return error_response(
                error="ZENMUX_API_KEY not set. Add it to ~/.hermes/.env or run `hermes setup`.",
                error_type="missing_api_key",
                provider="zenmux",
                aspect_ratio=aspect,
            )

        # Resolve model (priority: kwarg > prompt hint > env var > config > default)
        model_id, meta = self._resolve_model_from_kwargs_or_prompt(prompt, kwargs)

        protocol = meta.get("protocol", "openai")

        if protocol == "vertex":
            return _generate_vertex(prompt, model_id, meta, aspect, api_key)
        else:
            return _generate_openai(prompt, model_id, meta, aspect, api_key)


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------


def register(ctx: Any) -> None:
    """Register this provider with the image gen registry."""
    ctx.register_image_gen_provider(ZenMuxImageGenProvider())
