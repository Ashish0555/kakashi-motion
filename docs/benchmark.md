# Development benchmarks — 28 September 2026

## Scope and decision

These are **synthetic development results on Linux x86_64**, not held-out physical-prop results or Snapdragon results. The default remains classical ORB/LK. FP32 XFeat reduces refresh-frame processing cost and improves slider error in these fixtures, but loses tracking more often after occlusion. Its overall usability advantage has not been demonstrated.

The quantized XFeat QDQ candidate **failed the clean hinge fit**. The fitter rejected its approximately 4.0 px hinge residual rather than relaxing the acceptance threshold. It is included for reproducible investigation, not as a qualified NPU model. Its successful slider and occlusion rows must not hide this failure.

## Pixel-to-control comparison

Source: `reports/baseline.json`. Environment: Linux 6.18.44 x86_64, Python 3.12.14, OpenCV 4.11.0, ONNX Runtime CPU 1.22.1. This shared container has no fixed target CPU allocation; these single-run timings are development measurements, not a hardware ranking. Dependencies and model hashes are bundled.

| Backend | Fixture | Processing p50 / p95 (ms) | Raw MAE (0–1) | Raw error p95 (0–1) | Visible tracking loss | Unavailable after learning |
|---|---|---:|---:|---:|---:|---:|
| ORB/LK | hinge | 5.7 / 45.1 | 0.0034 | 0.0110 | 0.0% | 0.0% |
| ORB/LK | slider | 6.1 / 46.1 | 0.0095 | 0.0219 | 0.0% | 0.0% |
| ORB/LK | occlusion | 5.6 / 48.8 | 0.0045 | 0.0116 | 1.5% | 12.7% |
| XFeat FP32/LK | hinge | 5.6 / 25.0 | 0.0060 | 0.0138 | 0.0% | 0.0% |
| XFeat FP32/LK | slider | 5.5 / 23.4 | 0.0032 | 0.0090 | 0.0% | 0.0% |
| XFeat FP32/LK | occlusion | 5.3 / 22.6 | 0.0052 | 0.0134 | 9.2% | 27.9% |
| ArUco | marker | 3.2 / 3.7 | 0.0067 | 0.0154 | 0.0% | 0.0% |
| XFeat QDQ/LK | hinge | **Fit rejected** | — | — | — | — |
| XFeat QDQ/LK | slider | 6.5 / 24.8 | 0.0032 | 0.0072 | 0.0% | 0.0% |
| XFeat QDQ/LK | occlusion | 5.3 / 22.0 | 0.0053 | 0.0135 | 11.1% | 30.4% |
| ORB/LK · manual | hinge | 5.1 / 42.3 | 0.0034 | 0.0110 | 0.0% | 0.0% |
| ORB/LK · manual | slider | 5.7 / 41.7 | 0.0094 | 0.0217 | 0.0% | 0.0% |

**Method.** Four original procedural videos contain 600 frames at 640×480 and 30 fps. The benchmark reads every second frame (15 source frames/s; 300 processed frames per successful trial), JPEG-encodes it at the same quality as the app, then runs the actual decoder, tracker, geometry and control. Offline execution is unpaced; processing time is not the source frame interval or live throughput. Ground-truth boxes provide perfect initial user selection. Learning runs over approximately the first six seconds and uses the same fitting thresholds as the application. Ground truth is used only for scoring and selection in this benchmark, never to drive the application's animation.

Hinge travel is approximately 48°, slider travel 78 reference-image pixels. Common prop translation/rotation is superimposed. The occlusion clip adds blur at frames 330–359, partial cover at 365–384, and full cover at 390–424. All backend thresholds were developed on these clips: **they are not a held-out test set**. QDQ calibration also used 40 frames from the development hinge/slider clips.

Raw control errors compare an available estimate with the analytically known relative transform, normalized using that trial's calibrated observed range. They are conditional on availability and do not penalize missing samples; read them alongside both loss columns. This scoring measures control extraction, not error in independently measured mechanical limits. Visible tracking loss excludes annotated partial/full covers and the first frame. Post-learning unavailability includes covered periods, inconsistent geometry and the recovery hold. The manual baseline supplies the exact procedural pivot/axis while retaining ORB tracking and learned range; it does not measure human configuration effort. ArUco uses a separate marker-textured version of the hinge, so its easier appearance and automatic marker selection are part of that baseline.

## Whole-prop leakage, jitter and recovery

The joint is held at a fixed internal opening while the entire prop moves. Raw standard deviation and peak-to-peak control over seconds 11–14 summarize jitter/leakage. They combine tracker noise and residual common-motion coupling; they are not a separate physical accuracy measurement.

| Backend | Fixture | Raw standard deviation | Raw peak-to-peak | Available after full uncover |
|---|---|---:|---:|---:|
| orb | hinge | 0.0006 | 0.0025 | — |
| orb | slider | 0.0094 | 0.0322 | — |
| orb | occlusion | 0.0063 | 0.0177 | 367 ms |
| xfeat | hinge | 0.0030 | 0.0110 | — |
| xfeat | slider | 0.0041 | 0.0141 | — |
| xfeat | occlusion | 0.0045 | 0.0149 | 500 ms |
| marker | marker | 0.0060 | 0.0244 | — |
| xfeat-qdq | slider | 0.0037 | 0.0145 | — |
| xfeat-qdq | occlusion | 0.0045 | 0.0148 | 633 ms |
| orb · manual | hinge | 0.0006 | 0.0025 | — |
| orb · manual | slider | 0.0094 | 0.0321 | — |

Recovery is the first available sample after frame 425, reported on the 30 fps source clock with the stride-two sampling limit (about 67 ms). The final 180 ms blend to the reacquired signal is additional. A dash means the fixture had no cover event. The implementation holds the last reliable output while unavailable; it never predicts hidden joint motion.

The learned path was iterated with seeded forward/backward LK refinement, patch appearance validation, feature replenishment, bounded ECC pose refinement, and a calibrated geometry consistency guard. These reduced descriptor localization bias and rejected coherent tracking of an occluder. The remaining occlusion gap is a real limitation, not evidence that the model is beneficial merely because it runs. Next improvements should be driven by real development footage before freezing a held-out protocol.

## Browser pipeline check

The checked build passed the complete selection → learning → confirmation → three bindings → assisted drawing → record/replay → save/load workflow with no browser JavaScript errors. The test downloaded a session and reopened it, checked a 390 px viewport for overflow, and verified the no-camera recovery message. Evidence: `reports/ui-smoke.json`, `reports/test-session.json` and the three `studio-*.png` captures.

Source: `reports/browser-diagnostics.json`, one headless Chromium 134 run using the decoded synthetic hinge WebM and the ORB backend.

| Quantity | Measured value / scope |
|---|---|
| Input clip rate | 30 fps; recorded synthetic input |
| Processed response rate | 23.2 fps at export, rolling two-second window |
| Browser render loop | 60.0 requestAnimationFrame callbacks/s |
| Processing p50 / p95 | 5.4 / 47.3 ms |
| Frame age p95 | 65.5 ms, canvas sample to response handling |
| Neural update rate | None in this ORB run |
| Control smoothing | 55 ms first-order time constant |
| Stage easing | 22 ms first-order time constant |
| Physical camera rate / camera-to-display latency | Unmeasured |
| Whole-system power / battery life | Unmeasured |
| NPU execution / Snapdragon throughput | Unverified |


Frame age includes JPEG encoding, transport and response handling but ends **before the next paint**. Browser camera buffering/exposure, actual display scanout and input-to-filter response are excluded. Smooth render callbacks are not proof of GPU placement or physical display quality. The 150 ms p95 software capture-to-render goal remains a goal; the response-age measurement alone does not certify it. XFeat's neural inference refreshes every 12 processed frames or on loss, and the app reports its measured refresh rate separately. Any `neural_refresh_hz` in the unpaced offline report is offline throughput, not a live camera rate.

`scripts/camera_smoke.mjs` separately passed the successful getUserMedia → selected parts → learned hinge → animated control software path using Chromium's **fake camera**. This is API/integration coverage, not a physical webcam trial. `reports/camera-smoke.json` preserves that distinction. `scripts/evaluate_video.py` was also exercised against the saved synthetic session; `reports/evaluation-smoke.json` and `.csv` record that CLI check without independent real-prop truth.

## Tests, model checks and outstanding evidence

- **24 Python tests passed**: noisy geometry, common transforms, wrapping, insufficient/degenerate input, serialization, mapping, hold/recovery, decoded pixel tracking, occlusion, dropped frames, selection frame identity, service errors and strict QNN rejection.
- **3 JavaScript tests passed**: replay fidelity/holds, invalid recordings and display-to-image selection coordinates. TypeScript compilation and production bundling passed.
- Export parity on the checked input: maximum absolute FP32 output differences from the pinned PyTorch model were 7.63e-6, 1.41e-5 and 1.19e-7. These are numerical export checks, not control robustness scores.
- QDQ CPU output mean absolute differences were 0.152, 0.362 and 0.00872 for the three outputs. Quality must be judged by the downstream rejection/loss/error results above.
- The optional inference worker was exercised with actual CPU inference. Its ORT profile contains CPU node events; `reports/worker-cpu/placement.json` explicitly reports zero QNN node events. Provider availability was not mistaken for NPU execution.
- Human setup time, selection correction count, physical retries, two held-out handmade hinges, one held-out slider, action-to-display latency and target power are **not measured**. No physical trials were possible here. Use `held-out-protocol.md` and `snapdragon.md` to collect the missing evidence.

## Reproduce

From the project directory with the README's development environment installed:

```bash
python -m pytest
npm test
npm run build
python scripts/benchmark.py --backends orb xfeat marker xfeat-qdq --include-manual
KAKASHI_PYTHON=.venv/bin/python node scripts/ui_smoke.mjs
KAKASHI_PYTHON=.venv/bin/python node scripts/camera_smoke.mjs
python scripts/evaluate_video.py --video fixtures/hinge.mp4 --session reports/test-session.json --stride 2 --output reports/evaluation-smoke.json
```

Playwright Chromium is required for browser checks, and ffmpeg for the fake-camera conversion. The browser scripts start their own local service. See the README for the PowerShell environment-variable equivalent. None of these commands establishes NPU or real-camera performance.
