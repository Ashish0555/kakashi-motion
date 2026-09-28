# Snapdragon-powered HP PC deployment

**Target execution is unverified.** Development used Linux x86_64, Python 3.12 and CPU inference. No HP PC, Snapdragon NPU, camera, power meter, or target driver was exposed. The exact HP model/SoC and installed NPU driver are still unknown; record these before profiling. This guide does not certify that the candidate graph will compile for that device.

## 1. Portable CPU baseline on Windows ARM

The pinned OpenCV 4.11.0.86 / SciPy 1.15.3 / NumPy 2.2.6 stack has x64 wheels but no Windows ARM64 wheels in the package metadata checked. Use **x64 Python 3.12 under Windows x64 emulation** for this baseline, including on a Snapdragon PC. That is CPU execution, not NPU acceleration.

Install x64 Python 3.12 to an explicit location, for example `C:\Python312-x64`. Extract the archive and run in the `kakashi` directory:

```powershell
& C:\Python312-x64\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

The browser opens at `http://127.0.0.1:8765`. After setup, `Launch-Kakashi.cmd` uses the existing environment. Select **Classical · ORB + optical flow** or **Learned · XFeat ONNX CPU** in Diagnostics. The built interface, models and examples are bundled; Node is unnecessary for normal launches. Installation downloads dependencies; performance itself is offline.

Record hardware without guessing:

```powershell
Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model
Get-CimInstance Win32_Processor | Select-Object Name,Architecture
Get-PnpDevice | Where-Object FriendlyName -Match 'NPU|Hexagon|Qualcomm|Camera'
.\.venv\Scripts\python.exe -c "import platform,onnxruntime as o; print(platform.platform(),platform.machine(),o.__version__,o.get_available_providers())"
```

## 2. Prepare the model and real calibration footage

`models/xfeat.onnx` is a fixed-shape FP32 export of the pinned official XFeat architecture/weights. `models/xfeat.qdq.onnx` is a **candidate** quantized on synthetic development frames, included to make the workflow reproducible. It is not qualified for the target. The manifests record hashes, preprocessing, operator inventory, quantization and numerical checks.

The bundled QDQ candidate failed the clean hinge fit in the final development benchmark. Correct and requalify its control quality before treating any target timing as a usable acceleration result; see `benchmark.md`.

Before target qualification, collect representative **development** footage under actual lighting (never the held-out props). On a development machine with `requirements-dev.txt` installed:

```bash
python scripts/quantize_qnn.py --videos development-hinge.mp4 development-slider.mp4
python scripts/benchmark.py --backends xfeat xfeat-qdq --output reports/quantized-quality.json
```

The benchmark command uses bundled synthetic fixtures; also evaluate saved sessions on the real development footage with `scripts/evaluate_video.py`. Check control error, availability and reacquisition after quantization. Similar neural output error alone is insufficient. Inputs are normalized grayscale `1×1×256×320`, with mean/variance normalization on CPU. Matching, refinement, tracking, fitting and filters remain CPU work. No ONNX `GridSample` or NMS is required in the neural graph; postprocessing is NumPy/OpenCV. Static shapes still do **not** prove QNN operator support.

## 3. Native ARM64 QNN worker

The optional worker isolates the native NPU runtime from x64 OpenCV. Install **ARM64 Python 3.12** at a distinct path, for example `C:\Python312-arm64`. Verified package availability: Windows ARM64 wheels for `numpy==2.3.5` and `onnxruntime-qnn==1.22.2`. These pins have not been installed on a target here. Do not replace the ordinary `onnxruntime` package inside the x64 environment with the ARM64 package.

```powershell
& C:\Python312-arm64\python.exe -m venv .venv-qnn
.\.venv-qnn\Scripts\python.exe -m pip install -r requirements-qnn-worker.txt
.\.venv-qnn\Scripts\python.exe -c "import platform,onnxruntime as o; print(platform.machine(),o.__version__,o.get_available_providers())"
.\.venv-qnn\Scripts\python.exe scripts\inference_worker.py --model models\xfeat.qdq.onnx --provider qnn
```

Use the latest supported OEM Snapdragon NPU driver for the actual PC. The pinned runtime expects its matching QNN libraries; inspect package/driver compatibility if loading fails. The worker chooses `QnnHtp.dll`, enables detailed profiling, disables CPU execution-provider fallback, and performs a real warm-up before advertising readiness. Missing providers, unsupported graphs or driver errors stop the worker. It does not silently select CPU.

In a second terminal:

```powershell
$env:KAKASHI_QNN_WORKER = 'http://127.0.0.1:8766'
.\.venv\Scripts\python.exe run.py
```

Choose **QNN HTP candidate** in Diagnostics. The service checks the worker's model hash and refuses a CPU worker in QNN mode. Requests contain one fixed preprocessed tensor; responses contain compact network feature maps. Include this loopback IPC overhead in end-to-end measurements. The extra process is a packaging workaround, not proof that all app code runs natively. The CPU path also works without this process.

## 4. Verify placement and matched quality

Stop the worker with Ctrl+C to save `reports/qnn-profile/environment.json`, an ORT event profile, and detailed QNN events when provided by the runtime. Inspect the actual file name printed at exit:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_placement.py reports\qnn-profile\ort_TIMESTAMP.json --output reports\qnn-placement.json
```

`get_available_providers()` or successful provider loading is not execution evidence. Require real QNN node events, the HTP configuration, no unintended CPU fallback, target device/driver metadata, and detailed backend profiling. Review graph partitions and any host-side operations. The interface conservatively says placement is unverified until this evidence is reviewed; no synthetic NPU utilization is shown.

For a CPU comparison, run **the same QDQ model** (`xfeat-qdq`) on the same input videos, selections and settings. `scripts/benchmark.py --backends xfeat-qdq qnn` can exercise the candidate worker through the same tracking pipeline. Use unchanged control-quality thresholds. Compare tracking availability and control errors as well as neural inference time. QNN on-device timings, frame age, camera/inference/render rates, filter delay and action-to-display measurements must be reported separately. Do not compare a smaller or worse-quality model and call the difference an NPU speedup.

## 5. Qualcomm AI Hub / QAIRT route

Official [AI Hub Workbench documentation](https://workbench.aihub.qualcomm.com/docs/hub/compile_examples.html) supports ONNX compilation and device-specific QNN artifacts. The [QNN EP guide](https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html) covers the local runtime. Use the actual PC's SoC and supported QAIRT version; do not select a phone by assumption. AI Hub compilation/profiling is an optional development-time cloud operation; **none was submitted here** and none is needed during live performance.

After installing/configuring the official `qai-hub` client, list devices and compile/profile explicitly. This example follows the current client API and has not been run against an account:

```python
import qai_hub as hub
client = hub.Client()
for device in client.get_devices():
    print(device)
# Replace with an exact supported device returned above that matches your SoC.
target = hub.Device("EXACT_RETURNED_DEVICE_NAME")
job = client.submit_compile_job(
    model="models/xfeat.qdq.onnx", device=target,
    options="--target_runtime onnx", input_specs={"image": (1, 1, 256, 320)}
)
job.download_target_model("models/xfeat-aihub.onnx")
profile = client.submit_profile_job(model=job.get_target_model(), device=target)
print(profile)
```

Record client/QAIRT versions, job IDs, downloaded model hash, graph compatibility and profile. Cloud profiling on a reference device still does not measure the user's HP camera-to-screen pipeline. If compiled outputs or shapes differ, adapt and revalidate the small perception boundary rather than claiming the bundled candidate is equivalent.

## Outstanding target gates

Native installation; driver/SoC compatibility; model compilation; executed HTP partitions; quantized control quality on real footage; actual HP end-to-end p50/p95 latency; whole-system power where measured. See `held-out-protocol.md`. The initial 150 ms p95 software capture-to-render goal remains a goal.
