#!/bin/bash
# ============================================================
# Build native arm64 enfuse and align_image_stack from source and
# package them for the app (vendor/bundle, consumed by release.sh).
#
# There are no official Apple Silicon builds of Hugin or enblend-enfuse,
# so we build: vigra (static) + libpano13 + enfuse + align_image_stack,
# against Homebrew for the remaining libraries.
#
# Prerequisites (Homebrew):
#   brew install cmake pkgconf boost libtiff libpng jpeg-turbo little-cms2 \
#     exiv2 openexr fftw gsl sqlite wxwidgets glew lensfun libomp
# (wxwidgets/glew are only needed for Hugin's configure step.)
#
# Output: vendor/bundle/{Helpers,Frameworks/hugin-libs,licenses}
# The tools require macOS 27, the minimum of the Homebrew bottles they link.
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# autotools can't cope with the space in the project path; work via a symlink
mkdir -p "$ROOT/vendor" "$HOME/.cache"
ln -sfn "$ROOT/vendor" "$HOME/.cache/te-vendor"
V="$HOME/.cache/te-vendor"
SRC="$V/src" BLD="$V/build" PREFIX="$V/prefix" H=/opt/homebrew
export MACOSX_DEPLOYMENT_TARGET=27.0
JOBS=$(sysctl -n hw.ncpu)

HUGIN=hugin-2025.0.1
ENBLEND=enblend-enfuse-4.2
PANO=libpano13-2.9.22
VIGRA=vigra-Version-1-12-1

fetch() {  # url file
  [ -f "$SRC/$2" ] || curl -fsSL -o "$SRC/$2" "$1"
}

echo "==> Sources"
mkdir -p "$SRC" "$BLD" "$PREFIX/bin"
fetch "https://sourceforge.net/projects/hugin/files/hugin/hugin-2025.0/$HUGIN.tar.bz2/download" "$HUGIN.tar.bz2"
fetch "https://sourceforge.net/projects/enblend/files/enblend-enfuse/$ENBLEND/$ENBLEND.tar.gz/download" "$ENBLEND.tar.gz"
fetch "https://sourceforge.net/projects/panotools/files/libpano13/$PANO/$PANO.tar.gz/download" "$PANO.tar.gz"
fetch "https://github.com/ukoethe/vigra/archive/refs/tags/Version-1-12-1.tar.gz" "vigra-1.12.1.tar.gz"
for f in "$SRC"/*.tar.*; do
  d="$SRC/$(basename "$f" | sed -E 's/\.tar\.(gz|bz2)$//')"
  [ "$(basename "$f")" = "vigra-1.12.1.tar.gz" ] && d="$SRC/$VIGRA"
  [ -d "$d" ] || tar -xf "$f" -C "$SRC"
done

echo "==> Patches"
# vigra: '--this' is ill-formed; newer clang rejects it (fixed upstream)
sed -i '' 's/^        --this;$/        --(*this);/' "$SRC/$VIGRA/include/vigra/multi_iterator_coupled.hxx"
# hugin: pass multi-word OpenMP flags (Apple clang: -Xpreprocessor -fopenmp) as separate arguments
grep -q _hugin_omp_flags "$SRC/$HUGIN/CMakeLists.txt" || sed -i '' \
  's|^  ADD_COMPILE_OPTIONS(${OpenMP_CXX_FLAGS})$|  SEPARATE_ARGUMENTS(_hugin_omp_flags UNIX_COMMAND "${OpenMP_CXX_FLAGS}")\
  ADD_COMPILE_OPTIONS(${_hugin_omp_flags})|' "$SRC/$HUGIN/CMakeLists.txt"

OMP="-Xpreprocessor -fopenmp -I$H/opt/libomp/include"
LEGACY_CXX="-D_LIBCPP_ENABLE_CXX17_REMOVED_UNARY_BINARY_FUNCTION"  # std::unary_function in 2016-era code

echo "==> vigra (static)"
mkdir -p "$BLD/vigra" && cd "$BLD/vigra"
# BUILD_DOCS stays ON: OFF breaks the generate step (PACKAGE_SRC_TAR needs doc_cpp). Docs are never built.
cmake "$SRC/$VIGRA" -Wno-dev -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_PREFIX_PATH="$H" -DCMAKE_IGNORE_PREFIX_PATH=/opt/local \
  -DVIGRA_STATIC_LIB=ON -DWITH_VIGRANUMPY=OFF -DWITH_HDF5=OFF -DWITH_OPENEXR=ON \
  -DWITH_BOOST_GRAPH=OFF -DWITH_VALGRIND=OFF \
  -DBUILD_DOCS=ON >/dev/null
make -j"$JOBS" vigraimpex >/dev/null && cmake --install . >/dev/null

echo "==> libpano13"
mkdir -p "$BLD/pano13" && cd "$BLD/pano13"
cmake "$SRC/$PANO" -Wno-dev -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_PREFIX_PATH="$H" -DCMAKE_IGNORE_PREFIX_PATH=/opt/local \
  -DSUPPORT_JAVA_PROGRAMS=OFF -DBUILD_DOC=OFF >/dev/null
make -j"$JOBS" >/dev/null && cmake --install . >/dev/null

echo "==> enfuse"
mkdir -p "$BLD/enfuse" && cd "$BLD/enfuse"
# latex=no: configure.ac tests the wrong variable and aborts without LaTeX (docs only)
latex=no ax_cv_cxx_openmp="-Xpreprocessor -fopenmp" PKG_CONFIG_PATH="$H/lib/pkgconfig" \
CPPFLAGS="-I$PREFIX/include -I$H/include -I$H/include/OpenEXR -I$H/include/Imath -I$H/opt/libomp/include $LEGACY_CXX" \
LDFLAGS="-L$PREFIX/lib -L$H/lib -L$H/opt/libomp/lib" \
CXXFLAGS="-O2 -std=gnu++17" CFLAGS="-O2" \
LIBS="-lomp -lOpenEXR -lIex -lIlmThread -lImath -lfftw3 -lz" \
"$SRC/$ENBLEND/configure" --enable-openmp --with-boost="$H" --without-tcmalloc --with-openexr >/dev/null
# HELP2MAN=true: skip man pages (needs help2man); builds enblend too, which is unused
make -j"$JOBS" -C src HELP2MAN=true >/dev/null
cp src/enfuse "$PREFIX/bin/"

echo "==> align_image_stack"
mkdir -p "$BLD/hugin" && cd "$BLD/hugin"
cmake "$SRC/$HUGIN" -Wno-dev -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$PREFIX;$H" -DCMAKE_IGNORE_PREFIX_PATH=/opt/local \
  -DCMAKE_CXX_FLAGS="$LEGACY_CXX -Wno-register" \
  -DVIGRA_INCLUDE_DIR="$PREFIX/include" -DVIGRA_LIBRARIES="$PREFIX/lib/libvigraimpex.a" \
  -DPANO13_INCLUDE_DIR="$PREFIX/include" -DPANO13_LIBRARIES="$PREFIX/lib/libpano13.dylib" \
  -DwxWidgets_CONFIG_EXECUTABLE="$H/bin/wx-config" -DHUGIN_SHARED=OFF -DBUILD_HSI=OFF \
  -DOpenMP_CXX_FLAGS="$OMP" -DOpenMP_C_FLAGS="$OMP" \
  -DCMAKE_EXE_LINKER_FLAGS="-L$H/opt/libomp/lib -lomp" \
  -DCMAKE_SHARED_LINKER_FLAGS="-L$H/opt/libomp/lib -lomp" >/dev/null
make -j"$JOBS" align_image_stack >/dev/null
cp src/tools/align_image_stack "$PREFIX/bin/"

echo "==> Bundle"
"$ROOT/.venv/bin/python" "$ROOT/build/bundle_hugin_tools.py" "$PREFIX" "$ROOT/vendor/bundle"
L="$ROOT/vendor/bundle/licenses"
mkdir -p "$L/hugin" "$L/enblend-enfuse" "$L/libpano13" "$L/vigra"
cp "$SRC/$HUGIN/COPYING.txt" "$L/hugin/" 2>/dev/null || cp "$SRC/$HUGIN"/COPYING* "$L/hugin/"
cp "$SRC/$ENBLEND/COPYING" "$L/enblend-enfuse/"
cp "$SRC/$PANO/COPYING" "$L/libpano13/"
cp "$SRC/$VIGRA/LICENSE.txt" "$L/vigra/"
cp "$ROOT/build/THIRD_PARTY_NOTICES.md" "$L/"

"$ROOT/vendor/bundle/Helpers/enfuse" --version | head -1
"$ROOT/vendor/bundle/Helpers/align_image_stack" 2>&1 | head -1 || true
echo "✓ vendor/bundle ready"
