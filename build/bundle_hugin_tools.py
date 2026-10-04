#!/usr/bin/env python3
"""
Make the self-built enfuse and align_image_stack relocatable.

Copies the tools and every non-system dylib they depend on into OUT:
    OUT/Helpers/{enfuse,align_image_stack}
    OUT/Frameworks/hugin-libs/*.dylib
    OUT/licenses/<formula>-<version>/   (licence files of the Homebrew libraries)
and rewrites load paths to @rpath (executables: @executable_path/../Frameworks/hugin-libs,
dylibs: @loader_path), matching the layout inside Totally Enfused.app/Contents.
Everything is ad-hoc signed so it runs locally; release.sh re-signs with Developer ID.

Usage: bundle_hugin_tools.py <prefix-with-bin-and-lib> <out-dir>
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = ["enfuse", "align_image_stack"]
LIB_DIR = "Frameworks/hugin-libs"
SYSTEM = ("/usr/lib/", "/System/")


def deps(path: Path) -> list[str]:
    out = subprocess.run(["otool", "-L", str(path)], capture_output=True, text=True, check=True).stdout
    lines = out.splitlines()[1:]
    return [m.group(1) for l in lines if (m := re.match(r"\s+(\S.*?) \(compatibility", l))]


def rpaths(path: Path) -> list[str]:
    out = subprocess.run(["otool", "-l", str(path)], capture_output=True, text=True, check=True).stdout
    return re.findall(r"cmd LC_RPATH\n\s+cmdsize \d+\n\s+path (.+?) \(offset", out)


def resolve(ref: str, referrer: Path, prefix: Path) -> Path:
    if ref.startswith("@rpath/"):
        name = ref[len("@rpath/"):]
        for rp in rpaths(referrer) + [str(prefix / "lib")]:
            rp = rp.replace("@loader_path", str(referrer.parent)).replace("@executable_path", str(referrer.parent))
            if (Path(rp) / name).exists():
                return (Path(rp) / name).resolve()
        raise FileNotFoundError(f"{ref} (from {referrer})")
    if ref.startswith("@loader_path/"):
        return (referrer.parent / ref[len("@loader_path/"):]).resolve()
    return Path(ref).resolve()


def main(prefix: Path, out: Path):
    helpers, libs = out / "Helpers", out / LIB_DIR
    if out.exists():
        shutil.rmtree(out)
    helpers.mkdir(parents=True)
    libs.mkdir(parents=True)

    # Walk the dependency graph from the tools
    queue = [(prefix / "bin" / t).resolve() for t in TOOLS]
    seen: dict[Path, str] = {}            # source path -> bundled file name
    refs: dict[Path, list[tuple[str, Path]]] = {}
    while queue:
        src = queue.pop()
        if src in refs:
            continue
        refs[src] = []
        for ref in deps(src):
            if ref.startswith(SYSTEM):
                continue
            dep = resolve(ref, src, prefix)
            if dep == src:                # a dylib's own install name
                continue
            refs[src].append((ref, dep))
            if dep not in seen:
                seen[dep] = Path(ref).name if not ref.startswith("@") else dep.name
                queue.append(dep)

    names = list(seen.values())
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        sys.exit(f"dylib name collision: {dupes}")

    # Copy and rewrite
    for src in refs:
        is_tool = src.name in TOOLS and src.parent == (prefix / "bin").resolve()
        dst = helpers / src.name if is_tool else libs / seen[src]
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)
        cmd = ["install_name_tool"]
        if not is_tool:
            cmd += ["-id", f"@rpath/{dst.name}"]
        for ref, dep in refs[src]:
            cmd += ["-change", ref, f"@rpath/{seen[dep]}"]
        want = "@executable_path/../" + LIB_DIR if is_tool else "@loader_path"
        existing = rpaths(src)
        for rp in existing:
            if rp != want:
                cmd += ["-delete_rpath", rp]
        if want not in existing:
            cmd += ["-add_rpath", want]
        subprocess.run(cmd + [str(dst)], check=True, capture_output=True)

    # install_name_tool invalidates signatures; ad-hoc sign so the tools run locally
    for f in list(libs.iterdir()) + list(helpers.iterdir()):
        subprocess.run(["codesign", "--force", "--sign", "-", str(f)], check=True, capture_output=True)

    # Nothing may still point outside the bundle
    for f in list(libs.iterdir()) + list(helpers.iterdir()):
        bad = [d for d in deps(f) if not d.startswith(SYSTEM + ("@rpath/",))]
        if bad:
            sys.exit(f"{f.name} still references {bad}")

    # Licence files for every Homebrew library bundled (Cellar/<formula>/<version>/)
    lic_dir = out / "licenses"
    for src in seen:
        parts = src.parts
        if "Cellar" in parts:
            i = parts.index("Cellar")
            keg = Path(*parts[: i + 3])
            dest = lic_dir / f"{parts[i + 1]}-{parts[i + 2]}"
            for f in keg.iterdir():
                if f.is_file() and f.name.upper().startswith(("LICENSE", "COPYING", "NOTICE", "COPYRIGHT")):
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest / f.name)

    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"bundled {len(TOOLS)} tools + {len(seen)} dylibs, {size / 1e6:.1f} MB -> {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
