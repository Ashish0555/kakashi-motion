"""Package runnable sources, the built UI, models, fixtures and measured evidence.

Run after `npm run build` and verification:
    python scripts/package_release.py --output ../Kakashi_Studio.zip

Virtual environments, node_modules and intermediate experiments are excluded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ("assets", "backend", "dist", "docs", "fixtures", "licenses",
               "models", "scripts", "src", "tests")
ROOT_FILES = ("README.md", "THIRD_PARTY.md", "Launch-Kakashi.cmd", "launch.sh",
              "run.py", "requirements.txt", "requirements-dev.txt",
              "requirements-dev-lock.txt", "requirements-qnn-worker.txt",
              "package.json", "package-lock.json", "pyproject.toml",
              "tsconfig.json", "vite.config.ts", "index.html", ".gitignore")
REPORTS = ("baseline.json", "browser-diagnostics.json", "ui-smoke.json",
           "camera-smoke.json", "test-session.json", "evaluation-smoke.json",
           "evaluation-smoke.csv", "verification.json", "studio-empty.png",
           "studio-performing.png", "studio-mobile.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT.parent / "Kakashi_Studio.zip"))
    args = parser.parse_args()
    paths = [ROOT / name for name in ROOT_FILES]
    paths += [ROOT / "reports" / name for name in REPORTS]
    for directory in (*DIRECTORIES, "reports/worker-cpu"):
        paths.extend(p for p in (ROOT / directory).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts
                     and p.suffix not in (".pyc", ".tsbuildinfo"))
    if not (ROOT / "dist/index.html").is_file():
        raise SystemExit("Build the interface with npm run build before packaging.")
    files = {}
    for path in sorted(set(paths)):
        if not path.is_file():
            raise SystemExit(f"Missing required release artifact: {path.relative_to(ROOT)}")
        relative = path.relative_to(ROOT).as_posix()
        files[relative] = {"bytes": path.stat().st_size,
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {
        "application": "Kakashi", "version": "0.1.0", "date": "2026-09-28",
        "scope": "CPU development prototype; real-prop and Snapdragon validation pending",
        "files": files,
        "note": "Manifest covers all bundled files except itself; no virtual environment is bundled."
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in files:
            archive.write(ROOT / relative, f"kakashi/{relative}")
        archive.writestr("kakashi/release-manifest.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise SystemExit("Archive integrity check failed.")
    print(json.dumps({"archive": str(output), "files": len(files) + 1,
                      "bytes": output.stat().st_size,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
