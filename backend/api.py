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
from . import batch as batch_mod
from . import deghost

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
        Run the pipeline on one set in a background thread; progress is pushed
        as process:* events. params: input_paths, output_path, plus the shared
        settings read by _pipeline_settings().
        """
        _start_job(_run_single, params)
        return True

    def scan_batch(self, paths: list, frames_per_set=None):
        """Expand folders and group files into bracket sets (see backend/batch.py)."""
        return batch_mod.scan(paths, size=int(frames_per_set) if frames_per_set else None)

    def process_batch(self, params: dict):
        """
        Run several sets in sequence in a background thread; progress is pushed
        as batch:* events. params: sets [{paths, output_path}], plus shared settings.
        """
        _start_job(_run_batch, params)
        return True

    def cancel(self):
        """Stop the running job, killing the current align/enfuse process."""
        _cancel.set()
        with _proc_lock:
            if _current_proc and _current_proc.poll() is None:
                _current_proc.terminate()
        return True

    def reveal_in_finder(self, path: str):
        import subprocess
        subprocess.Popen(["open", "-R", path])
        return True


# ---------------------------------------------------------------------- #
# Pipeline
# ---------------------------------------------------------------------- #

class Cancelled(Exception):
    pass


_cancel = threading.Event()
_proc_lock = threading.Lock()
_current_proc = None
_job_lock = threading.Lock()  # one job at a time


def _start_job(target, params):
    if not _job_lock.acquire(blocking=False):
        raise RuntimeError("A job is already running")

    def run():
        try:
            target(params)
        finally:
            _job_lock.release()

    _cancel.clear()
    threading.Thread(target=run, daemon=True).start()


def _track(proc):
    global _current_proc
    with _proc_lock:
        _current_proc = proc
    if _cancel.is_set():
        proc.terminate()


def _check_cancel():
    if _cancel.is_set():
        raise Cancelled()


def _pipeline_settings(params: dict) -> dict:
    return {
        "align_enabled": params.get("align_enabled", True),
        "align_mode": params.get("align_mode", "translation_rotation"),
        "align_grid_points": params.get("align_grid_points", 8),
        "align_crop": params.get("align_crop", True),
        "blend": dict(
            exposure_weight=params.get("exposure_weight", 1.0),
            saturation_weight=params.get("saturation_weight", 0.2),
            contrast_weight=params.get("contrast_weight", 0.0),
            hard_mask=params.get("hard_mask", False),
            levels=params.get("levels", 29),
            jpeg_quality=params.get("jpeg_quality", 85),
            exposure_optimum=params.get("exposure_optimum", 0.5),
            highlight_protect=params.get("highlight_protect", 0.0),
        ),
        "motion_enabled": params.get("motion_enabled", False),
        "motion_sensitivity": params.get("motion_sensitivity", 0.5),
        # Index into input_paths; None = the frame nearest 0 EV
        "reference_index": params.get("reference_index"),
    }


def unique_path(path: str) -> str:
    """path, or path with _01, _02… before the extension if it already exists."""
    p = Path(path)
    if not p.exists():
        return path
    for n in range(1, 1000):
        candidate = p.with_name(f"{p.stem}_{n:02d}{p.suffix}")
        if not candidate.exists():
            return str(candidate)
    raise RuntimeError(f"Too many existing outputs named {p.name}")


def run_pipeline(input_paths: list[str], output_path: str, cfg: dict, report) -> str:
    """
    RAW conversion → alignment → motion masks (optional) → enfuse → metadata, for one set.
    report(stage, pct, message): stage is a name when a stage starts, else None;
    pct is 0–100 within this set, or -1 for message-only updates.
    """
    output_path = unique_path(output_path)   # never overwrite an earlier result
    tmp_dir = tempfile.mkdtemp(prefix="totally_enfused_")
    try:
        enfuse_inputs = input_paths
        has_raw = needs_raw_conversion(input_paths)
        align_start = 20 if has_raw else 0

        if has_raw:
            report("convert", 0, "Converting RAW files…")
            enfuse_inputs = convert_raws_to_tiff(
                input_paths, tmp_dir,
                lambda pct, msg: (_check_cancel(), report(None, max(0, pct) * 0.2, msg)))
            report(None, 20, "RAW conversion done")
        _check_cancel()

        if cfg["align_enabled"]:
            report("align", align_start, "Aligning images…")
            enfuse_inputs = align(
                input_paths=enfuse_inputs,
                output_dir=tmp_dir,
                mode=cfg["align_mode"],
                grid_points=cfg["align_grid_points"],
                crop=cfg["align_crop"],
                progress_callback=lambda pct, msg: report(
                    None, align_start + max(0, pct) * 0.4 if pct >= 0 else -1, msg),
                on_process=_track,
            )
        _check_cancel()

        if cfg["motion_enabled"]:
            ref = cfg["reference_index"]
            if ref is None or not 0 <= ref < len(input_paths):
                ref = input_paths.index(image_utils.reference_exposure(input_paths))
            report("motion", -1, f"Finding movement (reference: {Path(input_paths[ref]).name})…")
            enfuse_inputs, moving = deghost.apply(enfuse_inputs, ref, cfg["motion_sensitivity"], tmp_dir)
            if moving > deghost.MAX_MOVING:
                report(None, -1, "Motion handling skipped: the frames differ almost everywhere (check alignment)")
            else:
                report(None, -1, f"Moving areas from {Path(input_paths[ref]).name}: {moving:.0%} of the image")
        _check_cancel()

        blend_start = align_start + (40 if cfg["align_enabled"] else 0)
        blend_scale = 100 - blend_start
        report("blend", blend_start, "Blending images…")
        result_path = blend(
            input_paths=enfuse_inputs,
            output_path=output_path,
            progress_callback=lambda pct, msg: report(
                None, blend_start + max(0, pct) / 100 * blend_scale if pct >= 0 else -1, msg),
            on_process=_track,
            **cfg["blend"],
        )
        _check_cancel()

        report(None, 99, "Copying metadata…")
        icc_path = None
        if has_raw:
            icc_path = os.path.join(tmp_dir, "sRGB.icc")
            Path(icc_path).write_bytes(image_utils.srgb_icc_bytes())
        image_utils.copy_metadata(image_utils.reference_exposure(input_paths), result_path, icc_path)
        return result_path

    except RuntimeError:
        if _cancel.is_set():  # the runner failed because we killed its process
            raise Cancelled() from None
        raise
    except Cancelled:
        raise
    finally:
        if _cancel.is_set() and os.path.exists(output_path):
            os.remove(output_path)  # partial output from an interrupted enfuse
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_single(params: dict):
    def report(stage, pct, msg):
        if stage:
            _emit("process:stage", {"stage": stage, "message": msg})
        _emit("process:progress", {"pct": pct, "message": msg})

    try:
        _emit("process:start", {"total_images": len(params["input_paths"])})
        result = run_pipeline(params["input_paths"], params["output_path"],
                              _pipeline_settings(params), report)
        _emit("process:complete", {"output_path": result,
                                   "preview": image_utils.get_preview_b64(result)})
    except Cancelled:
        _emit("process:cancelled", {})
    except Exception as e:
        _emit("process:error", {"message": str(e)})


def _run_batch(params: dict):
    sets = params["sets"]
    cfg = _pipeline_settings(params)
    done = failed = 0
    _emit("batch:start", {"total": len(sets)})
    for i, job in enumerate(sets):
        if _cancel.is_set():
            break
        _emit("batch:set_start", {"index": i})

        def report(stage, pct, msg, i=i):
            _emit("batch:set_progress", {"index": i, "pct": pct, "message": msg})

        try:
            result = run_pipeline(job["paths"], job["output_path"], cfg, report)
            done += 1
            _emit("batch:set_done", {"index": i, "output_path": result,
                                     "thumbnail": image_utils.get_thumbnail_b64(result)})
        except Cancelled:
            break
        except Exception as e:
            failed += 1
            _emit("batch:set_error", {"index": i, "message": str(e)})
    _emit("batch:complete", {"done": done, "failed": failed, "cancelled": _cancel.is_set()})
