# Architecture and operating envelope

## A deliberately small system

React/TypeScript provides the creator interface. A single FastAPI process owns tracking, fitting and control state for each WebSocket connection. The browser alone owns camera capture. Original editable SVG rigs keep the renderer small and offline; the browser decides compositing/GPU placement, which has **not** been measured. There is no LLM, account, cloud inference, remote asset request, or CUDA dependency in the runtime.

The default path uses OpenCV ORB plus pyramidal Lucas–Kanade tracking. The experimental path uses the actual XFeat ONNX network for feature extraction, descriptor matching and reacquisition, then the same geometry. An explicit ArUco 4×4/50, IDs 0/1 baseline is supplied. `scripts/inference_worker.py` is an optional extra process only for Windows ARM64 deployment where pinned x64 OpenCV dependencies cannot coexist with the native QNN runtime. It sends preprocessed tensors over loopback, not over the Internet.

## Capture and coordinate contract

1. `getUserMedia` or a clearly labelled file-backed video feeds one offscreen canvas. Resolution is fitted to at most 640×480 with preserved aspect ratio. Frames are **unmirrored**, with x right and y down.
2. Each JPEG is preceded by a little-endian 32-bit JSON-header length. The JSON contains increasing `frame_id` and `capture_t` in browser `performance.now()/1000` units. The server never compares that clock directly to its own clock.
3. Only one camera request can be in flight. New camera frames are skipped while busy. WebSocket queue length is one. Duplicate or out-of-order IDs/timestamps are rejected; gaps over 250 ms force descriptor reacquisition and make the control temporarily unavailable.
4. The display draws the exact submitted bitmap after its corresponding result arrives. Overlay polygons are in that same bitmap's coordinate system. Selection pauses capture, waits for the current request, and sends the frozen frame ID. Selection against any older server frame is rejected.
5. Pointer positions are scaled from the displayed element rectangle to native canvas coordinates. There is no CSS mirror or hidden crop. A dimension change requires new selections. Browser responses older than 250 ms cannot update the live control; no input for 600 ms marks it held.

Camera exposure latency is not known. Browser frame-age diagnostics cover canvas sampling through response handling, not actual photons-to-display latency. The browser render loop is counted independently. Video fixture rate and processed rate are distinct.

## Transform conventions

All points are homogeneous **column vectors**. Each part transform maps pixels in the selected reference image into the current image:

`p_current = T_A · p_reference_A`, and similarly for B. Both reference coordinate systems are the same image, not separate crop-local systems.

`T_relative = inverse(T_A) · T_B`.

For common planar motion G, `inverse(G · A) · (G · B) = inverse(A) · B`. This is why moving/rotating the entire prop should not animate its internal joint. It does not promise invariance to perspective or out-of-plane rotations.

For a hinge at reference-image pivot p: `t = (I − R) · p`. A robust least-squares fit estimates p over the demonstration. For a slider, translation principal components propose an axis; perpendicular residual and relative orientation reject unsuitable movement. Angles are unwrapped for fitting and updated with shortest wrapped deltas during performance. Relative scale changes over 8% are rejected. A live pose must also agree with the confirmed joint geometry, which guards against plausible-looking drift.

## Fitting and availability

- At least 24 reliable samples and 0.7 seconds are required. Suggested user demonstrations are 3–8 seconds.
- Default hinge excitation: at least 15°. Slider travel: at least 20 canonical pixels with little relative rotation. A small arc is intentionally ambiguous.
- Hinge residual/conditioning, translation orthogonality, feature spread, inlier ratio, forward/backward optical-flow consistency and selected-patch appearance all contribute checks.
- Reported travel is the robust 2nd–98th percentile **observed** range, not a physical mechanical limit. Outliers are not treated as stops.
- Manual hinge/axis corrections are labelled and serialized. They do not bypass a no-motion failure.
- Lost or geometrically inconsistent tracking holds the last output and marks it unavailable. Three consecutive reliable observations are required to resume, followed by an explicit 180 ms blend. Nothing is extrapolated through occlusion.
- Sensitivity is centered on 0.5, inversion reverses output, dead zone is normalized hysteresis, and smoothing is a time-based first-order low-pass filter. Default time constant: 55 ms. Stage easing adds a 22 ms time constant. Both contribute response delay.

## Tracking design and known limits

Reference descriptors anchor the two user-selected patches. Features are matched periodically (every 12 processed frames), or during loss/reacquisition. RANSAC similarity transforms filter matches. XFeat matches receive forward/backward image alignment. Both backends then use bounded ECC subpixel refinement of accepted descriptor poses, which reduces localization bias before fitting a joint. Tracked corner sets are replenished inside accepted part polygons. An independent normalized patch-correlation check rejects texture that has disappeared. None of these checks ensures identity under every repeated pattern or occlusion.

Use approximately rigid, matte, textured parts large enough for at least 12 distinctive features. Boxes should lie entirely within one part and exclude fingers, joint gaps and background. Aim for patches at least 80×80 canonical pixels, stable diffuse light, a fixed camera, and modest scale/perspective variation. Begin with slow in-plane motion. These are engineering recommendations, **not a physically validated envelope**. Test each real prop before presenting.

Untextured, reflective, flexible or repeating surfaces, severe blur, large sudden rotations, background leakage and long occlusions remain failure modes. A saved reference may not reacquire from a very different viewpoint. Reselect and recalibrate visibly when necessary.

## Persistence and recording

Session JSON contains schema version, reference JPEG, part selections, calibration, backend, mapping, selected rig, assisted drawing, normalized control samples and source label. It therefore includes one camera image; the save flow says so. The downloaded file is portable. The most recent save is also retained in browser local storage when capacity permits. An unsuccessful browser-local backup does not affect the downloaded file.

Replay interpolates available samples without rerunning vision or a second smoothing filter; it holds across unavailable spans. Maximum recording length is 18,000 samples. Videos are not stored in the session. Drawing imports are rasterized to PNG, two parts share one canvas, and the pivot/axis is manually authored. This is assisted rigging, not arbitrary automatic character rigging.

## File map

| File | Responsibility |
|---|---|
| `src/client.ts` | Capture ownership, frame protocol, backpressure, source errors |
| `src/App.tsx` | Show → Learn → Bind → Perform → Save |
| `src/Rigs.tsx`, `src/DrawingEditor.tsx` | Original rigs and assisted drawing |
| `src/timeline.js` | Recording validation, replay, display coordinate mapping |
| `backend/perception.py` | ORB/XFeat/QNN boundary and preprocessing |
| `backend/tracking.py` | Correspondence, flow, transform estimation, reacquisition |
| `backend/geometry.py` | Joint hypotheses, residuals, conditioning, calibration |
| `backend/control.py` | Mapping, filtering, hold/recovery state |
| `backend/engine.py` | Session orchestration and persistence |
| `backend/app.py` | Loopback HTTP/WebSocket service |
| `scripts/` | Reproducible fixtures, evaluation, model export, quantization and placement checks |
