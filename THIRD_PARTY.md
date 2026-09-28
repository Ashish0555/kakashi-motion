# Attribution and component notices

Kakashi's interface, controller/state code, test fixtures and dragon/flower/claw/drawing assets were created for this project. No anime screenshots, franchise character assets, Mixamo assets, or figures/assets from the reference papers are bundled.

## XFeat (reused implementation and pretrained weights)

Guilherme Potje, Felipe Cadar, Andre Araujo, Renato Martins, Erickson R. Nascimento. **XFeat: Accelerated Features for Lightweight Image Matching**, CVPR 2024, pp. 2682–2691. DOI: 10.1109/CVPR52733.2024.00259.

Official source: https://github.com/verlab/accelerated_features

Pinned revision: `e92685f57f8318b18725c5c8c0bd28c7fe188d9a`.

The official `modules/model.py` and `weights/xfeat.pt` are retained in `models/source/`; the repository's **Apache License 2.0** is retained as `models/source/LICENSE`. The included ONNX model is derived from those weights and architecture. Kakashi's exporter replaces InstanceNorm with equivalent CPU preprocessing and removes unused graph branches through export. Neural weights are not retrained. Sparse postprocessing, tracking and geometric refinement are implemented in Kakashi; no LighterGlue or fine matcher is used at runtime. The QDQ candidate is separately quantized and labelled experimental.

`models/manifest.json` records source/weight/ONNX hashes, version, preprocessing, operator inventory, export numerical parity and placement status. `models/xfeat.qdq.onnx.json` records calibration sources and QDQ numerical checks. These are implementation/model notices, not assumptions based on the paper's publication license.

## Runtime libraries

| Component | License / retained notice |
|---|---|
| React / React DOM | MIT, retained under `licenses/` |
| Lucide icons | ISC, retained under `licenses/` |
| NumPy | BSD license and bundled dependency notices in `licenses/` |
| SciPy | BSD license and bundled dependency notices in `licenses/` |
| OpenCV / opencv-contrib-python-headless | Apache-2.0 core plus bundled third-party notices in `licenses/` |
| ONNX Runtime | MIT plus third-party notices in `licenses/` |
| FastAPI, Pydantic | MIT, see retained distribution notices |
| Uvicorn, Starlette, websockets | BSD licenses, see retained distribution notices |

Package metadata and installed versions are in `licenses/components.json`; pinned top-level dependencies are in `requirements.txt` and the npm lockfile. The development environment's full Python resolution is in `requirements-dev-lock.txt`. Build/test tools are installed separately and retain their upstream licenses. They are not copied wholesale into the distribution.

ArUco marker images are generated using OpenCV's DICT_4X4_50 dictionary. The illustrative mechanism fixtures and all rig artwork are original procedural assets. MP4/WebM examples are generated using the external ffmpeg executable; ffmpeg itself is not bundled.

AniCraft, DancingBox and TopoCap are credited as prior work in `docs/references.md`. No implementation, model or asset from those projects is reused. In particular, DancingBox's CC BY-NC-ND notice was not treated as a permissive software license.
