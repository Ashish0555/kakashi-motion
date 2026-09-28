# Physical-prop validation — outstanding

No real camera or handmade mechanisms were available in the development container. **Zero held-out physical trials have been completed.** Synthetic fixtures must not be entered as physical results.

Freeze code/model hashes and parameters before collecting the following three mechanisms. Their images and videos must not have been used to tune thresholds or quantization:

1. A cardboard hinge with independent printed texture on each leaf.
2. A differently sized paperboard/book-cover hinge with different texture and pivot placement.
3. A textured two-part sliding strip in a rigid guide.

Use each prop with classical ORB, experimental XFeat, printed-marker baseline, and manual joint/axis configuration. Where verified QNN execution becomes available, compare **the same QDQ model**, resolution, postprocessing and thresholds on CPU versus QNN. Keep floating-point comparisons separate from quantization comparisons.

For every trial save raw input video, session JSON, diagnostics, the software/model hashes, and a metadata file:

```json
{
  "trial_id": "heldout-hinge-01-orb-trial-1",
  "split": "held-out real prop",
  "prop": "Describe materials, dimensions, texture, and joint",
  "hardware": {"pc": "", "soc": "", "camera": "", "driver": ""},
  "lighting": {"description": "", "lux_measured": null},
  "camera": {"distance_cm": null, "placement": "", "resolution": "", "fps": null},
  "manual_assistance": [],
  "setup_seconds_measured": null,
  "retries": null,
  "failures": [],
  "software_commit_or_archive_sha256": "",
  "model_sha256": "",
  "physical_camera_to_display_p50_ms": null,
  "physical_camera_to_display_p95_ms": null,
  "whole_system_power_watts_measured": null
}
```

Record at least three repeats per condition. Include opening/closing, constant-joint common translation/rotation, a brief partial occlusion, a full occlusion, blur/fast motion, and recovery. Log **all** failures and retries, not just the best take. Compare action ranges in canonical pixels or degrees; use separately measured ground truth. Manual labels from the same tracker are not independent ground truth.

Use `scripts/evaluate_video.py` for offline trace extraction. Optional ground-truth CSV columns are `time_s,control`, normalized using the saved profile. Keep filtering/mapping constant for matched-quality comparisons. Report normalized error/jitter, leakage while internal motion is fixed, available/lost fraction, and seconds from uncovering to a reliably available control.

Physical action-to-display latency needs an external high-speed view that sees both the real mechanism and screen (or an equivalent instrumented event). Report camera rate, vision rate, browser rendering rate, filter delay and p50/p95 software timings separately. Browser canvas timestamps exclude camera buffering/exposure. Use a measured wall-power instrument for power when available; otherwise leave power and battery life unmeasured.

Initial acceptance goals, not claims: p95 software capture-to-render below 150 ms, smooth stage rendering, stable internal control under common planar movement, honest hold/recovery, and successful user authoring on all three held-out props. Revise the documented envelope if trials fail. The two-minute stage demo should not be presented as reliable until these checks pass.
