import { writable } from 'svelte/store'

const DEFAULTS = {
  output_format: 'tiff',
  output_quality: 95,
  output_dir_mode: 'same_as_input',
  output_dir: '',
  output_template: '{name}_enfused.{ext}',
  align_enabled: true,
  align_mode: 'translation_rotation',
  align_grid_points: 8,
  align_crop: true,
  fusion_exposure_weight: 1.0,
  fusion_saturation_weight: 0.2,
  fusion_contrast_weight: 0.0,
  fusion_hard_mask: false,
  fusion_levels: 29,
  fusion_exposure_optimum: 0.5,
  fusion_highlight_protect: 0,
  motion_enabled: false,
  motion_sensitivity: 0.5,
  last_preset: 'natural',
}

// Preset field -> settings field. Presets saved before a field existed get its default.
const PRESET_FIELDS = {
  exposure_weight: 'fusion_exposure_weight',
  saturation_weight: 'fusion_saturation_weight',
  contrast_weight: 'fusion_contrast_weight',
  hard_mask: 'fusion_hard_mask',
  levels: 'fusion_levels',
  exposure_optimum: 'fusion_exposure_optimum',
  highlight_protect: 'fusion_highlight_protect',
  motion_enabled: 'motion_enabled',
  motion_sensitivity: 'motion_sensitivity',
}

export const settings = writable({ ...DEFAULTS })

export async function loadSettings() {
  try {
    const saved = await window.pywebview?.api?.get_settings()
    if (saved) settings.set({ ...DEFAULTS, ...saved })
  } catch (e) {
    console.warn('Could not load settings', e)
  }
}

export async function saveSettings(data) {
  try {
    await window.pywebview?.api?.save_settings(data)
  } catch (e) {
    console.warn('Could not save settings', e)
  }
}

export function applyPreset(preset) {
  settings.update(s => {
    const next = { ...s }
    for (const [field, key] of Object.entries(PRESET_FIELDS)) next[key] = preset[field] ?? DEFAULTS[key]
    return next
  })
}

export function presetFromSettings(s) {
  return Object.fromEntries(Object.entries(PRESET_FIELDS).map(([field, key]) => [field, s[key]]))
}

// Output file for a set, named after its first frame
export function outputPathFor(firstPath, s) {
  if (!firstPath) return null
  const dir = s.output_dir_mode === 'custom' && s.output_dir
    ? s.output_dir
    : firstPath.substring(0, firstPath.lastIndexOf('/'))
  const baseName = firstPath.split('/').pop().replace(/\.[^.]+$/, '')
  const ext = s.output_format === 'jpeg' ? 'jpg'
    : s.output_format === 'tiff' ? 'tif'
    : s.output_format
  return `${dir}/${s.output_template.replace('{name}', baseName).replace('{ext}', ext)}`
}
