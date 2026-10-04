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
  last_preset: 'natural',
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
  settings.update(s => ({
    ...s,
    fusion_exposure_weight: preset.exposure_weight,
    fusion_saturation_weight: preset.saturation_weight,
    fusion_contrast_weight: preset.contrast_weight,
    fusion_hard_mask: preset.hard_mask,
    fusion_levels: preset.levels,
  }))
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
