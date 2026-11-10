# Third-party software in Totally Enfused

Totally Enfused is MIT-licensed. It ships two command-line programs from other projects, `enfuse` and `align_image_stack`, as separate executables in `Contents/Helpers`, with the libraries they need in `Contents/Frameworks/hugin-libs`. It also ships ExifTool, a Perl program, in `Contents/Resources/exiftool`. The app runs them as independent processes and does not link against them. Each program keeps its own licence, and the full licence texts are in `Contents/Resources/ThirdParty/`, one folder per component.

## Programs

| Program | Project | Version | Licence | Source |
|---|---|---|---|---|
| `enfuse` | enblend-enfuse | 4.2 | GPL-2.0-or-later | https://sourceforge.net/projects/enblend/files/enblend-enfuse/enblend-enfuse-4.2/ |
| `align_image_stack` | Hugin | 2025.0.1 | GPL-2.0-or-later | https://sourceforge.net/projects/hugin/files/hugin/hugin-2025.0/ |
| `exiftool` | ExifTool by Phil Harvey | 13.55 | Same terms as Perl (Artistic License or GPL-1.0-or-later) | https://exiftool.org/ |

ExifTool is copied from its Homebrew package, keeping only its own modules (`Image::ExifTool` and `File::RandomAccess`). One line is changed: Homebrew's absolute library path is replaced with upstream's `unshift @INC, $incDir`, so the script finds its modules next to itself. The script runs with macOS's `/usr/bin/perl`. See `build/bundle_exiftool.py`.

`enfuse` and `align_image_stack` were built from the unmodified release archives above, with two build-only changes:

- **Hugin**: one line of `CMakeLists.txt` splits the OpenMP compiler flags into separate arguments (`SEPARATE_ARGUMENTS`) so Apple clang accepts them.
- **vigra**: `--this` is corrected to `--(*this)` in `include/vigra/multi_iterator_coupled.hxx`. The upstream project carries the same fix.

Neither change alters image processing. Every step, flag and patch is in `build/build_hugin_tools.sh` in the Totally Enfused source. On request, the complete corresponding source for these binaries will be provided for at least three years from the date of each release, as GPL section 3(b) requires.

## Libraries

Built from source and linked into the programs:

| Library | Version | Licence | Source |
|---|---|---|---|
| vigra (static, in both programs) | 1.12.1 | MIT | https://github.com/ukoethe/vigra |
| libpano13 | 2.9.22 | GPL-2.0-or-later | https://sourceforge.net/projects/panotools/ |

Taken from Homebrew, unmodified apart from load paths and code signatures:
Boost headers; brotli, exiv2, fftw, gettext (libintl), GLEW, GSL, Imath, inih, jpeg-turbo, libdeflate, libomp, libpng, libtiff, Little CMS, OpenEXR, OpenJPH, WebP, xz (liblzma) and zstd. Each one's version and licence text is in `ThirdParty/<name>-<version>/`. GSL is GPL-3.0, so the `enfuse` binary as distributed is covered by GPL-3.0, which enblend-enfuse's "or later" licence permits.
