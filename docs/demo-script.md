# Two-minute live demonstration

This script is ready to rehearse. It has **not** been successfully performed on held-out handmade props or a Snapdragon PC here. Qualify the physical setup first.

Prepare a fixed webcam, a matte textured two-part hinge, markers as a disclosed recovery baseline, the local app, and a saved fallback session. Start with the classical backend unless a tested learned backend performs better on the supported prop. Open Diagnostics beforehand to check actual source/backend and camera permission. Keep the laptop offline after dependencies are installed if demonstrating local operation.

| Time | Action | Say / show |
|---|---|---|
| 0:00–0:20 | Connect camera. Hold an unfamiliar supported hinge. Freeze and draw one box inside each part, excluding fingers. Confirm selection. | “These are two textured rigid parts and one joint. I select the visible patches.” |
| 0:20–0:45 | Start learning. Slowly open/close through a broad in-plane range. Finish. Show the proposed hinge, pivot/residual in the saved profile or correction controls, and observed range. Confirm or visibly correct. | “Kakashi proposes a reusable opening control from the relative motion. This is the travel I demonstrated, not the mechanical limit.” |
| 0:45–1:05 | Choose Ember. Start recording and perform with the wings. | “The learned control is independent of this rig.” |
| 1:05–1:20 | Hold the joint opening fixed while translating and gently rotating the entire prop in the image plane. | Point to the control trace. Admit drift if it occurs; do not hide it with the dead zone. |
| 1:20–1:35 | Click Bloom without recalibrating. Continue opening/closing. | “The same control now opens a flower.” |
| 1:35–1:50 | Briefly cover one selected patch. Reveal it in a recoverable orientation. | Show “control held,” consistent reacquisition and the short blend. If recovery fails, reselect visibly and count the retry. |
| 1:50–2:00 | Stop recording. Replay. Open Diagnostics. | “This is recorded control replay. These are the actual backend and software timings.” No NPU claim without execution evidence. |

## Recovery without misrepresentation

If the camera or prop fails, announce the switch before selecting **Example · hinge/slider/occlusion** or opening a real recorded clip. The built-in examples are labelled **RECORDED INPUT** and contain a synthetic-video watermark. They decode actual pixels through the same vision pipeline; they do not supply a precomputed control trajectory to the app. Recording replay is separately labelled **RECORDED CONTROL REPLAY** and does not run inference. Do not call either mode live camera inference.

The demonstration is not a competition submission. Nothing is published or sent by these scripts.
