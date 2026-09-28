# Kakashi

**Copy Motion. Create Anything.**

A local creator tool that turns a demonstrated two-part hinge or slider into a reusable control. Select two textured parts, teach their relative movement, confirm the proposed joint, then perform with original dragon wings, an opening flower, a mechanical claw, or your own manually rigged drawing.

This is a working **development prototype**, not a fully validated Snapdragon release. Real-camera/held-out-prop robustness and NPU performance are outstanding. The classical CPU backend is the default; learned XFeat perception is functional but experimental. Read [status](docs/status.md) and [benchmarks](docs/benchmark.md) for the actual evidence.

## Run

Requires Python **3.11 or 3.12**, a modern browser and, for live input, a webcam. No Node installation is needed to run the bundled interface. First setup needs Internet access to install pinned dependencies; subsequent use is local and offline.

**Windows x64:** extract the entire archive and double-click `Launch-Kakashi.cmd`. If Python isn't installed or the launcher cannot select the right version, use the commands below. On a Snapdragon PC use the explicit x64 CPU baseline and optional native NPU worker in [docs/snapdragon.md](docs/snapdragon.md).

**macOS / Linux:** from the `kakashi` folder:

```bash
bash launch.sh
```

Or set up manually:

```bash
python3 -m venv .venv
# Windows: .venv\Scripts\python.exe -m pip install -r requirements.txt
.venv/bin/python -m pip install -r requirements.txt
# Windows: .venv\Scripts\python.exe run.py
.venv/bin/python run.py
```

Kakashi opens `http://127.0.0.1:8765`. Keep the local process running while using the app. If the browser doesn't open, visit that address. `python run.py --no-browser --port 8765` is available for development. Only Linux x86_64 was executed here; macOS/Windows setup follows the portable dependency path but is not device-tested.

## First controller

1. Connect a camera or try a clearly labelled **recorded synthetic example**. Use fixed camera placement and diffuse light.
2. Click **Select parts**. Draw one box inside each textured rigid part. Use **Redraw** if a box contains fingers/background or crosses the joint. Confirm the boxes.
3. Click **Start learning**. Move the joint through a clear range for 3–8 seconds. Keep motion roughly parallel to the image plane. Click **Finish demonstration**.
4. Confirm the proposed hinge/slider, or open **Correct the joint** to provide a manual pivot/axis. Stationary or ambiguous movement is rejected.
5. Click a creation to bind the control. Tune sensitivity, inversion, dead zone and smoothing. **Learn again** recalibrates the observed range.
6. Record, replay, and save a session. Session JSON includes one reference camera image. Open that file after starting the desired input to restore it. Reacquisition requires the same textured faces and similar camera geometry.

The main workflow uses no terminal or chat box. Diagnostics are collapsed until needed. A frozen selection, recorded video and recorded-control replay have distinct labels. The control holds on loss rather than inventing movement.

## Capabilities

- One RGB camera, two approximately rigid textured parts, one planar hinge or slider.
- Relative transforms cancel common planar translation/rotation; robust fitting proposes geometry and observed travel.
- Three original editable SVG rigs; direct click binding and control-card drag/drop.
- Drawing editor: draw/import two raster parts, position a pivot or slide axis manually, bind the existing control.
- Recording/replay, session export/import, browser-local backup, explicit tracking-loss/recovery states.
- ORB/LK CPU baseline; actual XFeat ONNX CPU inference; printed ArUco marker baseline in `assets/marker-0.png` and `assets/marker-1.png`.
- QDQ candidate and strict QNN boundary with profiling helpers. **NPU execution is unverified.**

“Anything” is the ambition in the tagline. This release does not recognize arbitrary mechanisms, reconstruct 3D objects, automatically rig arbitrary characters, or synthesize full-body motion.

## Develop and verify

Use the same Python environment as above. Node 20.19+ is needed only to edit/build the interface. Node 22+ is recommended for the browser-check scripts.

```bash
source .venv/bin/activate  # PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
npm ci
npm run build
python -m pytest
npm test

# Test the complete interface with actual decoded fixture pixels:
npx playwright install chromium
KAKASHI_PYTHON=.venv/bin/python node scripts/ui_smoke.mjs

# Reproduce benchmarks (synthetic development fixtures):
python scripts/benchmark.py --backends orb xfeat marker xfeat-qdq --include-manual
```

On PowerShell set `$env:KAKASHI_PYTHON = '.venv\Scripts\python.exe'` before `node scripts/ui_smoke.mjs`. Do not run a separate server on the same port when using the smoke scripts. `scripts/camera_smoke.mjs` also needs ffmpeg; it uses Chromium's fake camera and is explicitly **not real-camera evidence**. `npm run dev` serves the interface with a proxy to the local backend for editing.

Bundled fixtures include H.264 MP4 for offline OpenCV evaluation and VP9 WebM for broad browser decoding. Regenerate them with `python scripts/make_fixtures.py` (ffmpeg required). Their ground-truth JSON is used only by tests/benchmarks, never by the live or recorded-input frontend. The original drawing/rig code is in `src/Rigs.tsx` and `src/DrawingEditor.tsx`.

## Documentation

- [Status and outstanding milestones](docs/status.md)
- [Measured development benchmarks](docs/benchmark.md)
- [Architecture, coordinates and operating envelope](docs/architecture.md)
- [Reference methods, attribution and hypothesis](docs/references.md)
- [Windows/Snapdragon setup and placement verification](docs/snapdragon.md)
- [Held-out physical evaluation protocol](docs/held-out-protocol.md)
- [Two-minute demo and honest recovery](docs/demo-script.md)

`reports/` contains the test and benchmark evidence. `models/manifest.json` records the immutable XFeat revision, hashes and ONNX export checks. The original project assets/code are separate from the Apache-2.0 XFeat component; see `THIRD_PARTY.md` and retained notices. No AniCraft, DancingBox, TopoCap or anime character assets are included. Nothing has been published or submitted.
