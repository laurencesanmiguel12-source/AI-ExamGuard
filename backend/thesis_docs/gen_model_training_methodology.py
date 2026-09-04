"""One-off script generating the Model Training Methodology chapter PDF - how each trained model
was preprocessed, trained, scored (F1 in particular), tested and validated. Not part of the app -
a docs-generation utility only, same convention as gen_related_literature.py / gen_diagrams.py.

Every number below was read out of this repository (training scripts, runs/*/results.csv,
runs/*/args.yaml, dataset directories, app/resources/risk_model.joblib) or out of the project's
recorded experiment log - none are illustrative or invented. Where a number is in-sample,
proxy-derived, or otherwise weaker evidence than it looks, the text says so in place.

The embedded figures are Ultralytics' own plots from the production training run. That run's
directory (backend/training/runs/) is GITIGNORED, so on a fresh clone the figures are absent -
missing ones are skipped with a warning rather than crashing the build, and the PDF still
generates. Re-run the training to regenerate them.

Usage: ../../.venv/Scripts/python.exe gen_model_training_methodology.py
"""
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                Table, TableStyle, Image, KeepTogether)

OUT_FILE = "AI_ExamGuard_Model_Training_Methodology.pdf"

# The production detector run - verified by MD5 to be the source of the deployed
# app/resources/phone_specialist.pt. Gitignored; see module docstring.
RUN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "training", "runs", "phone_face_specialist-7")

styles = getSampleStyleSheet()
title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=20, leading=25, spaceAfter=6)
subtitle_style = ParagraphStyle("SubtitleX", parent=styles["Normal"], fontSize=13, leading=17,
                                alignment=TA_CENTER, textColor="#334155", spaceAfter=4)
meta_style = ParagraphStyle("MetaX", parent=styles["Normal"], fontSize=10, leading=14,
                            alignment=TA_CENTER, textColor="#64748b")
h1_style = ParagraphStyle("H1X", parent=styles["Heading1"], fontSize=15, leading=19,
                          spaceBefore=18, spaceAfter=8, textColor="#0f172a")
h2_style = ParagraphStyle("H2X", parent=styles["Heading2"], fontSize=12, leading=16,
                          spaceBefore=12, spaceAfter=6, textColor="#1e293b")
body_style = ParagraphStyle("BodyX", parent=styles["Normal"], fontSize=10.3, leading=15.5,
                            alignment=TA_JUSTIFY, spaceAfter=9)
bullet_style = ParagraphStyle("BulletX", parent=body_style, leftIndent=16, bulletIndent=4,
                              spaceAfter=5)
code_style = ParagraphStyle("CodeX", parent=styles["Normal"], fontName="Courier", fontSize=8.6,
                            leading=11.6, leftIndent=14, spaceBefore=4, spaceAfter=9,
                            textColor="#0f172a", backColor="#f1f5f9", borderPadding=6)
caption_style = ParagraphStyle("CapX", parent=styles["Normal"], fontSize=8.8, leading=12,
                               textColor="#64748b", spaceAfter=12)

TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.8),
    ("LEADING", (0, 0), (-1, -1), 11.5),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
])

story = []


def h1(text):
    story.append(Paragraph(text, h1_style))


def h2(text):
    story.append(Paragraph(text, h2_style))


def p(text):
    story.append(Paragraph(text, body_style))


def bullets(items):
    for item in items:
        story.append(Paragraph(item, bullet_style, bulletText="•"))
    story.append(Spacer(1, 4))


def code(text):
    story.append(Paragraph(text.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))


def figure(filename, caption, width=6.1 * inch):
    """Embed one of the training run's plots, scaled to `width` with aspect ratio preserved.
    A missing file is skipped with a warning (runs/ is gitignored - see module docstring), so a
    fresh clone still builds a complete document minus the figures."""
    path = os.path.join(RUN_DIR, filename)
    if not os.path.isfile(path):
        print(f"  SKIPPING figure {filename} - not found at {path}")
        return
    img = Image(path)
    img.drawWidth = width
    img.drawHeight = width * img.imageHeight / img.imageWidth
    img.hAlign = "CENTER"
    story.append(KeepTogether([Spacer(1, 4), img, Spacer(1, 5),
                               Paragraph(caption, caption_style)]))


def table(rows, widths, caption=None):
    cells = [[Paragraph(c, ParagraphStyle(
        "cell", parent=styles["Normal"], fontSize=8.8, leading=11.5,
        fontName="Helvetica-Bold" if r == 0 else "Helvetica")) for c in row]
        for r, row in enumerate(rows)]
    t = Table(cells, colWidths=widths, repeatRows=1)
    t.setStyle(TABLE_STYLE)
    story.append(t)
    if caption:
        story.append(Spacer(1, 4))
        story.append(Paragraph(caption, caption_style))
    else:
        story.append(Spacer(1, 12))


# ---------------------------------------------------------------- Title page
story.append(Spacer(1, 1.5 * inch))
story.append(Paragraph("Model Training Methodology", title_style))
story.append(Paragraph("Preprocessing, Training, Evaluation, and Validation", subtitle_style))
story.append(Spacer(1, 0.3 * inch))
story.append(Paragraph(
    "AI ExamGuard: An AI-Assisted Online Examination Proctoring and "
    "Academic Integrity Monitoring System", meta_style))
story.append(Spacer(1, 0.25 * inch))
story.append(Paragraph(
    "All figures in this chapter were read directly from the project's training scripts, "
    "training-run artifacts, dataset directories, and serialized production models. "
    "In-sample, proxy-derived, and negative results are labeled as such where they appear.",
    meta_style))
story.append(PageBreak())

# ---------------------------------------------------------------- 1. Overview
h1("1. Overview of the Trained Components")

p("AI ExamGuard runs three <b>trained</b> machine-learning components and three <b>pretrained, "
  "unmodified</b> ones. Only the first group was trained by this project; the second group is used "
  "as shipped and is documented here so the boundary between 'what we trained' and 'what we "
  "reused' is unambiguous.")

table([
    ["Component", "Algorithm / architecture", "Trained by this project?", "Artifact"],
    ["Phone + face detector",
     "YOLOv8s object detector, fine-tuned from COCO weights",
     "Yes - transfer learning, 8 epochs",
     "app/resources/phone_specialist.pt"],
    ["Face identity verification",
     "LBPH (Local Binary Patterns Histograms) face recognizer",
     "Yes - one model fitted per enrolled student at enrollment time",
     "backend/storage/&lt;student_id&gt;.yml"],
    ["Risk scorer",
     "Logistic regression over three windowed detection counts",
     "Yes - fitted on real cheat-event ground truth",
     "app/resources/risk_model.joblib"],
    ["Face detector",
     "OpenCV YuNet (ONNX), used as published",
     "No - pretrained, unmodified",
     "app/resources/face_detection_yunet_2023mar.onnx"],
    ["Person counter",
     "YOLOv8s COCO baseline, deliberately never fine-tuned",
     "No - see 4.1 for why it must stay untouched",
     "app/resources/yolov8s.pt"],
    ["Pose estimator",
     "YOLOv8n-pose, used as published (wrist and nose keypoints only)",
     "No - pretrained, unmodified",
     "app/resources/yolov8n-pose.pt"],
], [1.15 * inch, 1.75 * inch, 1.7 * inch, 1.9 * inch],
    "Table 1. The six model artifacts in the deployed pipeline. Sections 4-6 cover the three "
    "trained ones; section 7 covers how F1 was computed; section 8 covers testing and validation.")

p("Head-pose estimation (the PROLONGED_HEAD_DOWN signal) is <b>not</b> a trained model at all - it "
  "is a solvePnP geometric estimate computed from YuNet's five sparse facial landmarks. It appears "
  "in this chapter anyway, in 8.4, because its decision thresholds were calibrated with exactly "
  "the same empirical sweep methodology used for the trained models, and because that calibration "
  "produced one of the project's more important negative findings.")

# ---------------------------------------------------------------- 2. Tools
h1("2. Tools, Libraries, and Compute Environment")

table([
    ["Purpose", "Tool / library", "Notes"],
    ["Object-detection training and inference", "Ultralytics YOLOv8 (PyTorch backend)",
     "YOLOv8s for detection, YOLOv8n-pose for keypoints"],
    ["Face detection, cropping, recognition",
     "OpenCV (<font face='Courier'>opencv-contrib-python</font>)",
     "<font face='Courier'>cv2.FaceDetectorYN</font> (YuNet) and "
     "<font face='Courier'>cv2.face.LBPHFaceRecognizer</font>; the contrib build is mandatory - the "
     "plain <font face='Courier'>opencv-python</font> wheel silently removes "
     "<font face='Courier'>cv2.face</font>"],
    ["Risk-model fitting and metrics", "scikit-learn",
     "<font face='Courier'>LogisticRegression</font>, "
     "<font face='Courier'>roc_auc_score</font>, "
     "<font face='Courier'>precision/recall/f1_score</font>"],
    ["Data handling", "pandas, NumPy, Python <font face='Courier'>csv</font>",
     "Window construction, feature tables, bootstrap resampling"],
    ["Model serialization",
     "joblib (risk model), PyTorch <font face='Courier'>.pt</font> (YOLO), "
     "OpenCV <font face='Courier'>.yml</font> (LBPH)", "-"],
    ["Frame extraction", "OpenCV <font face='Courier'>VideoCapture</font>",
     "Webcam-track extraction from the source video corpus"],
    ["Manual annotation", "LabelImg (YOLO-format bounding boxes)",
     "Fed with machine-generated draft boxes, then human-corrected"],
    ["Serving", "FastAPI + Uvicorn, containerized with Docker",
     "Inference is deliberately CPU-only in the deployed image"],
], [1.5 * inch, 1.85 * inch, 3.15 * inch])

p("<b>Training compute.</b> The production detector run used a single local CUDA GPU "
  "(<font face='Courier'>device: '0'</font> in the run's "
  "<font face='Courier'>args.yaml</font>), taking roughly 6,100 seconds of wall-clock time across "
  "8 epochs. The earlier single-class prototype was trained on CPU. <b>Inference in production is "
  "CPU-only by design</b> - the Docker image has no GPU passthrough - so every threshold sweep and "
  "holdout evaluation in this chapter was also run with "
  "<font face='Courier'>device=\"cpu\"</font>, measuring the deployment configuration "
  "rather than a faster one that is never actually served.")

story.append(PageBreak())

# ---------------------------------------------------------------- 3. Data
h1("3. Data Sources and Preprocessing")

h2("3.1 Source corpora")

table([
    ["Corpus", "Content", "Role"],
    ["MSU Online Exam Proctoring (OEP) database",
     "Real proctored online-exam sessions: 15 'actor' subjects instructed to improvise cheating, "
     "9 'real exam' subjects covertly prompted by a proctor. Ships event-level cheat-type "
     "timestamps (<font face='Courier'>gt.txt</font>), no bounding boxes.",
     "Primary real-world source for both the detector (after manual box annotation) and the risk "
     "model (directly from <font face='Courier'>gt.txt</font>)."],
    ["Kaggle <font face='Courier'>samuelayman/cell-phone</font>",
     "Single-class phone bounding boxes.",
     "First-generation prototype detector only; superseded."],
    ["Pre-labeled two-class phone/face set (~22.9k images)",
     "Phone and face boxes, already split train/val/test.",
     "Bulk of the production detector's training data."],
    ["Locally captured 'back-facing phone' batches",
     "Four sequentially shot real-webcam sessions of the hard low-held / screen-away phone poses.",
     "Targeted hard positives and negatives; also the only data that can evaluate "
     "sequence-dependent behavior (8.5)."],
], [1.35 * inch, 3.0 * inch, 2.15 * inch])

h2("3.2 Frame extraction from the OEP videos")

p("Each OEP subject folder holds two synchronized video tracks. Only the <b>webcam</b> track is "
  "extracted; the wearable first-person camera is discarded, because its framing has no "
  "relationship to the laptop-webcam viewpoint the deployed system actually receives at inference "
  "time. Training on it would optimize for a camera geometry the product never sees.")

p("Extraction is also the project's <b>anonymization boundary</b>. The OEP subject folders are "
  "anonymized as <font face='Courier'>subjectNN</font>, but the media filenames inside them encode "
  "each participant's real username. <font face='Courier'>extract_oep_frames.py</font> therefore "
  "never propagates a source filename: output frames are named purely from the subject number and "
  "timestamp, so no real identity ever enters the derived dataset, the annotation batch, or any "
  "artifact in this repository.")

h2("3.3 Frame prioritization and batch assembly")

p("One-frame-per-second extraction produced roughly 9,700 raw frames - far more than can be "
  "annotated by hand, and heavily redundant. "
  "<font face='Courier'>prioritize_oep_frames.py</font> classifies every frame against "
  "<font face='Courier'>gt.txt</font> into <i>phone</i>, <i>other_cheat</i>, or <i>clean</i>, and "
  "<font face='Courier'>build_annotation_batch.py</font> then assembles a bounded, less redundant "
  "annotation folder under a fixed seed:")

bullets([
    "<b>All</b> phone frames are kept. They are the scarce class, and even near-duplicate frames "
    "inside one burst differ in hand and phone position - real variety, not waste.",
    "<i>other_cheat</i> frames are downsampled to roughly twice the phone count, spread "
    "<b>evenly per subject</b> rather than sampled globally, so one long session cannot dominate "
    "the batch.",
    "<i>clean</i> frames are downsampled to roughly 15% of the batch, supplying negatives.",
    "Original filenames are preserved because they encode subject and timestamp, which is what "
    "makes the later leakage-safe per-subject split possible.",
])

h2("3.4 Annotation: machine draft, human ground truth")

p("The OEP corpus has no bounding boxes, so they were created for this project. "
  "<font face='Courier'>auto_annotate_oep.py</font> opens each frame with <b>draft</b> boxes "
  "already drawn - YuNet for faces, and the union of the then-current phone specialist plus the "
  "COCO <i>cell phone</i> class for phones, de-duplicated at IoU 0.5. Draft thresholds are "
  "deliberately <b>looser</b> than production (phone confidence 0.15 vs 0.35; face score 0.6 vs "
  "0.9), because in a draft-then-correct workflow a missed box costs an annotator far more effort "
  "(draw one from scratch) than a spurious one (one click to delete).")

p("Every draft box was then reviewed and corrected by hand in LabelImg. This correction step is "
  "not a formality: the entire reason for building the dataset was that the existing detector had "
  "blind spots, so training a successor on that detector's own uncorrected output would have "
  "taught it to reproduce exactly those blind spots. Frames with a face but no phone were kept as "
  "reviewed real negatives; frames with no boxes at all had an <b>empty label file written "
  "explicitly</b>, so that 'verified as containing nothing' is stored distinctly from 'never "
  "labeled'.")

h2("3.5 Label-defect remediation")

p("A per-subject accuracy breakdown (8.6) flagged three subjects as far below the overall recall. "
  "Visual review of every one of their phone-positive frames found <b>zero genuine phones</b>. The "
  "boxes were the OEP study's own wired eye-tracking camera clipped to the subject's glasses, "
  "background objects, and similar confounders - a labeling defect, not a fairness gap, and one "
  "that agreed exactly with <font face='Courier'>gt.txt</font>, which documents real phone-use "
  "events for only four of the subjects.")

p("Remediation ran in two modes. For the seven subjects with no documented phone use, all "
  "phone-class boxes were stripped after a full visual confirmation (a dry run preceded every "
  "write). For the four subjects with genuine phone use, all 722 phone-positive frames were "
  "reviewed individually rather than blanket-stripped, since those subjects contain a real mixture "
  "of held phones and the same eye-tracker confounder; 114 bogus single-box frames were removed. "
  "Corrections were applied consistently across the annotation batch, the derived train/val split, "
  "and the frozen holdout, so no split kept a stale copy of a corrected label.")

p("One residual defect is recorded rather than papered over: a minority of multi-box frames may "
  "still carry a redundant bogus device box alongside the genuine phone box. These were not "
  "surgically split, and the consequence is handled on the evaluation side instead - the metric "
  "code matches predictions against <b>all</b> ground-truth boxes in a frame, not just the first "
  "one (7.3).")

h2("3.6 Image preprocessing at training and inference")

table([
    ["Model", "Preprocessing applied"],
    ["Phone/face detector (YOLOv8s)",
     "Ultralytics letterbox resize to 416x416, RGB, pixel values scaled to [0,1]. "
     "Training-time augmentation (mosaic, HSV jitter, horizontal flip, translate, scale, random "
     "erasing) is listed in Table 3. <b>No</b> augmentation at inference."],
    ["Face recognition (LBPH)",
     "YuNet detects the largest face, the detection box is cropped, converted from BGR to "
     "grayscale, and resized to exactly 200x200. That size is mandatory, not cosmetic: LBPH's "
     "<font face='Courier'>predict</font> requires the probe to match the enrollment geometry, so "
     "an off-spec client crop is re-resized before it reaches the recognizer."],
    ["Risk model",
     "No image preprocessing. Its inputs are integer counts produced by the vision models above, "
     "aggregated over a sliding time window (6.1)."],
], [1.55 * inch, 4.95 * inch])

story.append(PageBreak())

# ---------------------------------------------------------------- 4. Detector
h1("4. Model A - Phone and Face Detector (YOLOv8s)")

h2("4.1 Why a second model instead of fine-tuning the deployed one")

p("The phone detector is trained as a <b>separate</b> network that runs as a second inference pass "
  "alongside an untouched COCO YOLOv8s. This is a deliberate architectural constraint, not "
  "convenience. The phone datasets contain no <i>person</i> class, and fine-tuning YOLO on them "
  "rebuilds the detection head to emit only the classes present in the new data - which would "
  "silently delete the <i>person</i> class that the MULTIPLE_PEOPLE violation check depends on. "
  "The failure would be silent: the pipeline would keep running and simply stop ever reporting a "
  "second person. Keeping the baseline model untouched makes that failure impossible.")

h2("4.2 Transfer-learning setup")

p("Training starts from the COCO-pretrained YOLOv8s weights and fine-tunes all layers (no frozen "
  "backbone) on the combined two-class dataset. The class ordering is fixed by the dataset's "
  "<font face='Courier'>data.yaml</font> as <font face='Courier'>['phone', 'face']</font>, making "
  "class 0 = phone, which is what the serving code asserts. The face class is a free by-product; "
  "production face detection still runs through YuNet, not through this model - although the face "
  "class did later earn its keep as a false-positive suppressor (4.6).")

table([
    ["Hyperparameter", "Value", "Hyperparameter", "Value"],
    ["Base weights", "yolov8s.pt (COCO)", "Optimizer", "auto (Ultralytics selection)"],
    ["Epochs", "8", "Initial LR (lr0)", "0.01"],
    ["Batch size", "8", "Final LR factor (lrf)", "0.01"],
    ["Image size", "416 x 416", "Momentum", "0.937"],
    ["Nominal batch size (nbs)", "64", "Weight decay", "0.0005"],
    ["Early-stop patience", "8", "Warmup epochs", "3"],
    ["Mixed precision (AMP)", "enabled", "Random seed", "0 (deterministic)"],
    ["Mosaic augmentation", "1.0, closed for last 10 epochs", "Horizontal flip", "0.5"],
    ["HSV jitter (h/s/v)", "0.015 / 0.7 / 0.4", "Translate / scale", "0.1 / 0.5"],
    ["Random erasing", "0.4", "Vertical flip / shear / perspective", "0.0 (disabled)"],
], [1.5 * inch, 1.75 * inch, 1.55 * inch, 1.7 * inch],
    "Table 3. Training configuration of the production detector, transcribed from the run's "
    "<font face='Courier'>args.yaml</font>. Vertical flip is disabled because a webcam feed is "
    "never upside down - allowing it would spend model capacity on an orientation that cannot "
    "occur in deployment.")

p("The production run was interrupted by an external event partway through and was <b>resumed from "
  "its own last checkpoint</b> rather than restarted from epoch 0, which is why the run's recorded "
  "<font face='Courier'>model</font> field points at its own "
  "<font face='Courier'>last.pt</font>. The learning-rate schedule and epoch counter continue "
  "correctly through a resume, so this does not change the effective training recipe.")

h2("4.3 Split strategy: by subject, never by frame")

p("The OEP annotation batch is split into train and validation <b>by subject</b>, with a fixed, "
  "deliberately chosen validation set rather than a random one. Frames from one subject share the "
  "same face, room, camera angle, and lighting, so a per-frame random split would place "
  "near-duplicate frames on both sides of the boundary and inflate validation metrics through "
  "leakage. The two validation subjects were chosen to cover one phone-heavy 'actor' subject and "
  "one 'real exam' subject, so validation retains both genuine phone positives and non-acted "
  "footage. The same subject-level discipline is reused for the risk model (6) and generalized to "
  "leave-one-subject-out cross-validation there.")

table([
    ["Split", "Frames", "Purpose"],
    ["OEP annotation batch (after holdout carve-out)", "2,260", "Source pool for train/val"],
    ["&#160;&#160;train", "1,837", "Gradient updates, combined with the ~22.9k external set"],
    ["&#160;&#160;val (2 held-out subjects)", "423",
     "Training-time model selection and early stopping"],
    ["Frozen holdout", "322",
     "Final accept/reject evidence only - never trained on, never tuned against"],
], [3.2 * inch, 0.85 * inch, 2.45 * inch],
    "Table 4. OEP frame allocation. The external ~22.9k-image corpus contributes its own "
    "publisher-provided train/val split on top of these numbers.")

h2("4.4 Training-time metrics")

p("Ultralytics' own per-epoch validation, computed on the combined validation split at the end of "
  "each epoch:")

table([
    ["Epoch", "Precision (B)", "Recall (B)", "mAP@50", "mAP@50-95", "val box loss"],
    ["6", "0.727", "0.809", "0.790", "0.509", "1.273"],
    ["7", "0.760", "0.859", "0.818", "0.559", "1.226"],
    ["8 (final)", "0.769", "0.867", "0.828", "0.566", "1.224"],
], [0.9 * inch, 1.15 * inch, 1.0 * inch, 0.95 * inch, 1.1 * inch, 1.1 * inch],
    "Table 5. Final epochs of the production run, from its "
    "<font face='Courier'>results.csv</font>. These are <b>aggregate</b> two-class detector metrics "
    "at Ultralytics' own default operating point - they are not the numbers that decided "
    "deployment. That decision was made on the frozen holdout, at the app's real threshold, "
    "through the full production pipeline (section 7).")

figure("results.png",
       "Figure 1. Per-epoch training curves for the production run (Ultralytics "
       "<font face='Courier'>results.png</font>). Top row: training box, classification, and "
       "distribution-focal losses, plus validation precision and recall. Bottom row: the same "
       "three losses measured on validation, plus mAP@50 and mAP@50-95. Two things are worth "
       "reading off it. First, <b>all six loss curves are still descending at epoch 8 and "
       "training and validation losses fall together</b> - there is no divergence between them, "
       "so the run shows no overfitting signature and was ended by its epoch budget rather than "
       "by convergence or early stopping. Second, <b>validation recall is visibly noisy from "
       "epoch to epoch</b>, dipping to 0.808 at epoch 6 before returning to 0.867 at epoch 8. "
       "That per-epoch wobble is larger than several of the margins that had previously been "
       "used to choose between candidate runs, which is a concrete argument for deciding "
       "deployment on the frozen holdout (section 8.1) rather than on epoch-level validation "
       "metrics.")

p("<b>Provenance check.</b> The deployed "
  "<font face='Courier'>app/resources/phone_specialist.pt</font> was verified to be byte-identical "
  "(matching MD5) to this run's <font face='Courier'>weights/best.pt</font>. The metrics and "
  "figures in this chapter therefore describe the artifact that is actually serving traffic, not "
  "a sibling candidate.")

h2("4.5 Per-class performance and error modes")

p("The aggregate mAP in Table 5 averages over two classes that behave quite differently, and the "
  "per-class curves matter because production consumes only one of them:")

figure("BoxPR_curve.png",
       "Figure 2. Precision-recall curves per class on the validation split. <b>The phone class "
       "reaches AP@0.5 = 0.914, the face class only 0.743</b>, averaging to the mAP@0.5 of 0.828 "
       "reported in Table 5. The stronger class is the one that matters: phone detection is what "
       "drives a PHONE_DETECTED violation, while production face <i>detection</i> runs through "
       "YuNet and never touches this model. The phone curve holds precision above 0.95 out to "
       "roughly 0.85 recall before collapsing, which is the shape a detector needs for this "
       "application - room to trade a little recall for high precision. One caveat follows from "
       "the weaker curve: the face-shaped false-positive suppressor described in section 4.6 "
       "relies on this model's own face-class box, that is, on the less accurate of its two "
       "outputs.")

figure("confusion_matrix_normalized.png",
       "Figure 3. Column-normalized confusion matrix (columns are ground truth, rows are "
       "predictions). <b>Class confusion is essentially absent</b> - 0.98 of true phones are "
       "predicted phone and 0.96 of true faces predicted face, with only 0.01 leaking either way "
       "between the two. The real error mode is the <i>background</i> column: among detections "
       "that matched no ground-truth box at all, 43% were phone-class and 57% face-class. The "
       "background row is the mirror case, showing objects missed entirely - 1% of true phones "
       "and 2% of true faces.",
       width=5.3 * inch)

p("Figure 3 also resolves an apparent contradiction with the face-shaped false-positive bug "
  "described in the next section. This matrix says the model almost never mistakes a phone for a "
  "face - yet the deployed model demonstrably emitted phone boxes at 0.88-0.90 confidence on "
  "frames containing only a bare face. Both are true, because they are counted differently: a "
  "spurious phone box drawn over a face matches no ground-truth <i>phone</i> box, so it is "
  "tallied in the background column as a background false positive, not in the face column as a "
  "class confusion. The bug is fully present in this matrix; it simply is not visible in the cell "
  "one would instinctively check. This is a compact illustration of the chapter's recurring "
  "point - an aggregate metric can be accurate and still fail to show the failure that matters.")

h2("4.6 The deployed inference pipeline")

p("Evaluating the raw network alone would measure a strictly weaker system than the one deployed. "
  "Production runs four stages, and every evaluation script in sections 7 and 8 reproduces all "
  "four by importing the same shared code path:")

bullets([
    "<b>Whole-frame pass</b> at confidence &#8805; 0.35.",
    "<b>Face-shaped false-positive suppression.</b> Any phone box overlapping the model's own "
    "same-pass face box at IoU &#8805; 0.45 is discarded. This exists because the detector was "
    "found to emit a phone box at 0.88-0.90 confidence on frames showing only a bare face - far "
    "above the 0.35 threshold, so it bypassed every downstream safety net. Two attempted retrains "
    "failed to fix it (8.7); this zero-cost geometric post-filter did.",
    "<b>Pose-guided hand-crop fallback.</b> If the whole-frame pass finds nothing, the pose model "
    "locates visible wrist keypoints (visibility &#8805; 0.10) and the detector re-runs on 320x320 "
    "crops centred there, at a deliberately lower threshold of 0.20 - narrowing the search to "
    "'right next to a hand' is itself strong evidence, so a lower score is admissible there than "
    "anywhere in frame. The 320 px crop size was swept empirically, not chosen for roundness: "
    "raising it from an initial 120 px recovered most of the missed recall, and false positives "
    "stayed flat until well past 320.",
    "<b>Temporal corroboration.</b> Detections between 0.20 and 0.35 are held as candidates and "
    "only escalate to a logged violation if corroborated across 2 of 3 consecutive polls, which "
    "suppresses isolated single-frame noise without lowering the standing threshold.",
])

story.append(PageBreak())

# ---------------------------------------------------------------- 5. Face recognition
h1("5. Model B - Face Identity Verification (LBPH)")

h2("5.1 Per-student training at enrollment")

p("Unlike the other two models, this one is not trained once and shipped. A <b>separate LBPH "
  "recognizer is fitted per student</b> at enrollment, from that student's own submitted images:")

code("crop = _detect_and_crop(image_bytes)   # YuNet -&gt; grayscale -&gt; 200x200\n"
     "...\n"
     "labels = np.array([student_id] * len(samples))\n"
     "recognizer = cv2.face.LBPHFaceRecognizer_create()\n"
     "recognizer.train(samples, labels)\n"
     "recognizer.write(f\"{student_id}.yml\")")

p("At least three usable samples are required; images in which YuNet finds no face are dropped, "
  "and enrollment is rejected with a corrective message if too few survive. <b>Raw enrollment "
  "photos are never persisted</b> - only the fitted "
  "<font face='Courier'>.yml</font> model is kept. That is a deliberate privacy design decision, "
  "and it has a direct methodological consequence: there exists no stored image set of real "
  "enrolled students, so the verification threshold could not be calibrated on real users and "
  "required a proxy population instead (5.2).")

p("At verification time the probe frame goes through the identical detect-crop-grayscale-resize "
  "path and is scored with <font face='Courier'>predict</font>, which returns an LBPH "
  "<b>distance</b>: lower means more similar. A distance above the threshold is an identity "
  "mismatch.")

h2("5.2 Threshold calibration on a proxy population")

p("The original threshold of 80.0 was an unvalidated default. It was calibrated by treating the "
  "OEP subjects - real people, real webcams, real lighting variety, recorded under similar shared "
  "study conditions - as a stand-in population. For each subject, a handful of their frames train "
  "an LBPH model exactly the way enrollment does; held-out frames from the <b>same</b> subject "
  "become genuine attempts, and frames from <b>every other</b> subject become impostor attempts. "
  "This is a plausible worst-case impostor model for this application: a classmate under similar "
  "camera and lighting conditions, not a random stranger.")

p("Genuine and impostor distance distributions overlap substantially (genuine median 42.2, ranging "
  "up to 90.0; impostor starting at 48.4, median 80.6):")

table([
    ["Threshold", "Precision", "Recall", "False Accept Rate", "False Reject Rate", "Verdict"],
    ["80.0 (original default)", "0.552", "0.979", "47.6%", "~2%",
     "Rejected - nearly half of impostor attempts accepted, defeating the check's entire purpose"],
    ["60.0 (deployed)", "0.950", "0.873", "2.7%", "12.7%",
     "F1-optimal on this data; adopted"],
], [1.05 * inch, 0.7 * inch, 0.6 * inch, 0.85 * inch, 0.85 * inch, 2.45 * inch],
    "Table 6. Face-verification threshold sweep. The trade is explicit: legitimate students are "
    "false-flagged on roughly 1 check in 8 instead of 1 in 48, in exchange for closing a 47.6% "
    "false-accept hole. This is defensible only because a flag is reviewable evidence for an "
    "instructor, not an automatic sanction.")

p("<b>Offline-to-live transfer was then confirmed, not assumed.</b> Five genuine trials on a real "
  "enrolled student with a real webcam scored 40.8-44.2, closely matching the offline genuine "
  "median of 42.2. This step exists because an earlier offline sweep for the phone detector "
  "transferred badly to live hardware (8.3), and the lesson - verify a swept threshold against "
  "live capture before trusting it - was applied here.")

h2("5.3 A ceiling found, and honestly recorded")

p("The same live test surfaced a problem that no threshold can fix: <b>a photograph of a different "
  "person held up to the webcam scored 41.9-46.2</b> - squarely inside the genuine range. LBPH "
  "compares texture and has no concept of liveness, so this is an anti-spoofing gap rather than a "
  "calibration gap.")

p("The first countermeasure is a frame-difference liveness check: a live face exhibits continuous "
  "micro-movement between polls, a static photo does not. Live measurement produced a partial "
  "result stated here in full:")

bullets([
    "<b>Genuine, deliberately still</b> (reading a question, trying not to move): consecutive-poll "
    "mean absolute difference 11.3-30.9.",
    "<b>Hand-held photo</b> (the realistic attack): 7.2-20.3 - <b>overlapping</b> genuine. Natural "
    "hand tremor moves the photo enough to imitate a living person. No threshold separates these "
    "two distributions; this ceiling stands.",
    "<b>Rigidly propped photo, no hand contact</b>: 3.06-6.68, pooled over two independent capture "
    "rounds, with zero overlap against genuine's 11.3 floor.",
])

p("The threshold was accordingly raised from 3.0 to 8.0 - above the rigid-spoof maximum of 6.68, "
  "safely below the genuine floor of 11.3 - which closes the rigid-mount sub-case only. The "
  "hand-held case remains open and is documented in the source as a signal ceiling, with the note "
  "that closing it would require a categorically different signal (such as blink detection from "
  "dense eyelid landmarks, which no photograph can produce) rather than further tuning of this one.")

story.append(PageBreak())

# ---------------------------------------------------------------- 6. Risk model
h1("6. Model C - Risk Scorer (Logistic Regression)")

h2("6.1 Feature construction")

p("The risk model replaces what were previously hand-guessed weights for the three vision signals. "
  "Its training data is built in two deliberately separated stages, because detection is slow "
  "(about 1 s per poll on CPU across three YOLO passes plus YuNet) while the labeling rule is a "
  "judgment call worth iterating on cheaply:")

bullets([
    "<b>Stage 1 - cache detections.</b> The real production detectors are run over the extracted "
    "OEP webcam frames, sampled at 15-second intervals to match the live polling cadence exactly, "
    "and the raw per-poll outcomes (face lost, phone detected, person count) are cached to disk. "
    "This produced 1,546 cached polls.",
    "<b>Stage 2 - window and label.</b> A trailing 120-second window - the same "
    "<font face='Courier'>WINDOW_SECONDS</font> the live risk service uses - slides over each "
    "subject's poll sequence, counting how many polls inside it flagged each event type. This "
    "mirrors exactly what the production risk service counts from real violation rows, so the "
    "model is trained on the same feature distribution it is served.",
])

p("The three features are therefore <font face='Courier'>face_lost_count</font>, "
  "<font face='Courier'>phone_detected_count</font>, and "
  "<font face='Courier'>multiple_people_count</font>. Browser-behavior signals (tab switching, "
  "copy-paste, fullscreen exit) are excluded from the model and remain hand-weighted, because no "
  "video ground truth exists to train them against - they are not visible in webcam footage at all.")

h2("6.2 The labeling rule, and what was deliberately excluded")

p("The OEP ground truth defines five cheat types. Only some have any correlate a webcam-based "
  "vision system could plausibly observe, and the labeling rule says so explicitly:")

table([
    ["Cheat code", "Meaning", "Treatment"],
    ["4, 5", "Phone call, phone use", "<b>Positive</b> - directly what phone detection targets"],
    ["2", "Talking to someone",
     "<b>Positive</b> - the documented protocol had a proctor talk to, walk up to, or hand a book "
     "to the student, so a second body plausibly enters frame"],
    ["1, 3, 6", "Reading notes, internet use, undefined",
     "<b>Excluded from the dataset entirely</b> - no plausible visual correlate. Reading notes "
     "does not reliably move the face out of frame; internet use is invisible to a webcam"],
], [0.95 * inch, 1.7 * inch, 3.85 * inch],
    "Table 7. Vision-plausible label mapping. A window whose only overlapping cheat code is 1, 3, "
    "or 6 is dropped rather than forced into either class.")

p("This exclusion was not a stylistic preference - it was forced by a real failure. The first "
  "version labeled <i>any</i> overlapping cheat code as positive, which meant the two validation "
  "subjects (one almost entirely 'talking', one mostly 'reading notes') were tested nearly "
  "exclusively on cheat types with no visual signal at all. The model scored AUC 0.51 - "
  "indistinguishable from chance. The fix was restricting labels to what the sensors can actually "
  "observe, not collecting more data: codes 1, 3, and 6 are structurally invisible no matter how "
  "many subjects are added.")

h2("6.3 Fitting")

p("Logistic regression over the three counts, with "
  "<font face='Courier'>class_weight=\"balanced\"</font> and "
  "<font face='Courier'>C=1.0</font>. The choice of a linear, inspectable model over something "
  "more powerful is deliberate and is the point: the learned coefficients preserve exactly the "
  "interpretability the original hand-weighted formula had - 'how much does each signal move the "
  "score' - while being fitted from real cheat-event ground truth instead of guessed. In a system "
  "whose outputs are contestable by students through an appeals workflow, a coefficient a human "
  "can read out and defend is worth more than a marginal accuracy gain from an opaque model.")

p("The production model is fitted on <b>all</b> subjects rather than on a train/val split. That is "
  "safe only because leave-one-subject-out cross-validation (8.2) already supplies an honest "
  "generalization estimate without permanently reserving data; the training script prints its "
  "in-sample fit under an explicit label stating it is not a held-out metric and pointing at the "
  "cross-validation number instead.")

table([
    ["Property", "Value"],
    ["Windows / subjects", "1,107 windows across 24 subjects"],
    ["Positive rate", "71.0%"],
    ["<font face='Courier'>face_lost_count</font> coefficient", "+0.012 log-odds per unit count"],
    ["<font face='Courier'>phone_detected_count</font> coefficient",
     "+0.027 log-odds per unit count"],
    ["<font face='Courier'>multiple_people_count</font> coefficient",
     "+1.710 log-odds per unit count"],
    ["Intercept", "-1.511"],
], [2.6 * inch, 3.9 * inch],
    "Table 8. Fitted production risk model, read from the serialized "
    "<font face='Courier'>risk_model.joblib</font>. The coefficients are themselves a finding: a "
    "second person in frame dominates the score by roughly two orders of magnitude over the other "
    "two signals, which is consistent with 'a second body is unambiguous, while a lost face or a "
    "borderline phone box is frequently benign'.")

h2("6.4 Output rescaling")

p("The OEP subjects were scripted or prompted to cheat, so the training set's 71% positive rate is "
  "nowhere near a real exam population's. That inflated base rate lives in the intercept, and its "
  "consequence is visible: the raw model assigns roughly 0.16 probability to a session with "
  "<b>zero</b> detected violations. A clean session must score 0, not an unexplained baseline, so "
  "the serving layer rescales the raw probability against that zero-evidence floor - the floor "
  "maps to 0, and the already near-1 maximum-evidence case stays near 1. This changes only the "
  "output scale; it does not alter what the model learned about how the three signals relate.")

story.append(PageBreak())

# ---------------------------------------------------------------- 7. F1
h1("7. F1 Score: Definition and Computation")

h2("7.1 The formulas")

p("Precision, recall, and F1 are computed from raw counts of true positives (TP), false positives "
  "(FP), and false negatives (FN), with F1 as their harmonic mean:")

code("precision = TP / (TP + FP)\n"
     "recall    = TP / (TP + FN)        # equivalently TP / total_positives\n"
     "F1        = 2 * precision * recall / (precision + recall)")

p("The harmonic mean is the appropriate summary here precisely because it refuses to be rescued by "
  "one strong component: a detector that flags every frame reaches recall 1.0, and a detector that "
  "flags nothing but its single most confident frame can reach precision 1.0. Both score near zero "
  "on F1. For proctoring, both failure modes are unacceptable in different ways - the first buries "
  "instructors in false accusations, the second silently misses real ones - so the metric must "
  "penalize each.")

h2("7.2 The unit of evaluation is a frame, not a box")

p("This is the single most important definitional choice in the chapter, and it is dictated by "
  "what the deployed system actually does. Production's real check is a <b>presence</b> test - "
  "'did any phone-class detection survive in this frame' - which then drives whether a violation "
  "is logged. It has no location awareness whatsoever. So the metric counts frames:")

bullets([
    "<b>TP</b> - a frame that contains a real phone and was flagged.",
    "<b>FP</b> - a frame that contains no phone and was flagged.",
    "<b>FN</b> - a frame that contains a real phone and was not flagged.",
    "A frame with no phone and no flag is a true negative, and correctly contributes to none of "
    "precision, recall, or F1.",
])

p("An earlier version of the evaluation required an IoU match against the ground-truth box before "
  "counting a detection as correct. That was a stricter and <b>different</b> question from the one "
  "production asks, and it silently mis-counted: a correct-verdict-but-wrong-location detection on "
  "a phone-positive frame was recorded only as a missed true positive, never as the false positive "
  "it simultaneously was. Both metrics are now computed and reported side by side:")

table([
    ["Metric", "Definition", "Status"],
    ["<b>Presence</b>",
     "Any surviving phone-class detection anywhere in frame, from the whole-frame pass "
     "<b>or</b> the hand-crop fallback, counts as a flag. Reproduces "
     "<font face='Courier'>object_detection_service.py</font>'s deployed check exactly.",
     "<b>The headline number.</b> Every accept/reject decision cites this."],
    ["<b>Localized</b>",
     "Additionally requires the detection to overlap a real ground-truth box at IoU &#8805; 0.3.",
     "Diagnostic only. Catches 'right answer for the wrong reason' - it is what exposed the "
     "eye-tracker-device confounder described in 3.5."],
], [0.85 * inch, 3.55 * inch, 2.1 * inch])

h2("7.3 Two evaluation bugs that changed the numbers")

p("Both were found and fixed before any reported figure was produced, and both are recorded "
  "because each had been silently distorting results:")

bullets([
    "<b>The evaluation omitted the hand-crop fallback.</b> The scripts scored only the whole-frame "
    "pass, that is, a strictly weaker pipeline than the one deployed, so real recall was being "
    "<i>understated</i>. Both the holdout evaluation and the threshold sweep now import one shared "
    "module that makes the identical model calls production makes - the fix was to unify the code "
    "path, not to keep two implementations in sync by discipline.",
    "<b>Ground-truth matching read only the first box in a frame.</b> Frames legitimately carry "
    "more than one phone-class box (3.5), so IoU was sometimes being computed against the wrong "
    "box - occasionally the residual bogus one. This alone manufactured an apparent per-subject "
    "recall gap that was later shown to be an evaluation defect, not a model or fairness defect "
    "(8.6). The loader now returns every box in the frame, and a prediction matching any of them "
    "counts.",
])

h2("7.4 Worked computation - the deployed detector")

p("Evaluated on the 322-frame frozen holdout (96 phone-positive, 226 phone-negative), through the "
  "full production pipeline, at production's real 0.35 confidence threshold:")

code("TP = 76,  FP = 6,  FN = 96 - 76 = 20\n\n"
     "precision = 76 / (76 + 6)  = 76 / 82 = 0.927\n"
     "recall    = 76 / 96                  = 0.792\n"
     "F1        = 2 * 0.927 * 0.792 / (0.927 + 0.792) = 0.854")

p("Read plainly: of every 100 frames the system flags for a phone, about 93 really contain one; of "
  "every 100 frames that really contain a phone, about 79 are flagged. The asymmetry is "
  "intentional. In proctoring a false accusation is more costly than a missed frame, and a missed "
  "<i>frame</i> is not a missed <i>event</i> - phone use spans many consecutive polls, so the "
  "system has repeated independent chances to catch a single real episode, while each false "
  "positive is a fresh burden on a real student.")

h2("7.5 F1 for the other two models")

p("<b>Risk model.</b> Fitted through scikit-learn, so precision, recall, F1, and ROC-AUC come from "
  "<font face='Courier'>sklearn.metrics</font> on the same TP/FP/FN definitions, with a window "
  "(not a frame) as the unit and the default 0.5 decision threshold for the thresholded metrics. "
  "The training script also evaluates the <b>old hand-set weights</b> on the identical validation "
  "windows, so the improvement from training is measured against the thing it replaced rather than "
  "assumed. Because a threshold-free summary is more informative for a scorer whose output is a "
  "continuous 0-100 value, ROC-AUC - not F1 - is the headline metric for this model (8.2).")

p("<b>Face verification.</b> Reported as precision and recall plus False Accept Rate and False "
  "Reject Rate (Table 6), since FAR and FRR are the biometric-standard framing and speak directly "
  "to the two asymmetric costs: an accepted impostor defeats the check, a rejected genuine student "
  "is a wrongly flagged innocent person.")

h2("7.6 The training-time F1 curve, and why it is not the headline number")

p("The training run produces its own F1 curve, and it is included here specifically because it is "
  "easy to mistake for the number in 7.4. It is not the same measurement:")

figure("BoxF1_curve.png",
       "Figure 4. F1 against confidence threshold on the validation split. All classes peak at "
       "<b>F1 = 0.80 at confidence 0.433</b>; the phone class alone peaks near 0.88. <b>This is "
       "not the 0.854 reported in section 7.4</b> - this curve is box-level and IoU-matched, "
       "computed per detection on the validation subjects, whereas 0.854 is frame-level presence "
       "on the frozen holdout through the full four-stage production pipeline. The two answer "
       "different questions and are not interchangeable.")

p("Two things are genuinely useful in Figure 4. First, <b>the curve is broad and flat between "
  "roughly 0.2 and 0.6</b> - across that whole band F1 barely moves. Production's threshold of "
  "0.35 sits comfortably inside that plateau, so the operating point is insensitive to small "
  "changes there, which is a reassuring property for a threshold that must survive varying real "
  "lighting.")

p("Second, and more instructive: <b>this curve's optimum (0.433) disagrees with the frozen-holdout "
  "sweep's recommendation of 0.60-0.70</b> (8.3). Two offline analyses of the same model, on "
  "different data through different pipelines, pointed at materially different thresholds - and "
  "the higher of the two, when actually deployed, collapsed live recall to roughly 4%. That "
  "disagreement is the argument for the rule this project now follows: an offline optimum is a "
  "hypothesis to be checked against live capture, not a decision.")

story.append(PageBreak())

# ---------------------------------------------------------------- 8. Testing and validation
h1("8. Testing and Validation")

h2("8.1 The frozen holdout, and the leakage it exists to prevent")

p("The two validation subjects are a legitimate held-out set for training-time model selection. "
  "But they had also been reused, run after run, to decide whether each new candidate should "
  "replace production. Repeatedly consulting one set to make a <i>sequence</i> of accept/reject "
  "decisions is test-set hill-climbing, not evidence of generalization. Worse, several of those "
  "decisions had also quoted accuracy on live-capture batches the candidate had just been trained "
  "on - a training-set number reported alongside a genuinely held-out one without a label "
  "distinguishing them.")

p("The remedy is a <b>frozen holdout</b>: a stratified 15% slice (322 frames, fixed seed) drawn "
  "proportionally from every train-eligible source - each OEP subject and each live-capture batch "
  "- and physically <b>moved out</b> of the annotation folder, so the split script cannot sweep it "
  "back into training even by accident. Enforcement is structural rather than procedural. Since "
  "all four subjects with real phone use were already committed to train or val, a stratified "
  "slice was the honest best available option, not a first-choice design; the constraint is "
  "recorded as such.")

p("The usage rules are written into the scripts themselves: never train on it; never use it to "
  "pick a checkpoint, tune a threshold, or choose between mid-development candidates; evaluate "
  "once per genuine swap candidate; report the result even when unflattering. The script that "
  "carves the holdout refuses to re-carve an existing one without an explicit force flag, because "
  "re-sampling after evaluation would reintroduce exactly the leakage it exists to prevent.")

h2("8.2 Leave-one-subject-out cross-validation (risk model)")

p("The risk model's original headline AUC of 0.879 was a single point estimate from two held-out "
  "subjects - and those two had been inherited from the detector's split by convention, not chosen "
  "for this purpose. Too thin to support a generalization claim, especially given that a different "
  "pair had once produced AUC 0.51 by accident of which cheat types they happened to contain.")

p("Leave-one-subject-out cross-validation refits the model once per subject, each time holding out "
  "one <b>whole subject</b>. A held-out window from a subject whose other windows are in training "
  "tests almost nothing new - the subject is the real unit of generalization risk, because it "
  "carries the camera, the lighting, and the individual's pose habits. Three things are reported:")

bullets([
    "<b>Per-subject held-out AUC</b> where computable. Subjects with zero positive or zero "
    "negative windows are reported as <i>n/a</i> with the reason - never silently skipped, never "
    "scored 0.",
    "<b>Pooled LOSO AUC</b> - all held-out predictions concatenated, one AUC over all of them. "
    "This is the headline generalization number and the fair comparison against the old "
    "single-split 0.879.",
    "<b>Subject-level bootstrap 95% CI</b> - resampling <b>which subjects</b> contribute, with "
    "replacement. Resampling individual windows would be wrong: windows within a subject are "
    "correlated (same room, same person), so window-level resampling would badly understate the "
    "real uncertainty. Degenerate all-one-class resamples are skipped and counted, not scored.",
])

table([
    ["Dataset", "Subjects", "Windows", "Pooled LOSO AUC", "Subject-level bootstrap 95% CI"],
    ["Original", "11", "-", "0.797", "[0.666, 0.941]  (width 0.275)"],
    ["Expanded (production)", "24", "1,107", "<b>0.813</b>", "<b>[0.712, 0.902]</b>  (width 0.190)"],
], [1.35 * inch, 0.75 * inch, 0.75 * inch, 1.15 * inch, 2.5 * inch],
    "Table 9. The dataset grew when 13 further real subjects with usable ground truth were found "
    "already on disk, unextracted. The interval narrowed by roughly 31% - a genuine tightening of "
    "the uncertainty, which is the more meaningful half of this result; the AUC itself moved only "
    "0.016. The interval remains wide, and that is reported as a real limitation, not smoothed "
    "over.")

h2("8.3 Threshold sweeping, and a live regression it caused")

p("Operating thresholds were swept rather than guessed. The sweep runs the full pipeline "
  "<b>once</b> per holdout image at a low confidence floor, recording every candidate score, and "
  "then sweeps the threshold analytically over those recorded scores - so the holdout is inspected "
  "once, not once per candidate threshold.")

p("That sweep recommended raising the phone threshold from 0.35 to a much higher value, on the "
  "basis of a clear offline F1 improvement. <b>It was deployed and it failed.</b> A live browser "
  "smoke test immediately afterwards, on a genuine continuously-visible phone, found real recall "
  "had collapsed to roughly 4%. Diagnosis: the holdout never sampled the lighting conditions of "
  "the live capture setup, so live confidence scores sat systematically below the offline ones and "
  "fell under the raised bar. The threshold was reverted to 0.35.")

p("This is retained in the methodology as a load-bearing finding rather than an embarrassment. It "
  "establishes the rule the project now follows everywhere - <b>an offline aggregate metric can be "
  "clean and still be wrong about live behavior</b> - and it is the direct reason the face "
  "threshold in 5.2 was live-verified before adoption, and the reason the sequence-replay "
  "evaluation in 8.5 exists at all.")

h2("8.4 Threshold validation for head-down detection")

p("The head-down thresholds were validated with the same sweep methodology, using human-labeled "
  "phone-present frames as a real-world proxy for 'looking down'. The result is a candid negative "
  "one:")

table([
    ["Threshold", "Value", "Precision", "Recall", "F1", "Assessment"],
    ["Head pitch", "-35 deg", "0.50", "0.57", "0.53",
     "F1 <b>peak</b> - no threshold does meaningfully better. Pitch alone is a genuinely weak "
     "signal; this is a ceiling, not a mistuned number"],
    ["Sustained duration", "25 s", "-", "-", "-",
     "Matches real sustained-episode timing measured from densely timestamped label sequences; "
     "ignores brief blips"],
    ["Pose-fallback confidence", "0.10", "0.944", "1.000", "0.971",
     "Never once misses a real head in this data; raising it trades that perfect recall for "
     "marginal precision - a bad deal here"],
], [1.15 * inch, 0.6 * inch, 0.65 * inch, 0.5 * inch, 0.45 * inch, 3.15 * inch],
    "Table 10. Head-down threshold validation.")

p("Roughly 50% frame-level precision is documented in the source as a real limitation of a "
  "pitch-only signal, and it is the reason this signal is never sufficient on its own: the "
  "duration requirement, the captured question context shown to the reviewing instructor, and "
  "mandatory human review all sit downstream of it. The same analysis also found and fixed a real "
  "bug - a single noisy poll was resetting an accumulating head-down episode, discarding a genuine "
  "sustained event, which is why a one-poll miss tolerance now exists.")

h2("8.5 Sequence replay for time-dependent behavior")

p("Temporal corroboration cannot be evaluated by any script that treats frames independently or "
  "shuffles them - the feature is defined over consecutive polls. A dedicated evaluation replays "
  "each live-capture batch <b>in its original filming order</b>, which is the order a live polling "
  "loop would have observed, and reports old single-frame behavior against new corroborated "
  "behavior per batch, naming the specific frames corroboration recovered and the ones it broke. "
  "It reuses the same shared analysis function, so it measures the deployed pipeline rather than a "
  "reimplementation of it.")

h2("8.6 Fairness sensitivity audit")

p("A tier-1 audit reports per-subject and per-capture-batch accuracy across all real labeled "
  "frames, flagging any group more than 15 points below the overall figure. Its limitation is "
  "stated first and not buried: <b>the source corpus carries no demographic metadata</b> - no skin "
  "tone, gender, age, or camera-quality labels. The audit can say 'this subject scores lower'; it "
  "cannot say why. Every disparity it surfaces is a lead for a real demographic audit (recruit "
  "deliberately, label attributes, re-run), never a finished fairness conclusion.")

p("It has nonetheless earned its place twice. It found the label defect described in 3.5. And when "
  "it flagged one subject at 0.741 recall against 0.918 overall, re-measuring after the multi-box "
  "ground-truth fix (7.3) showed <b>no disparity at all</b>: 0.898 presence recall against 0.948 "
  "overall across 2,582 frames, with the audit's own disparity flag returning nothing. The gap had "
  "been an evaluation defect. The procedural rule taken from this - visually review a flagged "
  "group's actual frames before concluding the model is at fault - is recorded for reuse.")

p("Note that this audit deliberately draws from <b>both</b> the training pool and the frozen "
  "holdout, unlike every other evaluation here. It is a diagnostic characterization of the "
  "deployed model rather than a swap decision, so per-group sample size (statistical power to "
  "detect a disparity at all) matters more than avoiding training contamination. Groups drawn from "
  "training data are labeled as such in its output so the two are never conflated.")

h2("8.7 Negative results")

p("Three are recorded, because a methodology that only reports what worked is not a methodology:")

bullets([
    "<b>Two retrains on additional hand-corrected data both regressed.</b> A 1,773-frame corrected "
    "personal-video batch was merged into training twice - once in full, once downweighted. Frozen "
    "holdout F1 came out at 0.833 and 0.838 against production's 0.854. The batch was dropped from "
    "the training set entirely and production weights were never touched. The underlying "
    "false-positive bug was later fixed by the zero-cost geometric post-filter in 4.6 - "
    "<b>more data was the wrong tool for that problem.</b>",
    "<b>A second independent pitch signal from the pose model was tried and reverted</b>, on "
    "measured evidence of worse F1.",
    "<b>The offline threshold sweep of 8.3 was deployed and reverted</b> after live measurement "
    "contradicted it.",
])

h2("8.8 Software-level regression testing")

p("Model behavior is only half of correctness. The backend carries <b>109 automated tests</b>, all "
  "passing at the most recent full run, covering authentication, the permission model, schema "
  "integrity, violation handling, head-down tracking, head-pose estimation, and an end-to-end "
  "system smoke test. Detection services expose synthetic-input paths so the surrounding logic can "
  "be tested without loading model weights, and the pure-bookkeeping parts of the pipeline (the "
  "static-image streak counter, the corroboration candidate window) are deliberately factored out "
  "of the model-calling code specifically so they remain testable in isolation.")

story.append(PageBreak())

# ---------------------------------------------------------------- 9. Limitations
h1("9. Limitations")

p("Stated plainly, because each one bounds how the numbers in this chapter may legitimately be "
  "read:")

bullets([
    "<b>The subject population is small and not demographically characterized.</b> 24 real "
    "subjects, no skin-tone, gender, age, or camera-quality metadata. The fairness audit is a "
    "sensitivity analysis over incidental variation, not a demographic audit.",
    "<b>The risk model's confidence interval is wide.</b> Pooled LOSO AUC 0.813, 95% CI "
    "[0.712, 0.902]. The point estimate should not be quoted without the interval.",
    "<b>Risk training labels come from a scripted cheating population</b> with a 71% positive "
    "rate, far from any real exam. The output rescaling in 6.4 corrects the score's zero point; it "
    "cannot correct the underlying prevalence mismatch.",
    "<b>Face-verification calibration used a proxy population,</b> because real enrolled students' "
    "photos are deliberately never stored. Live testing confirmed the genuine distribution "
    "transfers, but the impostor distribution was never validated against real impostor attempts.",
    "<b>The hand-held photo spoof is not caught</b> by the current liveness check, and this is a "
    "signal ceiling rather than a tuning gap (5.3).",
    "<b>Head-pitch precision is roughly 50% at the frame level</b> - the signal requires duration, "
    "question context, and human review to be usable at all (8.4).",
    "<b>A minority of multi-box training frames may retain a redundant spurious box</b> (3.5). "
    "The evaluation code compensates; the training labels still carry it.",
    "<b>Offline metrics have been shown to mispredict live behavior on this system</b> (8.3). "
    "Every reported figure is offline unless it says otherwise.",
])

h1("10. Reproduction")

p("The pipeline is reproducible end to end from this repository. All scripts live in "
  "<font face='Courier'>backend/training/</font>; the external image corpora must be obtained "
  "separately and their paths set in the corresponding "
  "<font face='Courier'>data.yaml</font>. Seeds are fixed throughout (dataset assembly, holdout "
  "carving, bootstrap resampling, and the detector run itself at "
  "<font face='Courier'>seed: 0, deterministic: true</font>).")

code("# Detector\n"
     "python extract_oep_frames.py            # webcam track only, anonymized filenames\n"
     "python prioritize_oep_frames.py         # classify frames against gt.txt\n"
     "python build_annotation_batch.py        # bounded, per-subject-balanced batch\n"
     "python auto_annotate_oep.py             # DRAFT boxes -&gt; hand-corrected in LabelImg\n"
     "python make_frozen_holdout.py           # carve the frozen holdout FIRST\n"
     "python prepare_oep_split.py             # subject-level train/val split\n"
     "python finetune_phone_face.py --epochs 8 --batch 8 --imgsz 416\n"
     "\n"
     "# Risk model\n"
     "python extract_risk_polls.py            # real detectors at the 15s live cadence\n"
     "python build_risk_windows.py            # 120s windows, vision-plausible labels only\n"
     "python loso_cv_risk_model.py            # generalization estimate + bootstrap CI\n"
     "python train_risk_model.py --final      # production fit on all subjects\n"
     "\n"
     "# Evaluation and validation\n"
     "python evaluate_frozen_holdout.py --model ../app/resources/phone_specialist.pt\n"
     "python threshold_sweep.py               # analytic sweep from a single inference pass\n"
     "python evaluate_corroboration.py        # sequence replay in original filming order\n"
     "python fairness_audit.py                # per-subject / per-batch disparity check\n"
     "python analyze_face_recognition_threshold.py\n"
     "python analyze_head_pose_thresholds.py\n"
     "python analyze_pose_fallback_threshold.py")

p("<b>One ordering constraint is not optional:</b> the frozen holdout must be carved before the "
  "train/val split is generated. Reversing the order puts holdout frames into training and "
  "invalidates every subsequent evaluation number in this chapter.")

if __name__ == "__main__":
    doc = SimpleDocTemplate(
        OUT_FILE, pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.9 * inch, bottomMargin=0.9 * inch,
        title="AI ExamGuard - Model Training Methodology",
        author="AI ExamGuard",
    )
    doc.build(story)
    print(f"Wrote {OUT_FILE}")
