# Optimization Audit — face_recognition_project

**Scope:** Full repository (`src/`, `button_trigger_with_rfid.py`, `setup_rfid_cards.py`, `start_face_auth_complete.sh`).
**Method:** Static read-through of every module (no profiler run, no access to a live Raspberry Pi or the `data/`/`output/` corpora — both are gitignored and empty in this checkout). Findings backed only by code inspection are labeled **likely**, with the measurement needed to confirm them.

**Assumptions** (state clearly since some context is missing):
- Target hardware is a Raspberry Pi (4 or 5 — `lgpio`/`LGPIOFactory` is used, which is the Pi 5-recommended backend). CPU-bound, no GPU.
- Training corpus is small (registration defaults to 10 photos/person, guided registration to 5 poses × 2 photos = 10). The dataset-growth findings (F3) matter more as usage scales past a handful of users.
- `auth` (one-shot) is the command actually invoked in production, via `button_trigger_with_rfid.py` → `python -m src.main auth --anti-spoofing` (confirmed in code and in `start_face_auth_complete.sh`). `monitor` is a secondary/manual mode.

---

## 1) Optimization Summary

**Current health:** The security logic itself (liveness + recognition + face-quality voting) is thoughtfully built, and some real perf work has already happened — 320×240 capture resolution, HOG-not-CNN by default, a frame-skip cache in `HeadPoseDetector`. But the system has **three independent, hand-rolled copies of the same authentication loop** with diverging behavior, and the actual production entrypoint (`auth`) bypasses the one implementation (`BiometricAuth`) that has a threaded recognition pipeline. On top of that, the deployed trigger script re-execs the entire Python process — reloading TensorFlow/DeepFace, dlib, MediaPipe, and reopening the camera and GPIO — on every single button press. There is no test suite and no profiling instrumentation anywhere in the repo.

**Top 3 highest-impact improvements:**
1. **Stop cold-starting the whole process per button press** (`button_trigger_with_rfid.py` → `subprocess.run([...,"auth",...])`). This single change likely dominates perceived latency more than any algorithmic fix below.
2. **Route the `auth` CLI command through `BiometricAuth`'s existing threaded pipeline** instead of the ~230-line duplicate, fully-synchronous loop in `main.py::run_authenticate`. This removes a maintenance hazard *and* buys the threading speedup for free.
3. **Stop DeepFace from re-detecting faces it's already been handed a crop of** (`detector_backend="skip"` instead of `"opencv"`), and **stop `FaceEncoder` from re-encoding the entire training set for every single new photo**.

**Biggest risk if nothing changes:** On real Pi hardware, every unlock attempt pays full interpreter + ML-framework import cost, then runs a fully synchronous, un-threaded per-frame loop with a blocking DeepFace call in it. Users will perceive the lock as slow and are likely to hit the button repeatedly, fighting the debounce/cooldown logic. Separately, the anti-spoofing "is this face real" filter is implemented three times with already-diverged logic (`all()` vs `any()` over detected face objects) — the next security tweak has a good chance of being applied to only one of the three copies, silently leaving the others less strict.

---

## 2) Findings (Prioritized)

### Finding 1 — Subprocess-per-trigger cold start reloads the entire ML stack and re-opens hardware every attempt
- **Category:** Reliability / Cost / CPU
- **Severity:** Critical
- **Impact:** End-to-end unlock latency, CPU/power draw per attempt, perceived responsiveness
- **Evidence:** `button_trigger_with_rfid.py:472-484` builds `cmd = [sys.executable, "-m", "src.main", "auth", "--anti-spoofing"]` and runs it with `subprocess.run(cmd, cwd=..., capture_output=True, timeout=120)` on **every button press**. That child process re-imports `deepface`/`tf-keras`/`torch`-adjacent stack, `face_recognition`/`dlib`, `mediapipe`, re-opens the V4L2 camera (`CameraHandler.start()`), and re-initializes the `lgpio` pin factory (`GPIOLock.__init__`, `gpio_lock.py:47-70`) from scratch.
- **Why it's inefficient:** TensorFlow/Keras + DeepFace import alone commonly takes multiple seconds on a Pi; dlib and MediaPipe add more. None of this is amortized across attempts — a long-running daemon would pay this cost once at boot instead of once per door-open.
- **Recommended fix:** Convert the button-trigger process into the long-lived daemon: import `BiometricAuth` (and its `FaceRecognizer`/`AntiSpoofing`/`GPIOLock`) once at startup, keep the camera handle warm (or open/close it, but skip re-importing frameworks), and on button press call `auth.authenticate(...)` in-process instead of `subprocess.run`. Communicate results via return value/callback instead of parsing captured stdout text (`"✅ Authentication successful" in output_text` — brittle string matching, also worth fixing while here).
- **Tradeoffs / Risks:** Long-running process must manage camera/GPIO lifecycle carefully (crash recovery, resource leaks) instead of getting a clean slate each time; needs a supervisor (systemd) for restarts. Import-time state (e.g. `logging.basicConfig` in `utils.py`) must not be reinitialized per "logical" auth attempt.
- **Expected impact estimate:** Likely removes several seconds of fixed overhead per attempt — very plausibly the largest single latency component in the whole system. Needs a stopwatch measurement to quantify precisely (see Validation Plan).
- **Removal Safety:** Needs Verification (architectural change, not a deletion)
- **Reuse Scope:** service-wide

### Finding 2 — The actual `auth` CLI path bypasses `BiometricAuth`'s threaded pipeline and duplicates it synchronously
- **Category:** Concurrency / Code Reuse
- **Severity:** Critical
- **Impact:** Latency (no producer/consumer overlap between frame capture and recognition), maintainability
- **Evidence:** `main.py::run_authenticate` (`main.py:44-304`) constructs `auth = BiometricAuth(...)` but never calls `auth.authenticate()`. Instead it hand-rolls its own camera loop that calls `auth.recognizer.recognize_face_in_frame(frame)` directly (`main.py:107`) and, when `--anti-spoofing` is set, calls `spoof_detector.is_live(frame)` **synchronously, inline, every frame** (`main.py:150-157`) — no worker thread, no queue. Meanwhile `BiometricAuth._recognition_worker` (`biometric_auth.py:79-142`) already implements exactly this pipeline with a `queue.Queue`-based producer/consumer split so frame capture and recognition/anti-spoofing overlap — but it's only reachable via `monitor`, not `auth`.
- **Why it's inefficient:** Every frame in the primary, documented command (`python -m src.main auth --anti-spoofing`) blocks on face detection *and* a DeepFace inference back-to-back on the same thread that also has to service `cv2.imshow`/`cv2.waitKey`. The already-written threaded version sits unused.
- **Recommended fix:** Make `run_authenticate` a thin wrapper around `auth.authenticate(max_attempts=..., timeout=...)`, passing through the `--window/--min-live/--min-match` args (which would need to be threaded into `BiometricAuth`, since it currently hardcodes `consecutive_matches_required` voting rather than `DecisionGate`). This is the point where Finding 2 and the duplication noted in Finding 5 should be fixed together.
- **Tradeoffs / Risks:** `BiometricAuth`'s per-user consecutive-match voting and `main.py`'s `DecisionGate` sliding-window voting are *not* behaviorally identical — unifying them changes authentication semantics slightly and needs to be validated against the "Security Testing Scenarios" already documented in `README.md`.
- **Expected impact estimate:** High — likely cuts effective per-frame latency substantially by overlapping capture with inference, in addition to deleting ~150+ lines of duplicate logic.
- **Removal Safety:** Needs Verification (behavioral merge, test against README's documented security scenarios)
- **Reuse Scope:** service-wide

### Finding 3 — `FaceEncoder.encode_known_faces()` re-encodes the entire training set on every single new photo
- **Category:** Algorithm / I/O
- **Severity:** High
- **Impact:** Registration latency, CPU, scales worse as the user base grows
- **Evidence:** `face_encoder.py:24-66` iterates **every** file under `TRAINING_DIR` (`for filepath in TRAINING_DIR.glob("*/*")`) and re-runs face detection + 128-d encoding on each. This is called by `add_face()` (`face_encoder.py:126`), `register_person_from_camera()` (`face_encoder.py:200`), and `GuidedRegistration`'s completion handler (`guided_registration.py:429`) — i.e. it runs after adding just one image.
- **Why it's inefficient:** Adding a single new photo triggers O(n) re-work over the whole corpus (n = all photos of all people ever registered), turning "register a person" into effectively O(n²) total work across a session with multiple registrations.
- **Recommended fix:** Add an `append_face(image_path, name)` path that loads the existing `encodings.pkl`, encodes only the new image(s), appends, and re-saves — instead of calling `encode_known_faces()`. Keep `encode_known_faces()` for the explicit `train` full-rebuild command where a full re-scan is the intended semantics.
- **Tradeoffs / Risks:** Two code paths (incremental vs. full rebuild) can drift if a training image is later deleted outside the app (encodings.pkl would still have a stale entry) — full rebuild remains necessary for cleanup/consistency, so keep it available, just don't call it as the default per-photo path.
- **Expected impact estimate:** Per-registration encoding time drops from O(total photos) to O(photos just added) — for a corpus of 50 photos, roughly a 10x+ reduction when adding one new photo.
- **Removal Safety:** Needs Verification
- **Reuse Scope:** module (`face_encoder.py`), consumed by `main.py`, `guided_registration.py`

### Finding 4 — DeepFace re-runs full face detection on regions that are already cropped to a detected face — ✅ FIXED
- **Category:** Algorithm / CPU
- **Severity:** High
- **Impact:** Anti-spoofing latency per frame per face
- **Evidence:** `AntiSpoofing.check_face_region` (`anti_spoofing.py:122-163`) and `AntiSpoofing.process_frame` (`anti_spoofing.py:165-219`) both crop the frame to `bbox` first (`face_img = frame[top:bottom, left:right]`, line 136/186) — a box already produced by `face_recognition.face_locations` — then called `DeepFace.extract_faces(..., detector_backend="opencv")`, which runs OpenCV's own face detector **again** on that crop. Same pattern in `biometric_auth.py:105-107` and `biometric_auth.py:225-227` (the two duplicated anti-spoofing blocks — see Finding 5) — except those two sites didn't pass `detector_backend` at all, silently relying on DeepFace's implicit `"opencv"` default.
- **Why it's inefficient:** Running a second face detector on an image that is already just a face is redundant work purely to satisfy DeepFace's API, and detector inference is one of the more expensive steps in the pipeline on CPU-only hardware.
- **Recommended fix:** Pass `detector_backend="skip"` (DeepFace's documented no-op detector for pre-cropped inputs) at these four call sites instead of `"opencv"`. Keep `"opencv"` only where the full, un-cropped frame is passed in (`AntiSpoofing.is_live`, `check_image`, `run_demo`), since detection is actually needed there.
- **Tradeoffs / Risks:** If the upstream bbox is loose/inaccurate (extra background included), skipping DeepFace's own re-detection could feed it a slightly worse-aligned face crop, which anti-spoofing models can be sensitive to — validate liveness accuracy doesn't regress before shipping (see Validation Plan; not yet run against real spoofed/live footage on hardware).
- **Expected impact estimate:** Medium-High — removes one full detector pass per face per frame in the anti-spoofing path specifically; exact % needs profiling since DeepFace's opencv detector on a 160×160 crop is already fairly cheap relative to model inference, but it's still 100% avoidable work.
- **Removal Safety:** Applied (Needs Verification on real hardware — validate against spoofed/live test images before relying on it in production)
- **Reuse Scope:** module (`anti_spoofing.py`), plus 2 duplicated inline copies in `biometric_auth.py`
- **Outcome:** Fixed at all 4 call sites (`anti_spoofing.py:146`, `anti_spoofing.py:199`, `biometric_auth.py:105-109`, `biometric_auth.py:225-231`). The two `biometric_auth.py` sites required *adding* the `detector_backend="skip"` argument (they had no explicit `detector_backend` before) rather than swapping an existing value — same fix, same effect, correcting the "one-word change" framing in the Quick Wins list below. Syntax-checked with `py_compile`; not yet exercised against live/spoofed camera input.

### Finding 5 — Anti-spoofing "is this face real" filtering logic is implemented three times, and has already drifted
- **Category:** Code Reuse / Reliability
- **Severity:** High
- **Impact:** Maintainability, bug/security-drift risk
- **Evidence:** The same "crop bbox → DeepFace.extract_faces(anti_spoofing=True) → check is_real → relabel as Fake" logic appears in:
  1. `biometric_auth.py::_recognition_worker`, lines 90-126 — uses `all(face_obj.get("is_real", False) for face_obj in face_objs)`
  2. `biometric_auth.py::_initialize_camera_and_process_frames` (non-threaded branch), lines 210-246 — byte-for-byte copy of #1
  3. `anti_spoofing.py::AntiSpoofing.process_frame`, lines 165-219 — uses `any(face_obj.get("is_real", False) for face_obj in face_objs)` instead of `all()`
- **Why it's inefficient:** Three copies of security-relevant logic that already disagree (`all` vs `any` changes whether a frame with multiple detected sub-faces needs *every* one to be real or just *one*) is a duplication smell with a realized correctness cost, not just a hypothetical one. It also means Finding 4's fix has to be applied in three places instead of one.
- **Recommended fix:** Extract a single `AntiSpoofing.filter_recognized_faces(frame, results, authorized_users) -> results` method (building on the existing `process_frame`) and call it from both `biometric_auth.py` sites, deleting the two inline copies.
- **Tradeoffs / Risks:** Must explicitly decide (and document) whether the semantics should be `all()` or `any()` — this is a product/security decision, not just a refactor.
- **Expected impact estimate:** N/A performance-wise; this is a correctness/maintainability fix that also enables Finding 4's fix to land once instead of three times.
- **Removal Safety:** Needs Verification (security-relevant semantics decision required)
- **Reuse Scope:** service-wide (`biometric_auth.py`, `anti_spoofing.py`)

### Finding 6 — Two ~250-line near-duplicate frame-annotation functions in `utils.py`
- **Category:** Code Reuse / CPU
- **Severity:** Medium
- **Impact:** Maintainability, and secondarily per-frame CPU (see Finding 7)
- **Evidence:** `draw_recognition_feedback_on_frame` (`utils.py:87-251`) and `draw_enhanced_anti_spoofing_feedback` (`utils.py:253-574`) both implement: frame-copy/validation boilerplate, per-result bbox clamping, corner-accent drawing, label-background alpha blending — differing only in color selection and label text composition. The second function is more than double the length of the first mostly to hand-draw multi-color label text segment-by-segment.
- **Why it's inefficient:** ~300 lines of copy-pasted geometry/drawing code that has to be kept in sync by hand; a bugfix to corner-accent math (e.g. `thickness`/`corner_length` clamping) needs to be applied twice.
- **Recommended fix:** Extract a shared `_draw_face_box(frame, bbox) -> (annotated_frame, geometry)` helper for the rectangle/corner-accent drawing, and a `_draw_label(frame, geometry, segments: List[Tuple[str, color]])` helper for the (possibly multi-colored) label text, then have both public functions call into these with their own color/label-composition logic only.
- **Tradeoffs / Risks:** Pure refactor, low behavioral risk if output pixels are diffed before/after on a few sample frames.
- **Expected impact estimate:** Maintainability win; CPU impact is captured separately in Finding 7.
- **Removal Safety:** Safe
- **Reuse Scope:** module (`utils.py`), consumed by `main.py`, `biometric_auth.py`, `face_recognizer.py`, `anti_spoofing.py`

### Finding 7 — Full-frame copy + alpha blend allocated per face just to draw a small label background
- **Category:** Memory / CPU
- **Severity:** Medium
- **Impact:** Per-frame allocation/compute overhead, scales with number of faces in frame
- **Evidence:** `utils.py:222` (`overlay = annotated_frame.copy()`) inside the per-result loop of `draw_recognition_feedback_on_frame`, and `utils.py:408` inside `draw_enhanced_anti_spoofing_feedback` — each allocates a **full frame-sized** copy (e.g. 320×240×3 bytes) and runs `cv2.addWeighted` over the whole frame just to alpha-blend a small text-label rectangle under one face.
- **Why it's inefficient:** The blend only needs to touch a small ROI (label width × label height); allocating and blending the entire frame is O(width×height) work to affect a region that's typically a few thousand pixels, repeated once per detected face per frame.
- **Recommended fix:** Blend only the label's bounding rectangle: slice the ROI (`annotated_frame[bottom:text_bottom, text_left:text_right]`), alpha-blend that sub-array in place, avoiding the full-frame `.copy()`.
- **Tradeoffs / Risks:** None functionally; purely a scoping change to the same `addWeighted` call.
- **Expected impact estimate:** Low-Medium in absolute terms (drawing is typically cheaper than detection/encoding), but it's free to fix once Finding 6's refactor touches this code anyway, and multiplies with face count.
- **Removal Safety:** Safe
- **Reuse Scope:** module (`utils.py`)

### Finding 8 — "Show status for 3 seconds" loop duplicated ~6 times across two files
- **Category:** Code Reuse
- **Severity:** Medium
- **Impact:** Maintainability
- **Evidence:** Nearly identical ~15-20 line loops (`while time.time() - start < 3.0: frame = camera.get_frame(); draw_authentication_status(...); cv2.imshow(...); check 'q'; time.sleep(0.03)`) appear at: `main.py:172-190` (success), `main.py:236-254` (max-frames failure), `main.py:260-277` (timeout failure), `main.py:283-300` (generic failure), `biometric_auth.py:318-336` (success), `biometric_auth.py:358-384` (failure).
- **Why it's inefficient:** Six copies of the same polling/draw/display loop, differing only in the status text — any future change (e.g. adding a sound cue, changing the duration, handling `camera.get_frame()` returning `None` differently) has to be applied six times.
- **Recommended fix:** Extract `show_status_screen(camera, window_name, status, message, is_success, duration=3.0)` once (in `utils.py` or a shared auth-UI module) and call it from all six sites.
- **Tradeoffs / Risks:** None; behavior-preserving extraction.
- **Expected impact estimate:** Maintainability only.
- **Removal Safety:** Safe
- **Reuse Scope:** service-wide (`main.py`, `biometric_auth.py`)

### Finding 9 — Chatty per-frame logging/printing inside the authentication hot loop
- **Category:** I/O / Reliability
- **Severity:** Medium
- **Impact:** Per-frame latency and SD-card wear on the deployed Pi
- **Evidence:** `main.py::run_authenticate`'s per-frame body issues multiple `print()` calls every iteration (`main.py:132-146`, `160`, `165`, `168-169`) plus `logger.info/warning` calls from `validate_face_size_and_distance`/`calculate_face_quality_score`/`DecisionGate.update` — all synchronous, and (per `start_face_auth_complete.sh:77`) stdout is redirected to a log file on disk (`python button_trigger_with_rfid.py >> face_auth.log 2>&1`), and `utils.py`'s `logging.basicConfig(filename=LOG_FILE, ...)` writes to a second log file, both unbuffered-by-default text writes.
- **Why it's inefficient:** A loop that's already trying to run at up to ~10-30 attempted FPS is paying for several synchronous line-buffered writes (console + 2 log files) every single frame, on an SD card, in the same thread that's also trying to service the camera and GUI.
- **Recommended fix:** Throttle per-frame logs to state *transitions* only (e.g. log when `is_quality`/`is_match` changes, not every frame) or gate verbose per-frame prints behind a `--verbose` flag; keep the periodic "every 30 frames" debug print pattern already used elsewhere (`main.py:110`) as the model to follow everywhere.
- **Tradeoffs / Risks:** Slightly less granular debugging trail; mitigate by keeping transition-based logs.
- **Expected impact estimate:** Likely small per-frame (single-digit ms) but recurring every frame for the full authentication window — worth confirming with the profiler run in the Validation Plan before/after.
- **Removal Safety:** Likely Safe
- **Reuse Scope:** local file (`main.py`), pattern applies wherever similar per-frame logging exists

### Finding 10 — Fixed `time.sleep(0.03)` added on top of already-slow per-frame processing
- **Category:** CPU / Latency
- **Severity:** Low-Medium
- **Impact:** Adds a constant latency tax regardless of how long recognition actually took
- **Evidence:** `main.py:228` (`time.sleep(0.03)` at the end of the main auth loop) and similarly in the status-display loops (Finding 8). Given that HOG detection + face encoding + (optionally) a DeepFace call already take well more than 30ms on a Pi, this sleep is added on top of the real processing time rather than being an elapsed-time-aware frame-rate cap.
- **Why it's inefficient:** It's dead weight when the loop is already detection-bound, and it's the wrong tool if the intent was frame-rate limiting (it doesn't account for time already spent).
- **Recommended fix:** Either remove it (letting the loop run as fast as detection allows) or replace with an elapsed-time-aware throttle: `target_dt = 1/target_fps; sleep(max(0, target_dt - elapsed))`.
- **Tradeoffs / Risks:** None significant; if removed, verify camera driver doesn't need the small yield to avoid buffer contention.
- **Expected impact estimate:** Small (30ms/frame) but compounds over a multi-second authentication attempt.
- **Removal Safety:** Likely Safe
- **Reuse Scope:** local file

### Finding 11 — `GPIOLock.unlock()` blocks its caller for the entire unlock duration via `time.sleep`
- **Category:** Concurrency / Reliability
- **Severity:** Low-Medium
- **Impact:** Whatever thread calls `unlock()` is frozen for `LOCK_UNLOCK_DURATION` (default 5s)
- **Evidence:** `gpio_lock.py:82-129` — `unlock()` sets the pin high, then `time.sleep(self.unlock_duration)` (line 102), then re-locks, all before returning. Called from `BiometricAuth.unlock_lock` (`biometric_auth.py:417-440`) and from `button_trigger_with_rfid.py::unlock_via_rfid`/`unlock_via_face_recognition`.
- **Why it's inefficient:** In the current one-shot-then-exit `auth` flow this happens to be harmless (nothing else needs the thread afterward), but in the button-trigger daemon it means the process is unresponsive to a new button press or RFID scan for the full unlock window — currently masked by the cooldown logic, but it's a blocking primitive standing in for what should be a timer.
- **Recommended fix:** Set the pin high immediately, schedule the re-lock via `threading.Timer(unlock_duration, self._set_locked_state).start()`, and return immediately.
- **Tradeoffs / Risks:** Must guard against overlapping unlock calls re-arming/canceling timers incorrectly (e.g. a second unlock while the first timer is pending should reset the timer, not stack two).
- **Expected impact estimate:** Restores responsiveness during the unlock window once the daemon architecture (Finding 1) is in place; low value in isolation under the current subprocess-per-attempt model.
- **Removal Safety:** Needs Verification
- **Reuse Scope:** module (`gpio_lock.py`), consumers in `biometric_auth.py` and `button_trigger_with_rfid.py`

### Finding 12 — "Load authorized users from training dir" block duplicated
- **Category:** Code Reuse
- **Severity:** Low
- **Impact:** Maintainability
- **Evidence:** `main.py:54-60` (`run_authenticate`) and `main.py:316-321` (`run_continuous_monitoring`) both do `for person_dir in training_dir.iterdir(): if person_dir.is_dir(): auth.add_authorized_user(...)`.
- **Why it's inefficient:** Small, but it's the kind of two-line divergence that accumulates; also candidate to move onto `BiometricAuth.__init__` itself (auto-load authorized users at construction) so callers can't forget it.
- **Recommended fix:** Extract `load_authorized_users(auth)` helper, or better, do it inside `BiometricAuth.__init__`.
- **Tradeoffs / Risks:** None.
- **Expected impact estimate:** Maintainability only.
- **Removal Safety:** Safe
- **Reuse Scope:** local file (`main.py`)

### Finding 13 — Dead code: unused `_recognize_face` method and `draw_bounding_box` import
- **Category:** Dead Code
- **Severity:** Low
- **Impact:** Code clutter / bundle-not-applicable but still maintenance surface
- **Evidence:** `grep -rn "_recognize_face\b"` across the repo shows only the definition at `face_recognizer.py:164-194`, no call sites (the live path uses `_recognize_face_with_confidence`, `face_recognizer.py:196-228`). `draw_bounding_box` (`utils.py:42-85`) is imported at `face_recognizer.py:10` but only referenced inside a commented-out block (`face_recognizer.py:246-250`).
- **Why it's inefficient:** Dead code increases the surface area a future reader/reviewer has to reason about, and the commented-out "alternative approach" block is stale clutter.
- **Recommended fix:** Delete `_recognize_face` (Counter-vote-based matcher, superseded by the confidence-based version), delete the unused `draw_bounding_box` import and the commented-out PIL block; if `draw_bounding_box` itself has no other callers repo-wide, remove it from `utils.py` too.
- **Tradeoffs / Risks:** Low — double-check no external script/notebook outside this repo imports these before deleting.
- **Expected impact estimate:** N/A (cleanliness).
- **Removal Safety:** Safe (verified no call sites via repo-wide grep)
- **Reuse Scope:** local file (`face_recognizer.py`)

### Finding 14 — Likely-unused heavy dependency: `torch` in `requirements.txt`
- **Category:** Cost / Dead Code
- **Severity:** Low (flagged as **likely**, needs verification)
- **Impact:** Install size/time, disk footprint on a Pi's SD card
- **Evidence:** `requirements.txt` lists `torch==2.5.1`. No file in the repo does `import torch` (`grep -rn "import torch"` returns nothing). `pip show deepface`'s declared dependencies are `fire, Flask, flask-cors, gdown, gunicorn, keras, mtcnn, numpy, opencv-python, pandas, Pillow, requests, retina-face, tensorflow, tqdm` — no `torch`. `tf-keras` is also pinned, suggesting DeepFace here is configured to run on its TensorFlow/Keras backend, not PyTorch.
- **Why it's inefficient:** PyTorch is a large package (several hundred MB with CUDA-less CPU wheels still being sizeable); if truly unused, it costs install time, SD-card space, and Pi provisioning time for zero runtime benefit.
- **Recommended fix:** Run `pip show -f torch` in the actual `facerecogenv` environment (not available in this checkout) to confirm nothing pulls it in transitively, then remove it from `requirements.txt` if confirmed unused.
- **Tradeoffs / Risks:** If some transitive dependency does lazily import torch (e.g. a `mtcnn`/`retina-face` code path DeepFace could switch to), removing it could break that unused-but-latent path — low risk given the pinned `detector_backend="opencv"` usage throughout this codebase.
- **Expected impact estimate:** Install/provisioning time and disk savings only; no runtime perf change expected.
- **Removal Safety:** Needs Verification
- **Reuse Scope:** service-wide (`requirements.txt`)

### Finding 15 — `encode_known_faces()` walks the training directory twice — ✅ FIXED
- **Category:** I/O
- **Severity:** Low
- **Impact:** Minor extra directory traversal, and it's the wrong denominator to begin with (see Finding 3)
- **Evidence:** `face_encoder.py:33` (`total_files = sum(1 for _ in TRAINING_DIR.glob("*/*"))`) followed immediately by `face_encoder.py:36` (`for filepath in TRAINING_DIR.glob("*/*"):`) — two separate filesystem globs purely to get a progress-log denominator.
- **Why it's inefficient:** Two directory listings where one (`list(...)`, then `len(...)` and iterate the list) would do.
- **Recommended fix:** `files = list(TRAINING_DIR.glob("*/*")); total_files = len(files); for filepath in files: ...`.
- **Tradeoffs / Risks:** None; materializing the list is trivial for realistic corpus sizes.
- **Expected impact estimate:** Negligible standalone; worth folding into the Finding 3 fix.
- **Removal Safety:** Applied (Safe)
- **Outcome:** Fixed at `face_encoder.py:32-37` — single walk with `files = [f for f in TRAINING_DIR.glob("*/*") if f.is_file()]`, `total_files = len(files)`, iterate `files`. Folded the pre-existing `is_file()` filter into the list comprehension itself (previously applied inside the loop body), which as a side effect makes `total_files` a slightly more accurate denominator — it now excludes non-file glob matches instead of counting them. Syntax-checked with `py_compile`.
- **Reuse Scope:** local file (`face_encoder.py`)

### Finding 16 — `HeadPoseDetector`'s MediaPipe `FaceMesh` is never closed
- **Category:** Memory / Reliability
- **Severity:** Low
- **Impact:** Native resource retained for process lifetime
- **Evidence:** `head_pose_detector.py:26` creates `self.face_mesh = self.mp_face_mesh.FaceMesh(...)`; no `.close()` call exists anywhere in the class or its callers (`guided_registration.py`, `head_pose_demo.py`).
- **Why it's inefficient:** Under the current subprocess-per-run model this is mostly harmless (the whole process exits and reclaims everything), but if Finding 1's daemon refactor lands and creates/discards `HeadPoseDetector`/`GuidedRegistration` instances repeatedly within one long-lived process (e.g. multiple guided-registration sessions), this becomes a real per-session native-resource leak.
- **Recommended fix:** Add a `close()`/`__del__` or context-manager (`__enter__`/`__exit__`) on `HeadPoseDetector` that calls `self.face_mesh.close()`, and call it when a registration session ends.
- **Tradeoffs / Risks:** None.
- **Expected impact estimate:** Low today; becomes relevant only after Finding 1's architecture change — flag as a follow-up to that work, not urgent standalone.
- **Removal Safety:** Safe
- **Reuse Scope:** module (`head_pose_detector.py`)

### Finding 17 — Guided registration doesn't use the frame-skip cache already built for head pose — ✅ FIXED
- **Category:** CPU / Reuse Opportunity
- **Severity:** Low
- **Impact:** Guided registration's capture loop runs MediaPipe FaceMesh on every frame
- **Evidence:** `HeadPoseDetector.get_head_pose_simple(frame, skip_frames=0)` supports reusing the last result for `skip_frames` out of every `skip_frames+1` frames (`head_pose_detector.py:230-244`), and `head_pose_demo.py:32` already uses it (`skip_frames=skip_frames`, default 1). But `guided_registration.py:260` called `self.head_pose_detector.get_head_pose_simple(frame)` with no argument, i.e. `skip_frames=0` — full MediaPipe inference every single frame of the capture loop.
- **Why it's inefficient:** The exact optimization this system already has for exactly this workload (real-time head-pose feedback in a UI loop) isn't applied to the busier of its two call sites.
- **Recommended fix:** Pass `skip_frames=1` (or a config constant) in `guided_registration.py:260`, matching the demo's default.
- **Tradeoffs / Risks:** Slightly staler pose feedback between processed frames (imperceptible at `skip_frames=1` given typical frame rates); the stability-timing logic (`pose_stable_time` accumulation at `guided_registration.py:304-315`) re-reads `pose_result["face_detected"]`/`["pose_label"]` fresh every loop iteration regardless of whether the result was recomputed or cached, so it behaves correctly with a repeated `pose_result` — not yet verified on real hardware with a live camera, only reasoned through statically.
- **Expected impact estimate:** Roughly halves MediaPipe inference calls in the guided-registration loop at `skip_frames=1`.
- **Removal Safety:** Applied (Likely Safe — recommend a quick manual guided-registration run to confirm pose stability/countdown timing still feels correct)
- **Outcome:** Fixed at `guided_registration.py:260` — one-argument change (`skip_frames=1`). Syntax-checked with `py_compile`; not yet exercised with a live camera.
- **Reuse Scope:** local file (`guided_registration.py`)

### Finding 18 — RFID input handling runs two independent polling loops instead of one blocking wait
- **Category:** Concurrency / Cost
- **Severity:** Low
- **Impact:** Minor constant CPU usage from idle polling
- **Evidence:** `button_trigger_with_rfid.py::rfid_input_thread` polls `select.select([sys.stdin], [], [], 0.1)` then additionally `time.sleep(0.01)` every iteration (`button_trigger_with_rfid.py:139-159`), while the separate main `run()` loop polls `process_rfid_input()` then `time.sleep(0.1)` (`button_trigger_with_rfid.py:595-598`) to drain the queue the first thread fills.
- **Why it's inefficient:** Two loops, two sleep cadences, waking up ~10-100 times/second combined just to move data from one thread to another via a `queue.Queue` that already supports blocking waits.
- **Recommended fix:** Have the main loop `self.rfid_input_queue.get(timeout=0.5)` (blocking with timeout) instead of `empty()`-polling every 100ms; this removes one of the two sleep loops entirely.
- **Tradeoffs / Risks:** None; behavior-preserving.
- **Expected impact estimate:** Negligible CPU savings on modern Pi hardware, but simplifies the concurrency model.
- **Removal Safety:** Safe
- **Reuse Scope:** local file (`button_trigger_with_rfid.py`)

---

## 3) Quick Wins (Do First)

Ordered by effort-to-impact ratio — all are small, localized diffs:

1. **Finding 4** — ✅ Done. Swapped/added `detector_backend="skip"` at the 4 pre-cropped DeepFace call sites (`anti_spoofing.py:146`, `anti_spoofing.py:199`, `biometric_auth.py:105-109`, `biometric_auth.py:225-231`). Still needs a live/spoofed-footage check on real hardware before trusting it in production (see Finding 4's Outcome note).
2. **Finding 17** — ✅ Done. Passed `skip_frames=1` in `guided_registration.py:260`.
3. **Finding 15** — ✅ Done. Collapsed the double `glob` in `face_encoder.py:33-36` into a single list walk.
4. **Finding 12** — extract the duplicated authorized-users-loading block (`main.py:54-60` / `main.py:316-321`).
5. **Finding 13** — delete dead `_recognize_face` method and unused `draw_bounding_box` import/commented block.
6. **Finding 10** — remove or fix the flat `time.sleep(0.03)` in `main.py:228` to be elapsed-time-aware.
7. **Finding 18** — switch the RFID main loop from `empty()`-polling to a blocking `queue.get(timeout=...)`.
8. **Finding 14** — run `pip show -f torch` in the real environment and drop it from `requirements.txt` if confirmed unused.

## 4) Deeper Optimizations (Do Next)

Larger, higher-value refactors that need more care/testing:

1. **Finding 1** — daemonize the button-trigger process; stop `subprocess.run`-ing a full Python re-exec per button press. Biggest expected win; needs a supervisor story (systemd unit) and careful camera/GPIO lifecycle handling.
2. **Finding 2** — route `main.py::run_authenticate` through `BiometricAuth.authenticate()`, reconciling `DecisionGate`'s sliding-window voting with `BiometricAuth`'s consecutive-match voting into one implementation. Do this alongside Finding 1 since the daemon refactor will be touching this same call path anyway.
3. **Finding 5** — extract one shared anti-spoofing filter method, resolving the `all()`/`any()` divergence as an explicit decision.
4. **Finding 3** — add an incremental `append_face` encoding path to `FaceEncoder`, reserving full `encode_known_faces()` re-scans for the explicit `train` command.
5. **Finding 6 + 7** — merge the two drawing functions in `utils.py` into shared primitives, and fix the per-face full-frame copy while touching that code.
6. **Finding 8** — extract the shared `show_status_screen` helper used 6 times across `main.py`/`biometric_auth.py`.
7. **Finding 11** — replace `GPIOLock.unlock()`'s blocking `time.sleep` with a `threading.Timer`-based re-lock, once the daemon (Finding 1) makes responsiveness during the unlock window actually matter.
8. *(Likely, needs profiling to confirm before investing)* — investigate whether HOG face detection itself (not just anti-spoofing) is the dominant per-frame cost; if so, consider a lightweight tracker (e.g. OpenCV `TrackerKCF`/`CSRT` or simple centroid tracking) to avoid running full HOG detection on every frame once a face has been located, re-running full detection only periodically or on tracking loss.

## 5) Validation Plan

No automated tests exist in this repo today (`find . -name "test_*"` / `*_test.py` returns nothing except the standalone `test_lock.py` hardware-cycling script). Recommended validation, roughly in the order the fixes above would land:

- **Latency benchmark (Finding 1 + 2):** Wrap the `subprocess.run` call in `button_trigger_with_rfid.py` with `time.perf_counter()` before/after the daemonization change; run 10 button-press trials on the actual Pi, report p50/p90 time-to-unlock-decision. Expect this to drop from "several seconds" to sub-second-to-low-seconds range.
- **Profiling (Finding 4, 9, 10):** `python -m cProfile -o auth.prof -m src.main auth --anti-spoofing`, then inspect with `pstats`/`snakeviz` to confirm the relative split between dlib detection, face encoding, and DeepFace inference — use this to confirm Finding 4's expected impact rather than assuming it.
- **FPS counter (Finding 2, 10):** Add a simple frames-processed-per-second counter to `run_authenticate`'s loop (temporary instrumentation, or reuse the pattern already in `CameraHandler.show_preview`'s FPS calculation), compare before/after moving to the threaded `BiometricAuth` pipeline.
- **Registration scaling (Finding 3):** Time `encode_known_faces()` with a corpus of 10 vs. 100 training images to demonstrate the current linear-per-registration cost, then confirm the incremental path is O(1) w.r.t. corpus size by timing `append_face` at both corpus sizes.
- **Anti-spoofing accuracy regression (Finding 4, 5):** Before/after the `detector_backend="skip"` change and the `all()`/`any()` consolidation, run a fixed set of known-live and known-spoofed sample images/frames through `AntiSpoofing` and confirm the real/fake classification is unchanged (or is the intentionally-chosen new behavior for Finding 5).
- **Visual regression (Finding 6, 7):** Diff rendered frames (pixel or perceptual hash) from `draw_recognition_feedback_on_frame`/`draw_enhanced_anti_spoofing_feedback` before/after the refactor on a handful of fixture frames with known bounding boxes.
- **Security scenario re-check (Finding 2, 5):** Re-run the "Security Testing Scenarios" already documented in `README.md` (face too far/close/edge, poor quality) manually against the consolidated authentication path to confirm behavior matches the documented expectations.
- **Metrics to compare, before/after, as a checklist:** time-to-unlock-decision (p50/p90), frames processed per second during an auth attempt, `encode_known_faces`/`append_face` wall time vs. corpus size, install size (`du -sh facerecogenv`) if `torch` is removed.

## 6) Optimized Code / Patch (Illustrative — Not Applied)

Per instructions, nothing below has been applied to the repository; these are proposed diffs for the quick wins to make the fixes unambiguous.

**Finding 4 — stop DeepFace re-detecting pre-cropped faces**
```python
# anti_spoofing.py, check_face_region() and process_frame()
# Before:
face_objs = DeepFace.extract_faces(
    img_path=resized_face,
    anti_spoofing=True,
    enforce_detection=False,
    detector_backend="opencv"  # Faster for Pi
)
# After:
face_objs = DeepFace.extract_faces(
    img_path=resized_face,
    anti_spoofing=True,
    enforce_detection=False,
    detector_backend="skip"  # Already a face crop from face_recognition — don't re-detect
)
```
Apply the same substitution at `biometric_auth.py:106` and `biometric_auth.py:226` (both operate on `face_img = frame_copy[top:bottom, left:right]`, i.e. an already-cropped face).

**Finding 17 — use the existing frame-skip cache in guided registration**
```python
# guided_registration.py:260
# Before:
pose_result = self.head_pose_detector.get_head_pose_simple(frame)
# After:
pose_result = self.head_pose_detector.get_head_pose_simple(frame, skip_frames=1)
```

**Finding 15 — single directory walk**
```python
# face_encoder.py:33-36
# Before:
total_files = sum(1 for _ in TRAINING_DIR.glob("*/*"))
processed = 0
for filepath in TRAINING_DIR.glob("*/*"):
# After:
files = [f for f in TRAINING_DIR.glob("*/*") if f.is_file()]
total_files = len(files)
processed = 0
for filepath in files:
```

**Finding 12 — deduplicate authorized-user loading**
```python
# main.py — new helper, replaces the block duplicated at lines 54-60 and 316-321
def _authorize_all_registered_users(auth: BiometricAuth) -> None:
    training_dir = TRAINING_DIR
    if not training_dir.exists():
        return
    for person_dir in training_dir.iterdir():
        if person_dir.is_dir():
            auth.add_authorized_user(person_dir.name)
            print(f"Authorized user: {person_dir.name}")

# call sites become:
_authorize_all_registered_users(auth)
```

**Finding 3 — incremental encoding sketch**
```python
# face_encoder.py — new method alongside encode_known_faces()
def append_face(self, image_path: Path, name: str) -> bool:
    """Encode a single new image and append to the existing encodings DB,
    instead of re-scanning the entire training corpus."""
    try:
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image, model=self.model)
        face_encodings = face_recognition.face_encodings(image, face_locations)
    except Exception as e:
        logger.error(f"Error encoding {image_path}: {e}")
        return False

    if not face_encodings:
        logger.warning(f"No face found in {image_path}, skipping")
        return False

    db = self.load_encodings()  # {"names": [...], "encodings": [...]}
    for encoding in face_encodings:
        db["names"].append(name)
        db["encodings"].append(encoding)
    self._save_encodings(db["names"], db["encodings"])
    logger.info(f"Appended {len(face_encodings)} encoding(s) for {name} without full re-scan")
    return True
```
`register_person_from_camera` and `GuidedRegistration`'s completion handler would call `append_face` once per captured image (or in a small batch) instead of `encode_known_faces()`; the `train` CLI command keeps calling `encode_known_faces()` for an explicit full rebuild.

---

*End of audit. No source files were modified as part of producing this document, per instructions.*
