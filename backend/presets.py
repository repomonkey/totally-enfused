import json
from pathlib import Path

PRESETS_PATH = Path.home() / ".totally_enfused" / "presets.json"

BUILTIN_PRESETS = {
    "natural": {
        "name": "Natural",
        "description": "Balanced weights for landscape and general use",
        "exposure_weight": 1.0,
        "saturation_weight": 0.2,
        "contrast_weight": 0.0,
        "hard_mask": False,
        "levels": 29,
        "exposure_optimum": 0.5,
        "highlight_protect": 0,
        "motion_enabled": False,
        "motion_sensitivity": 0.5,
        "builtin": True,
    },
    "real_estate": {
        "name": "Real Estate",
        "description": "Optimised for interior and architecture brackets",
        "exposure_weight": 1.0,
        "saturation_weight": 0.1,
        "contrast_weight": 0.0,
        "hard_mask": True,
        "levels": 29,
        "exposure_optimum": 0.5,
        "highlight_protect": 0,
        "motion_enabled": False,
        "motion_sensitivity": 0.5,
        "builtin": True,
    },
    "macro": {
        "name": "Macro / Focus Stack",
        "description": "Focus stacking-friendly (contrast-weighted blend)",
        "exposure_weight": 0.0,
        "saturation_weight": 0.0,
        "contrast_weight": 1.0,
        "hard_mask": True,
        "levels": 29,
        "exposure_optimum": 0.5,
        "highlight_protect": 0,
        "motion_enabled": False,
        "motion_sensitivity": 0.5,
        "builtin": True,
    },
    "seascape": {
        "name": "Seascape / Moving Water",
        "description": "Sharp waves and clouds from one frame, protected highlights",
        "exposure_weight": 1.0,
        "saturation_weight": 0.3,
        "contrast_weight": 0.0,
        "hard_mask": False,
        "levels": 29,
        "exposure_optimum": 0.5,
        "highlight_protect": 5,
        "motion_enabled": True,
        "motion_sensitivity": 0.5,
        "builtin": True,
    },
    "vivid": {
        "name": "Vivid",
        "description": "Boosted saturation for dramatic skies",
        "exposure_weight": 1.0,
        "saturation_weight": 0.6,
        "contrast_weight": 0.1,
        "hard_mask": False,
        "levels": 29,
        "exposure_optimum": 0.5,
        "highlight_protect": 0,
        "motion_enabled": False,
        "motion_sensitivity": 0.5,
        "builtin": True,
    },
}


def load_all():
    presets = dict(BUILTIN_PRESETS)
    if PRESETS_PATH.exists():
        try:
            with open(PRESETS_PATH) as f:
                custom = json.load(f)
            presets.update(custom)
        except Exception:
            pass
    return presets


def save_custom(key: str, preset: dict):
    presets = {}
    if PRESETS_PATH.exists():
        try:
            with open(PRESETS_PATH) as f:
                presets = json.load(f)
        except Exception:
            pass
    presets[key] = {**preset, "builtin": False}
    PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PRESETS_PATH, "w") as f:
        json.dump(presets, f, indent=2)


def delete_custom(key: str):
    if not PRESETS_PATH.exists():
        return
    with open(PRESETS_PATH) as f:
        presets = json.load(f)
    presets.pop(key, None)
    with open(PRESETS_PATH, "w") as f:
        json.dump(presets, f, indent=2)
