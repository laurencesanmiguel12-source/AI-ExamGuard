# new_dataset (Desktop/new_dataset) — annotation + retrain/re-validation results

Date: 2026-09-08. 15 webcam `.mp4` clips → 2224 frames extracted at ~1 fps
(`datasets/new_video/frames/`, `manifest.json`).

## What's in it

6 distinct people across ~5 rooms / lighting conditions (visually identified):

| id | clips | content |
|----|-------|---------|
| p1 | `1788827228145881 / …147403 / …147533` | man, beige wall — phones (white/blue/green) at ear/face/chest; **draft labels FN-heavy on held-low phones → dropped from training** |
| p2 | `WIN_20260907_17_56_50`, `WIN_20260908_08_30_06`, `…08_32_05` | young man, guitar room — phone near face + two pure head-down clips |
| p3 | `WIN_20260908_01_55_53 / 01_59_07 / 02_04_42 / 02_07_53` | girl, TV room — mostly head-down, incl. extreme tilt |
| p4 | `WIN_20260907_23_46_13` | young man, pink shirt — phone in hand near-continuous |
| p5 | `Copy_of_WIN_20260907_23_45_14` | girl — phone in hand + eyes down, whole clip |
| p6 | `WIN_20260908_01_45_12 / 01_48_26 / 01_51_53` | girl, bedroom — phone + head-down |

## Annotation

`annotate_new_video.py` — loose two-model phone pass (base COCO cls 67 ∪ `phone_specialist.pt` @0.15)
+ YuNet faces @0.6 + production's validated face-anchored IoU-suppression (0.45). YOLO labels
written next to every frame (0=phone, 1=face); real production head-pose pitch per frame in
`head_pose.csv`. 967/2224 frames got a draft phone box.

Reviewed via box-overlay contact sheets. Draft quality: **near-perfect on the phone-heavy clips**
(p4, p5 — box tracks the real phone every frame), **good** on p2/p6, **FN-heavy on p1** (misses
held-low white phones). Only cleanup needed: ~10 bottom-edge desk/monitor strip FP boxes in p3's
clips (dropped by `build_new_video_dataset.py`).

Discipline note: this is an AI-assisted visual-review substitute for a manual LabelImg pass, same
as the personal-video batch — not literal box-by-box hand review. See
`ai_examguard_phone_detection_personal_video_labeling`.

## Phone detection

### New multi-person holdout (the durable asset)

`datasets/new_video/holdout/` = p4 + p5, 365 frames (363 phone-positive), **never** in `data.yaml`.
The frozen holdout has no lighting/hardware diversity within one session (it missed the 0.70-threshold
live-recall crash). This set is 2 unseen people on their own webcams — it measures recall /
generalization. `evaluate_new_video_holdout.py` runs the full production pipeline at 0.35.

Baseline, current production `phone_specialist.pt` (phone_face_specialist-7):
**recall 0.972 (353/363), FP 0/2** — p4 0.969 (186/192), p5 0.977 (167/171).
The deployed model is already very strong on this in-hand / near-face footage (only 10 FN in 363);
the frozen holdout's harder backface/dim cases are where its recall actually sits at 0.792.

### Retrain candidate — phone_face_specialist-13 — NOT YET RUN (machine memory)

Training set += `datasets/new_video/split/train/` = p2 + p3 + p6, stride-2 sampled, 815 frames
(239 phone-positive). Stride-sampled + multi-person specifically to avoid the single-context
over-representation that regressed the two personal-video retrains. p1 excluded (labels), p4/p5
held out. `data.yaml` train list already has the 3rd path appended.

**Status 2026-09-08:** two attempts to run `finetune_phone_face.py --epochs 8 --batch 8
--imgsz 416` were killed — the first by operator error (killed its dataloader workers), the second
by the OS at epoch 2 (host low on RAM; the 8-worker dataloader + torch don't fit alongside
everything else). Epoch 1 alone gave val P/R/mAP50 = 0.63 / 0.70 / 0.67 — undertrained, not a
usable candidate. Run it when the machine is otherwise idle, with fewer workers:

```
cd backend/training
../../.venv/Scripts/python.exe finetune_phone_face.py --epochs 8 --batch 8 --imgsz 416 --workers 2
```

| metric | production baseline | candidate -13 | verdict |
|--------|--------------------|---------------|---------|
| frozen holdout presence P / R / F1 (**corrected labels**) | 0.915 / 0.987 / **0.949** | 0.882 / 0.987 / **0.932** | identical recall, worse precision |
| frozen holdout FP (246 neg) | **7** | **10** | +3 false positives, no gain |
| new_video holdout recall (363 pos) | 0.972 | **0.981** | +0.9 pt (already at ceiling) |

> The pre-correction figures (prod 0.927/0.792/0.854 vs -13 0.882/0.781/0.829) are superseded — the
> holdout carried 41 mislabeled boxes on the OEP rig's own second camera. See
> `fix_frozen_holdout_device_labels.py` and the frozen-holdout memory. On honest labels the two
> models miss the *same single frame*; the entire difference is 3 extra false positives.

**Outcome (2026-09-08): NOT swapped — negative result, same as the two prior retrains.**
Candidate -13 finished all 8 epochs (resumed once from an epoch-5 checkpoint after two OS OOM
kills). It regressed the frozen holdout — the binding gate — on precision, recall, F1, and FP
count, in exchange for a marginal +0.9 pt on a new-holdout recall that was already 97%. Production
`phone_specialist.pt` (phone_face_specialist-7) is unchanged. The `datasets/new_video/split/train`
path was removed from `data.yaml`. The `runs/phone_face_specialist-13/` weights are kept on disk
(gitignored) for reference. The new_video **holdout** and the annotation scripts remain the
lasting deliverable; the retrain does not.

**Swap rule:** replace `app/resources/phone_specialist.pt` only if the frozen holdout does **not**
regress (P/R/F1 ≥ baseline, FP ≤ 6) AND new_video holdout recall improves. Otherwise keep
production and record the negative result — same gate the last two retrains failed. Given the
baseline already scores 0.972 on the new holdout (10 FN in 363), expectations for a recall gain
here are modest; the real question is whether the added multi-person real-webcam frames move the
frozen holdout at all without regressing it.

### Resume commands (training run `bj2iopfl9` → `runs/phone_face_specialist-13/`)

```
cd backend/training
../../.venv/Scripts/python.exe evaluate_frozen_holdout.py   --model runs/phone_face_specialist-13/weights/best.pt   # run ONCE
../../.venv/Scripts/python.exe evaluate_new_video_holdout.py --model runs/phone_face_specialist-13/weights/best.pt
# then compare to the baseline row above and apply the swap rule.
# to swap:  copy runs/phone_face_specialist-13/weights/best.pt -> backend/app/resources/phone_specialist.pt
#           then re-run both evals against the copied file + `python -m app.services.object_detection_service` self-check.
# if NOT swapping (holdout regressed): revert the 3rd path added to datasets/phone-face-yolo/data.yaml
#           train list so future runs don't silently include new_video.
```

## Head-down (PROLONGED_HEAD_DOWN) — re-validation

`analyze_head_down_new_video.py`, video-level behaviour labels from direct visual review (not the
model's own pitch, so not circular). Live threshold `HEAD_DOWN_PITCH_THRESHOLD_DEGREES = -35`.

| clip(s) | behaviour | pitch p50 | YuNet drop | fallback=head-present on drops | %≤−35 |
|---------|-----------|-----------|------------|-------------------------------|-------|
| p2 `08_30_06` | attentive at screen | −13° | 0% | — | 0% |
| p2 `08_32_05` | deep head-down | −42° | 99% | **99%** | 100% |
| p3 `02_07_53` | deep head-down | −37° | 89% | **100%** | 55% |
| p5 `Copy…23_45_14` | phone in hand, **eyes** down, head level | −13° | 1% | — | 1% |
| p3 `02_04_42` | normal screen-reading, low webcam | **−49°** | 0% | — | **78%** |

Findings:

1. **No drift.** Attentive posture on fresh 2026-09 hardware sits at −13° p50, clear of −35°. No
   false-positive pressure from normal screen gaze on that setup.
2. **Fallback path validated.** Genuine deep head-down drops YuNet ~90–99% of the time; on those
   frames the pose fallback reports head-present 99–100% → the head-down streak is sustained
   through the blackout and `PROLONGED_HEAD_DOWN` still fires. This is the load-bearing mechanism
   for deep head-down and it holds up on new data.
3. **Ceiling confirmed, with fresh exemplars:**
   - **FN — p5:** covert phone use with head near-level / eyes down reads −13° (identical to
     attentive). No pitch cut separates it from "attentive at screen." Only the phone detector
     catches this case (it does — draft saw p5's phone in 171/171 frames).
   - **FP — p3 `02_04_42`:** normal reading posture on a low webcam reads −49° p50, 78% of frames
     past −35°. Any threshold ≥ −50 flags this student; −50 kills real recall elsewhere. The 25 s
     duration gate + mandatory human review is the only real mitigation — which is the existing
     design.
4. **Soft signal, not actioned:** on the thin set of deep-head-down frames that keep a pitch (n=21)
   + all attentive frames (n=92), −30° scored F1 0.83 / precision 1.00 / recall 0.71 vs −35° at
   F1 0.73 / recall 0.57 — zero FP either way. Filed as "worth a wider-data look + live smoke-test"
   per this project's threshold-change discipline; **not changed** on n=21.

**Verdict:** calibration re-validated on fresh multi-person data, fallback path confirmed working.
No threshold change recommended. Matches and strengthens the existing
`ai_examguard_gaze_monitoring_feasibility` conclusion: head pitch is a bounded proxy; the duration
gate and human review do the real work.
