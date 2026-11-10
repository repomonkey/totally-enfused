#!/usr/bin/env python3
"""
Package ExifTool (pure Perl) for the app, from the Homebrew install.

Output: <out>/exiftool/{exiftool, lib/Image, lib/File}
        <out>/licenses/exiftool-<version>/README

Homebrew rewrites the script's library lookup to absolute Cellar paths; this
restores upstream's `unshift @INC, $incDir` so it finds lib/ next to itself,
and runs it with macOS's /usr/bin/perl.

Usage: bundle_exiftool.py <out-dir>
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path


def main(out: Path):
    prefix = Path(subprocess.run(["brew", "--prefix", "exiftool"], capture_output=True,
                                 text=True, check=True).stdout.strip()).resolve()
    version = prefix.name
    lib = prefix / "libexec" / "lib" / "perl5"

    dest = out / "exiftool"
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "lib").mkdir(parents=True)
    for d in ("Image", "File"):  # ExifTool itself; the rest of libexec is optional extras
        shutil.copytree(lib / d, dest / "lib" / d)

    script = (prefix / "bin" / "exiftool").read_text()
    script, n = re.subn(
        r'unshift @INC, "[^"]*/libexec/lib/perl5";\nunshift @INC, "[^"]*\$Config\{archname\}";\n',
        "    unshift @INC, $incDir;\n", script)
    if n != 1:
        sys.exit("Homebrew's exiftool script changed shape; update bundle_exiftool.py")
    script = re.sub(r"\A#!\S+", "#!/usr/bin/perl", script)
    (dest / "exiftool").write_text(script)
    (dest / "exiftool").chmod(0o755)

    lic = out / "licenses" / f"exiftool-{version}"
    lic.mkdir(parents=True, exist_ok=True)
    shutil.copy2(prefix / "README", lic / "README")

    ver = subprocess.run(["/usr/bin/perl", str(dest / "exiftool"), "-ver"], capture_output=True,
                         text=True, check=True, env={"PATH": "/usr/bin:/bin"}).stdout.strip()
    size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    print(f"bundled exiftool {ver}, {size / 1e6:.1f} MB -> {dest}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
