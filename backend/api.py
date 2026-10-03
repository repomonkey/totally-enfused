"""
pywebview JS bridge. All public methods are callable from the frontend as:
  window.pywebview.api.<method_name>(args)
"""

import os
import shutil
import tempfile
import threading
from pathlib import Path

from . import settings as settings_mod
from . import presets as presets_mod
from . import image_utils
from .image_utils import needs_raw_conversion, convert_raws_to_tiff
from .align_runner import find_align_image_stack, align
from .enfuse_runner import find_enfuse, blend

_window = None  # set by main.py after window creation


def set_window(w):
    global _window
    _window = w


def _emit(event: str, payload: dict):
    """Send an event to the frontend via JS evaluation."""
    if _window:
        import json
        # Double-encode: the inner dumps is the payload, the outer makes it a safe JS string literal
        _window.evaluate_js(f"window.__te_event({json.dumps(event)}, JSON.parse({json.dumps(json.dumps(payload))}))")


class API:
    # ------------------------------------------------------------------ #
    # Tool detection
    # ------------------------------------------------------------------ #

    def check_tools(self):
        return {
            "enfuse": find_enfuse(),
            "align_image_stack": find_align_image_stack(),
        }

    # ------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------ #

    def get_settings(self):
        return settings_mod.load()

    def save_settings(self, data: dict):
        settings_mod.save(data)
        return True

    # ------------------------------------------------------------------ #
    # Presets
    # ------------------------------------------------------------------ #

    def get_presets(self):
        return presets_mod.load_all()

    def save_preset(self, key: str, preset: dict):
        presets_mod.save_custom(key, preset)
        return True

    def delete_preset(self, key: str):
        presets_mod.delete_custom(key)
        return True

    # ------------------------------------------------------------------ #
    # Image loading
    # ------------------------------------------------------------------ #

    def get_image_info(self, path: str):
        if not image_utils.is_supported(path):
            return {"error": f"Unsupported format: {Path(path).suffix}"}
        return image_utils.get_image_info(path)

    def get_thumbnail(self, path: str):
        return image_utils.get_thumbnail_b64(path)

    def get_preview(self, path: str):
        return image_utils.get_preview_b64(path)

    def open_file_dialog(self):
        """Open native file dialog and return selected paths."""
        import webview
        if _window:
            result = _window.create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=True,
                file_types=(
                    "Image files (*.jpg;*.jpeg;*.tif;*.tiff;*.png;*.cr2;*.cr3;*.nef;*.arw;*.orf;*.raf;*.dng;*.rw2)",
                    "All files (*.*)",
                ),
            )
            return list(result) if result else []
        return []

    def open_folder_dialog(self):
        import webview
        if _window:
            result = _window.create_file_dialog(webview.FileDialog.FOLDER)
            return result[0] if result else ""
        return ""

    # ------------------------------------------------------------------ #
    # Processing
    # ------------------------------------------------------------------ #

    def process(self, params: dict):
        """
        Kick off the full align+blend pipeline in a background thread.
        Progress is pushed via JS events.

        params keys:
          input_paths       list[str]
          output_path       str
          align_enabled     bool
          align_mode        str
          align_grid_points int
          align_crop        bool
          exposure_weight   float
          saturation_weight float
          contrast_weight   float
          hard_mask         bool
          levels            int
        """
        thread = threading.Thread(target=self._run_process, args=(params,), daemon=True)
        thread.start()
        return True

    def _run_process(self, params: dict):
        tmp_dir = None
        try:
            input_paths = params["input_paths"]
            output_path = params["output_path"]

            _emit("process:start", {"total_images": len(input_paths)})

            tmp_dir = tempfile.mkdtemp(prefix="totally_enfused_")
            enfuse_inputs = input_paths

            # Convert RAW files to TIFF before alignment/blending
            has_raw = needs_raw_conversion(input_paths)
            align_start = 20 if has_raw else 0

            if has_raw:
                _emit("process:stage", {"stage": "convert", "message": "Converting RAW files…"})

                def raw_progress(pct, msg):
                    _emit("process:progress", {"pct": max(0, pct) * 0.2, "message": msg})

                enfuse_inputs = convert_raws_to_tiff(input_paths, tmp_dir, raw_progress)
                _emit("process:progress", {"pct": 20, "message": "RAW conversion done"})

            if params.get("align_enabled", True):
                _emit("process:stage", {"stage": "align", "message": "Aligning images…"})

                def align_progress(pct, msg):
                    _emit("process:progress", {
                        "pct": align_start + max(0, pct) * 0.4,
                        "message": msg,
                    })

                enfuse_inputs = align(
                    input_paths=enfuse_inputs,
                    output_dir=tmp_dir,
                    mode=params.get("align_mode", "translation_rotation"),
                    grid_points=params.get("align_grid_points", 8),
                    crop=params.get("align_crop", True),
                    progress_callback=align_progress,
                )

            blend_start = align_start + (40 if params.get("align_enabled") else 0)
            blend_scale = 100 - blend_start

            _emit("process:stage", {"stage": "blend", "message": "Blending images…"})

            def enfuse_progress(pct, msg):
                _emit("process:progress", {
                    "pct": blend_start + (max(0, pct) / 100 * blend_scale),
                    "message": msg,
                })

            result_path = blend(
                input_paths=enfuse_inputs,
                output_path=output_path,
                exposure_weight=params.get("exposure_weight", 1.0),
                saturation_weight=params.get("saturation_weight", 0.2),
                contrast_weight=params.get("contrast_weight", 0.0),
                hard_mask=params.get("hard_mask", False),
                levels=params.get("levels", 29),
                progress_callback=enfuse_progress,
            )

            _emit("process:progress", {"pct": 99, "message": "Copying metadata…"})
            icc_path = None
            if has_raw:
                icc_path = os.path.join(tmp_dir, "sRGB.icc")
                Path(icc_path).write_bytes(image_utils.srgb_icc_bytes())
            image_utils.copy_metadata(image_utils.reference_exposure(input_paths), result_path, icc_path)

            preview = image_utils.get_preview_b64(result_path)
            _emit("process:complete", {"output_path": result_path, "preview": preview})

        except Exception as e:
            _emit("process:error", {"message": str(e)})
        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def reveal_in_finder(self, path: str):
        import subprocess
        subprocess.Popen(["open", "-R", path])
        return True
