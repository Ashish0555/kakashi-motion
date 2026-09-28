# Status — 28 September 2026

This is a runnable development prototype. **Do not describe all five milestones as completed.** Real handmade-prop validation and Snapdragon execution require hardware and observations that were unavailable here.

| Milestone | Implemented | Verified here | Outstanding |
|---|---|---|---|
| 1. Camera-to-control-to-animation | Browser webcam ownership, explicit two-box selection, classical and marker tracking, relative transforms, original animated stage | Real decoded video through the full UI/service; successful getUserMedia path with Chromium's explicitly fake camera; source/error/coordinate handling | A physical webcam connected to a supported real mechanism |
| 2. Controller learning | Robust hinge/slider fits, observed range, proposal/confirmation/correction, common-motion cancellation, unwrapping, filtering, loss/hold/blend | Focused geometry/state tests; noisy analytic trajectories; decoded hinge/slider/occlusion fixtures; manual/marker comparisons | Practical envelope, setup effort and independent error measurements on real props |
| 3. Learned perception | Actual pinned XFeat ONNX inference, descriptor correspondence/refinement, LK tracking/reacquisition; CPU backend; QDQ candidate and strict QNN boundary | CPU inference, export parity, normalized descriptors, occlusion recovery regression and benchmark comparisons | Overall real-world advantage over classical tracking is **not established**; learned tracking remains experimental, especially under rotation/occlusion |
| 4. Creator workflow | Three directly bound rigs, assisted two-part drawing/import, mapping, recalibration, recording/replay, save/load, diagnostics, launcher scripts, prebuilt interface | Browser workflow smoke tests, downloaded/reopened session with drawing/recording, responsive overflow check and camera-error recovery | Real stage rehearsal, accessibility/user study and native OS launcher qualification |
| 5. Snapdragon validation | Target guide, pinned native worker dependencies, quantization/export scripts, profile inspection and matched-quality benchmark commands | QDQ CPU numerical check; loopback worker protocol using actual CPU inference | HP model/SoC, native installation, QNN/QAIRT compilation, executed HTP partitions, matched-quality NPU comparison, target pipeline/power measurement |

## Verification evidence

- `reports/ui-smoke.json`: browser selection → demonstration → confirmation → three bindings → drawing → record/replay → save/load; no browser JavaScript errors in the checked run.
- `reports/camera-smoke.json`: successful browser camera API branch using a **fake camera fixture**; never evidence for real-camera robustness.
- `reports/baseline.json`: reproducible synthetic development video comparisons. The fixtures are included with source generators and ground truth.
- `reports/browser-diagnostics.json`: measured software timings/rates for the recorded-input UI run; physical camera exposure and display latency are excluded.
- `reports/worker-cpu/`: CPU-only execution profile demonstrating that placement inspection reports CPU honestly.
- Focused Python and JavaScript tests cover geometry, insufficient evidence, wrapping, calibration serialization, mapping, hold/recovery, frame ordering, pixel-to-control integration, selection coordinates and replay.
- Final focused suite: **24 Python tests and 3 JavaScript tests passed**. The QNN rejection test proves that missing QNN does not silently become CPU inference; it does not prove NPU execution.

## Experimental / not claimed

- General recognition of arbitrary mechanisms or arbitrary objects.
- Automatic character rigging, 3D reconstruction, cloth or multi-joint motion.
- Learned perception superiority just because a model is present.
- The QDQ candidate failed the clean hinge fit in the final synthetic comparison. It is not qualified for deployment. FP32 XFeat has worse occlusion availability than ORB in these fixtures; ORB remains the default.
- Exact invariance under perspective/out-of-plane motion.
- NPU execution, battery savings, target throughput or physical camera-to-display latency.
- Completed held-out tests: **0 real hinges, 0 real sliders**. The required two hinges and one slider are explicitly pending in `held-out-protocol.md`.

## Next dependent work

1. Run the portable app on a PC with a webcam and collect development footage. Fix any real-texture, selection, blur or viewpoint failures before changing claims.
2. Freeze thresholds/model hashes and conduct the three held-out handmade-prop trials, recording failures, retries and assistance.
3. Identify the actual Snapdragon HP SoC/driver, qualify the native QNN worker and inspect executed partitions. Compare the same model/settings on CPU and NPU.
4. Measure real interactive latency and rehearse the two-minute demo. Do not substitute a recorded example without announcing it.
