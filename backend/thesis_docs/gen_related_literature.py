"""One-off script generating the Related Literature (Technical + Theoretical Background)
chapter PDF. Not part of the app - a docs-generation utility only, same convention as
gen_diagrams.py. Every citation below was verified against a real, findable source before
being written in; none are invented.
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

OUT_FILE = "AI_ExamGuard_Related_Literature.pdf"

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
ref_style = ParagraphStyle("RefX", parent=styles["Normal"], fontSize=9.7, leading=14,
                            leftIndent=18, firstLineIndent=-18, spaceAfter=7,
                            alignment=TA_JUSTIFY)

story = []

# ---- Title page ----
story.append(Spacer(1, 1.6 * inch))
story.append(Paragraph("Review of Related Literature and Studies", title_style))
story.append(Paragraph("Technical and Theoretical Background", subtitle_style))
story.append(Spacer(1, 0.35 * inch))
story.append(Paragraph(
    "AI ExamGuard: An AI-Assisted Online Examination Proctoring and "
    "Academic Integrity Monitoring System", meta_style))
story.append(PageBreak())

# ---- Introduction ----
story.append(Paragraph("Introduction", h1_style))
story.append(Paragraph(
    "This chapter reviews the technical and theoretical foundations underpinning AI ExamGuard, "
    "an AI-assisted online examination proctoring system built to detect identity mismatches, "
    "unauthorized devices, and behavioral anomalies during remote assessments while remaining "
    "auditable and appealable. The technical background surveys the computer-vision and "
    "machine-learning techniques behind the system's face-detection, face-recognition, "
    "object-detection, head-pose, and risk-scoring components, together with the documented "
    "fairness limitations of these techniques. The theoretical background situates the system "
    "within academic-integrity, surveillance, and technology-acceptance scholarship, since a "
    "proctoring tool is as much a social intervention as a technical one. Together, these two "
    "strands motivate the specific design choices — disclosed limitations, an appeals "
    "workflow, and a fairness audit — that distinguish this system from conventional "
    "black-box commercial proctoring tools.", body_style))

# ---- Technical Background ----
story.append(Paragraph("Technical Background", h1_style))

story.append(Paragraph("AI-Based Online Examination Proctoring Systems", h2_style))
story.append(Paragraph(
    "The shift to remote and online assessment has driven a large body of work on AI-assisted "
    "proctoring, which typically combines webcam-based identity verification, gaze/behavior "
    "monitoring, and browser-activity tracking to flag potential academic dishonesty without a "
    "live human proctor watching every student continuously. This literature consistently reports "
    "that such systems improve scalability and cost relative to live human proctoring, but just as "
    "consistently flags privacy, algorithmic bias, and test-taker anxiety as open, unresolved "
    "problems rather than solved ones. AI ExamGuard's own architecture — a FastAPI backend "
    "coordinating browser-based face and object checks against a React exam-taking client — "
    "follows this same general pattern, but was deliberately built to treat the privacy, bias, and "
    "anxiety concerns as first-class design requirements (evidence-retention limits, a student "
    "appeals workflow, a documented fairness audit) rather than deferred future work, directly "
    "responding to the gap this literature repeatedly identifies.", body_style))

story.append(Paragraph("Real-Time Object Detection for Unauthorized-Device Monitoring", h2_style))
story.append(Paragraph(
    "Redmon, Divvala, Girshick, and Farhadi (2016) introduced You Only Look Once (YOLO), reframing "
    "object detection as a single regression problem over a full image rather than a multi-stage "
    "classify-then-localize pipeline, which made real-time detection (45+ FPS on then-current "
    "hardware) practical for the first time. Successive YOLO generations, culminating in "
    "Ultralytics' YOLOv8 (Jocher, Chaurasia, &amp; Qiu, 2023), retained this single-pass design "
    "while improving small-object and occluded-object accuracy — the exact failure mode (a "
    "partially hidden phone held low, out of frame center) that matters for exam-room device "
    "detection. AI ExamGuard's object-detection service uses a YOLOv8-based general detector "
    "alongside a phone-specialist model fine-tuned on real proctoring footage, plus a pose-guided "
    "hand-region re-check, specifically to recover the low-confidence, partially-occluded cases "
    "this literature identifies as YOLO's persistent weak point.", body_style))

story.append(Paragraph("Lightweight Real-Time Face Detection", h2_style))
story.append(Paragraph(
    "Locating a face reliably, at low latency, on commodity webcam hardware without a GPU "
    "dependency, is a separate problem from recognizing whose face it is. Wu, Peng, and Yu (2023) "
    "address exactly this with YuNet, an anchor-free, sub-100KB-parameter face detector reporting "
    "millisecond-level inference and explicit robustness to pose and partial occlusion — "
    "properties that matter directly for a browser-based, CPU-only proctoring pipeline that must "
    "run a face check every few seconds without becoming the exam-taking experience's bottleneck. "
    "AI ExamGuard adopts YuNet (via OpenCV's DNN face module) as its face-localization stage, and "
    "the same facial landmarks YuNet already computes for detection are reused downstream for "
    "head-pose estimation rather than discarded, directly building on the model's documented "
    "landmark output.", body_style))

story.append(Paragraph("Face Recognition for Identity Verification", h2_style))
story.append(Paragraph(
    "Once a face is located, identity verification is a distinct recognition problem. Ahonen, "
    "Hadid, and Pietikäinen (2006) proposed Local Binary Pattern Histograms (LBPH), which "
    "encode a face as a set of local micro-texture histograms rather than holistic pixel "
    "intensities, giving the representation documented robustness to the uneven, uncontrolled "
    "lighting typical of a home webcam setup. This lighting robustness and low computational cost "
    "are why AI ExamGuard trains a per-student LBPH model (via OpenCV's cv2.face module) from a "
    "small number of enrollment images rather than requiring a large labeled dataset or cloud "
    "inference, at the cost of the lower accuracy headroom the literature also documents relative "
    "to modern deep face-recognition embeddings.", body_style))

story.append(Paragraph("Head-Pose Estimation as an Attention/Gaze Proxy", h2_style))
story.append(Paragraph(
    "Because true eye-gaze tracking typically needs specialized hardware or tightly controlled "
    "camera geometry, online-learning-engagement research instead commonly estimates coarse head "
    "orientation from ordinary webcam frames — via OpenCV's solvePnP against a generic 3D "
    "face template fitted to a small set of 2D facial landmarks — and treats sustained "
    "head-down or off-screen orientation as an attention proxy rather than a literal measurement "
    "of visual focus. Closer to the proctoring context specifically, Shih et al. (2024) built an "
    "AI-assisted gaze-detection tool at Duolingo to help human proctors triage which recorded exam "
    "moments are worth reviewing. This same distinction — pose as a proxy signal, not a "
    "ground-truth measurement — is central to how AI ExamGuard frames its own “Prolonged "
    "Downward Gaze” feature: head pitch is estimated via solvePnP from YuNet's landmarks at "
    "zero added inference cost, but the feature is deliberately disclosed to students as a coarse "
    "signal for human review, not as gaze tracking, matching this literature's own caution that "
    "head pose is a meaningfully weaker signal than genuine gaze.", body_style))

story.append(Paragraph("Algorithmic Fairness and Demographic Bias in Facial Analysis", h2_style))
story.append(Paragraph(
    "A now-foundational finding in this space is Buolamwini and Gebru's (2018) Gender Shades "
    "study, which measured commercial gender-classification systems' error rates across a dataset "
    "intentionally balanced by skin type and found error rates below 1% for lighter-skinned men "
    "but as high as 34.7% for darker-skinned women — evidence that aggregate accuracy figures "
    "can conceal large, systematic subgroup disparities. NIST's own Face Recognition Vendor Test "
    "Part 3 (Grother, Ngan, &amp; Hanaoka, 2019), evaluating nearly 200 algorithms from around 100 "
    "developers, corroborated this at much larger scale, finding demographic-dependent "
    "false-positive/false-negative differentials that vary by algorithm and threshold rather than "
    "being uniformly present or absent. This literature directly motivates AI ExamGuard's own "
    "fairness-audit work: a per-subject/per-batch sensitivity sweep against real proctoring "
    "footage, and — because the project's own dataset lacks labeled demographic attributes "
    "— a set of disclosed proxy analyses (image-brightness/lighting condition, synthetic "
    "camera-quality degradation, and headscarf presence via Meta's FACET benchmark) run as an "
    "honest, caveated first step toward the genuine demographic audit this literature shows is "
    "necessary, not a substitute for it.", body_style))

story.append(Paragraph("Statistical Risk Scoring and Model Evaluation", h2_style))
story.append(Paragraph(
    "Beyond detection and recognition, combining multiple weak behavioral signals (face loss, "
    "device detection, tab-switching, prolonged head-down) into a single interpretable risk "
    "estimate is itself a standard supervised-learning problem — logistic regression, "
    "cross-validation for generalization estimation, and their associated bias-variance tradeoffs "
    "are covered in standard statistical-learning references such as James, Witten, Hastie, and "
    "Tibshirani (2021). AI ExamGuard's risk service follows this methodology directly: a "
    "logistic-regression model fit on real, labeled proctoring windows, with leave-one-subject-out "
    "cross-validation — rather than a random split — used specifically to estimate how "
    "the score is likely to generalize to a student the model has never seen, the harder and more "
    "honest question for a deployed proctoring tool than in-sample accuracy alone.", body_style))

# ---- Theoretical Background ----
story.append(Paragraph("Theoretical Background", h1_style))

story.append(Paragraph("Deterrence Theory and the Fraud Triangle", h2_style))
story.append(Paragraph(
    "The premise that observation, or the credible threat of it, reduces dishonest behavior "
    "traces to Cressey's (1953) fraud-triangle model, which identifies opportunity, pressure, and "
    "rationalization as the three jointly necessary conditions for fraud, and holds that removing "
    "any one of them suppresses the behavior. Applied to remote assessment, this predicts that "
    "visible, credible monitoring — reducing perceived opportunity and the ease of "
    "rationalizing “no one will know” — should measurably reduce dishonesty, a "
    "prediction empirically tested by Alguacil, Herranz-Zarzoso, and Perniás (2024), whose "
    "randomized field experiment on webcam-monitored versus unmonitored online exams found "
    "monitored students scored significantly lower, consistent with monitoring suppressing "
    "behavior that had been inflating unmonitored scores. This theory is the direct justification "
    "for AI ExamGuard's existence as a deterrent, but it also supplies a caution the system's own "
    "design tries to take seriously: deterrence theory says nothing about false positives, and a "
    "system that deters by threat of detection carries a distinct due-process obligation when a "
    "detection is wrong — the motivation behind building a real student-facing appeals "
    "workflow rather than treating every flagged violation as a settled verdict.", body_style))

story.append(Paragraph("Surveillance Theory: The Panopticon and Educational AI", h2_style))
story.append(Paragraph(
    "Foucault's (1977) panopticon — a prison architecture in which a single unseen watcher "
    "can observe any cell at any moment, so inmates internalize discipline under the mere "
    "possibility of being watched — is the standard theoretical lens for continuous "
    "monitoring technologies, and has been applied specifically to online proctoring: the "
    "one-sidedness of the arrangement, in that the student cannot verify when or whether they are "
    "being watched or algorithmically scored, reproduces the panopticon's central mechanism. Dai, "
    "Thomas, and Rawolle (2025) extend this analysis to AI-mediated education specifically, "
    "arguing that algorithmic surveillance introduces a “post-panoptic” form of "
    "disciplinary power in which the system itself, not a human watcher, normalizes behavior "
    "toward efficiency and compliance, often at a documented cost to student autonomy and trust. "
    "This theoretical framing is why AI ExamGuard treats disclosure as a design requirement rather "
    "than a legal formality: every monitored signal, including weaker, proxy-based ones like "
    "prolonged downward gaze, is listed to the student before the exam begins, on the reasoning "
    "that an undisclosed panopticon is a strictly worse position for the student than a disclosed "
    "one, even though disclosure alone does not resolve the power asymmetry the theory "
    "describes.", body_style))

story.append(Paragraph("Technology Acceptance Model (TAM)", h2_style))
story.append(Paragraph(
    "Davis's (1989) Technology Acceptance Model explains adoption behavior through two constructs "
    "— perceived usefulness and perceived ease of use — and remains the dominant "
    "framework for studying whether users actually trust and adopt a given system rather than "
    "merely tolerate it. Jiang, Goh, Chen, Liu, and Yang (2023) extended TAM specifically to "
    "online-proctoring acceptance during COVID-19, and found that social influence and social "
    "presence, rather than usefulness alone, were the strongest predictors of whether students "
    "accepted being proctored — meaning a proctoring tool's perceived legitimacy depends "
    "heavily on institutional framing and social context, not just on the tool's technical "
    "accuracy. This motivates AI ExamGuard's positioning choice: since raw detection accuracy is "
    "not, by this literature, sufficient for acceptance, the system is deliberately framed to "
    "instructors and students as a transparent, explainable, and appealable alternative to opaque "
    "commercial proctoring — an attempt to influence the social-presence and trust variables "
    "TAM identifies as decisive, not just the underlying model accuracy.", body_style))

story.append(Paragraph("Disability, Accessibility, and Fairness in Surveillance-Based Assessment", h2_style))
story.append(Paragraph(
    "A growing qualitative literature documents that proctoring surveillance and disability "
    "accommodation are frequently in direct tension: Kwapisz, Ackerman, Nguyen, and Rajivan (2025) "
    "interviewed students with disability accommodations and found real, reported anxiety that "
    "ordinary accommodation behavior, such as looking away, stepping away, or atypical posture and "
    "movement, would itself be misread by the system as suspicious, increasing cognitive load "
    "during an already high-stakes exam. This is the direct rationale for AI ExamGuard's "
    "accommodation pathway — server-side flags that suppress specific checks (face "
    "verification, object detection) entirely for students with a documented need, enforced in the "
    "detection service itself rather than only hidden in the frontend — a design response to "
    "exactly the failure mode this literature reports, rather than a generic accessibility "
    "checkbox.", body_style))

# ---- Related Studies (local) ----
story.append(Paragraph("Related Studies", h1_style))
story.append(Paragraph(
    "The literature reviewed above is predominantly foreign. This section reviews local, "
    "Philippine-context studies that ground the same technical and theoretical concerns in the "
    "population and institutions AI ExamGuard is actually built for.", body_style))

story.append(Paragraph("Academic Dishonesty and Online-Learning Behavior in Philippine Higher Education", h2_style))
story.append(Paragraph(
    "Local Philippine research confirms that the deterrence dynamics summarized in the Theoretical "
    "Background are not merely imported theory. Aguilar (2021) documented the prevalence of "
    "academic dishonesty among Filipino 21st-century learners, and Beruin (2022) surveyed the "
    "specific factors driving it during the Philippines' pandemic-era shift to fully online "
    "instruction, finding that reduced direct observation was a repeatedly cited enabling "
    "condition rather than a side detail. Perez, Zapanta, Heradura, and Napicol (2025) sharpened "
    "this into a quantitative account, surveying 562 Filipino undergraduates and finding that "
    "demographic factors and, most relevant here, students' own attitude toward cheating were the "
    "strongest predictors of self-reported academic cheating in online learning specifically, not "
    "distance-learning circumstances alone. Together these three studies establish that the "
    "deterrence and fraud-triangle mechanisms discussed earlier operate concretely in the "
    "Philippine undergraduate population AI ExamGuard is built for, supporting the premise that a "
    "locally-deployed monitoring tool addresses a real, locally-documented problem rather than an "
    "imported one.", body_style))

story.append(Paragraph("Technology Acceptance of E-Learning and Learning Management Systems in the Philippines", h2_style))
story.append(Paragraph(
    "The Technology Acceptance Model literature reviewed earlier has its own local track record. "
    "Garcia (2017) extended TAM with Philippine-specific predictors, including internet "
    "connectivity experience and social-media influence, to explain Filipino college students' "
    "acceptance of learning management systems, finding these context-specific factors mattered "
    "alongside the classic usefulness/ease-of-use constructs. Liday and Agapito (2020) applied an "
    "extended TAM specifically to LMS adoption by faculty at a Philippine state university, again "
    "finding acceptance was not explained by system quality alone. Both studies reinforce the "
    "conclusion that a monitoring or e-learning tool's local acceptance depends on more than "
    "technical accuracy — a caution AI ExamGuard's own positioning as a transparent, "
    "appealable system is built to take seriously in a Philippine higher-education deployment "
    "context specifically, not as a generic TAM footnote.", body_style))

story.append(Paragraph("Local Deployment of Face-Recognition-Based Monitoring in Philippine Educational Institutions", h2_style))
story.append(Paragraph(
    "Closest in kind to AI ExamGuard's own face-verification component are two independent local "
    "deployments. Grefaldo and Bausa (2025) built a face-recognition attendance-monitoring system "
    "for Pilar National Comprehensive High School, reporting concrete gains — eliminated proxy "
    "attendance, reduced manual-tracking error — while documenting the data-privacy and "
    "access-control obligations (encrypted storage, role-based access) that come with deploying "
    "biometric monitoring in a real Philippine school. Valenzuela, Sandigan, Villar, Litang, "
    "Obligado, and Masungsong (2025), publishing in Caraga State University's peer-reviewed "
    "<i>Advances in Engineering and Information Sciences</i>, independently built a comparable "
    "facial-recognition computer-laboratory attendance system, formally evaluated against the ISO "
    "9126 software-quality model and rating strongly on functionality, reliability, and usability, "
    "while flagging the same recognition-accuracy-under-varying-lighting and privacy concerns as "
    "open challenges rather than solved ones. That two separate Philippine institutions building "
    "independently arrived at the same encryption/access-control/lighting-sensitivity concerns is "
    "strong local corroboration that face-recognition-based monitoring is both technically "
    "deployable and institutionally acceptable in Philippine education specifically when paired "
    "with real privacy safeguards — and the closest available local precedent to AI ExamGuard's "
    "own enrollment/verification pipeline and its retention and audit-logging controls, which "
    "arrived at the same privacy-by-design pairing.", body_style))

# ---- Synthesis ----
story.append(Paragraph("Synthesis", h1_style))
story.append(Paragraph(
    "Read together, the technical and theoretical literature above converge on the same "
    "conclusion from two different directions: an AI proctoring system's real risk is not merely "
    "whether the model detects phones and faces accurately, but what happens when it is wrong, for "
    "whom it is more often wrong, and whether the person being watched has any way to contest "
    "that. The technical literature shows that vision models carry measurable, non-uniform error "
    "across subgroups even at reasonable aggregate accuracy, and that honest generalization "
    "estimates require deliberately harder evaluation, subject-held-out rather than merely "
    "record-held-out, than a single train/test split. The theoretical literature shows that "
    "deterrence justifies monitoring in principle but says nothing about wrongful flags, that "
    "surveillance without disclosure or recourse reproduces a specific, well-documented power "
    "asymmetry, that acceptance depends on perceived legitimacy as much as accuracy, and that "
    "accommodation and surveillance can actively conflict unless accommodation is designed in "
    "rather than bolted on. The local studies reviewed above confirm these are not abstract, "
    "imported concerns: Philippine undergraduates report cheating along the same "
    "attitude/opportunity lines deterrence theory predicts, Philippine LMS-adoption research shows "
    "the same legitimacy-over-accuracy pattern TAM predicts, and a real Philippine high-school "
    "deployment independently arrived at the same privacy-by-design safeguards this project "
    "builds in. AI ExamGuard's concrete departures from a conventional proctoring "
    "build — a disclosed-limitations pre-exam notice, a per-subject fairness audit, "
    "leave-one-subject-out risk-model validation, a real appeals workflow, and server-enforced "
    "accommodation flags — are each a direct response to one of these findings, which is the "
    "basis for positioning the system, in this thesis, as an honestly-evaluated and "
    "transparently-limited alternative to black-box commercial proctoring rather than a "
    "like-for-like clone of one.", body_style))

# ---- References ----
story.append(Paragraph("References", h1_style))

references = [
    "Aguilar, M. G. W. (2021). Academic dishonesty in the Philippines: The case of 21st century "
    "learners and teachers. <i>International Journal of Management, Technology, and Social "
    "Sciences, 6</i>(1), 1–13.",

    "Ahonen, T., Hadid, A., &amp; Pietikäinen, M. (2006). Face description with local binary "
    "patterns: Application to face recognition. <i>IEEE Transactions on Pattern Analysis and "
    "Machine Intelligence, 28</i>(12), 2037–2041. https://doi.org/10.1109/TPAMI.2006.244",

    "Alguacil, M., Herranz-Zarzoso, N., &amp; Perniás, J. C. (2024). Academic dishonesty and "
    "monitoring in online exams: A randomized field experiment. <i>Journal of Computing in Higher "
    "Education, 36</i>, 835–851. https://doi.org/10.1007/s12528-023-09378-x",

    "Beruin, L. C. (2022). Influencing factors and current approaches to academic dishonesty in "
    "the Philippines during COVID-19 pandemic: An overview. <i>Journal of Learning Theory and "
    "Methodology, 3</i>(3), 116–124.",

    "Buolamwini, J., &amp; Gebru, T. (2018). Gender shades: Intersectional accuracy disparities in "
    "commercial gender classification. <i>Proceedings of Machine Learning Research, 81</i>, "
    "77–91.",

    "Cressey, D. R. (1953). <i>Other people's money: A study of the social psychology of "
    "embezzlement</i>. Free Press.",

    "Dai, R., Thomas, M. K. E., &amp; Rawolle, S. (2025). Revisiting Foucault's panopticon: How "
    "does AI surveillance transform educational norms? <i>British Journal of Sociology of "
    "Education</i>. https://doi.org/10.1080/01425692.2025.2501118",

    "Davis, F. D. (1989). Perceived usefulness, perceived ease of use, and user acceptance of "
    "information technology. <i>MIS Quarterly, 13</i>(3), 319–340. "
    "https://doi.org/10.2307/249008",

    "Foucault, M. (1977). <i>Discipline and punish: The birth of the prison</i> (A. Sheridan, "
    "Trans.). Pantheon Books. (Original work published 1975)",

    "Garcia, M. B. (2017). E-learning technology adoption in the Philippines: An investigation of "
    "factors affecting Filipino college students' acceptance of learning management systems. "
    "<i>International Journal of E-Learning and Educational Technologies in the Digital Media, "
    "3</i>(3), 118–130.",

    "Grefaldo, L. H., Jr., &amp; Bausa, M. E. (2025). Attendance monitoring and records management "
    "system for Pilar National Comprehensive High School using face recognition. <i>GSJ: Global "
    "Scientific Journal, 13</i>(2), Aemilianum College Inc., Sorsogon City, Philippines.",

    "Grother, P., Ngan, M., &amp; Hanaoka, K. (2019). <i>Face recognition vendor test (FRVT) part "
    "3: Demographic effects</i> (NISTIR 8280). National Institute of Standards and Technology. "
    "https://doi.org/10.6028/NIST.IR.8280",

    "James, G., Witten, D., Hastie, T., &amp; Tibshirani, R. (2021). <i>An introduction to "
    "statistical learning with applications in R</i> (2nd ed.). Springer.",

    "Jiang, X., Goh, T.-T., Chen, X., Liu, M., &amp; Yang, B. (2023). Investigating university "
    "students' online proctoring acceptance during COVID-19: An extension of the technology "
    "acceptance model. <i>Australasian Journal of Educational Technology, 39</i>(2), 47–64. "
    "https://doi.org/10.14742/ajet.8121",

    "Jocher, G., Chaurasia, A., &amp; Qiu, J. (2023). <i>Ultralytics YOLOv8</i> (Version 8.0.0) "
    "[Computer software]. Ultralytics. https://github.com/ultralytics/ultralytics",

    "Kwapisz, M. B., Ackerman, Y., Nguyen, J., &amp; Rajivan, P. (2025). Surveillance and "
    "disability in online proctored exams: Student perspectives and design implications. "
    "<i>arXiv</i>. https://arxiv.org/abs/2511.10826",

    "Liday, D. M., &amp; Agapito, N. V. (2020). Examining the learning management system adoption "
    "in a state university using the extended technology acceptance model. <i>SARIRIT: The "
    "University Research Journal, 9</i>(1).",

    "Perez, J. A., Zapanta, R. D., Heradura, R. P., &amp; Napicol, S. C. (2025). The drivers of "
    "academic cheating in online learning among Filipino undergraduate students. <i>Ethics &amp; "
    "Behavior, 35</i>(2), 113–128. https://doi.org/10.1080/10508422.2024.2328597",

    "Redmon, J., Divvala, S., Girshick, R., &amp; Farhadi, A. (2016). You only look once: Unified, "
    "real-time object detection. In <i>Proceedings of the IEEE Conference on Computer Vision and "
    "Pattern Recognition</i> (pp. 779–788). IEEE. https://doi.org/10.1109/CVPR.2016.91",

    "Shih, Y.-S., Zhao, Z., Niu, C., Iberg, B., Sharpnack, J., &amp; Baig, M. B. (2024). "
    "AI-assisted gaze detection for proctoring online exams. <i>arXiv</i>. "
    "https://arxiv.org/abs/2409.16923",

    "Valenzuela, J. T., Sandigan, C. R., Villar, C. R., Litang, L. R., Obligado, J. D., Jr., &amp; "
    "Masungsong, R. A. S. (2025). Development and evaluation of a facial recognition-based computer "
    "laboratory attendance monitoring system. <i>Advances in Engineering and Information Sciences, "
    "1</i>(2), 16–25. https://journals.carsu.edu.ph/AEIS",

    "Wu, W., Peng, H., &amp; Yu, S. (2023). YuNet: A tiny millisecond-level face detector. "
    "<i>Machine Intelligence Research, 20</i>(5), 656–665. "
    "https://doi.org/10.1007/s11633-023-1423-y",
]

for ref in references:
    story.append(Paragraph(ref, ref_style))

doc = SimpleDocTemplate(
    OUT_FILE, pagesize=LETTER,
    topMargin=0.9 * inch, bottomMargin=0.9 * inch,
    leftMargin=1.0 * inch, rightMargin=1.0 * inch,
    title="AI ExamGuard - Related Literature (Technical and Theoretical Background)",
)
doc.build(story)
print(f"Wrote {OUT_FILE}")
