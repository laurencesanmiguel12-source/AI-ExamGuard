"""One-off script generating the marketing one-pager PDF (hero-page copy source for Figma).
Not part of the app - a docs-generation utility only, same convention as gen_diagrams.py /
gen_related_literature.py. Every claim below maps to a real, built, verified feature - no
invented stats, pricing, or capabilities. See MEMORY.md / project history for what's actually
been shipped and tested.
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

OUT_FILE = "AI_ExamGuard_Marketing_OnePager.pdf"

RED = HexColor("#c8192e")
BLUE = HexColor("#1a4fa8")
INK = HexColor("#0f172a")
SLATE = HexColor("#334155")
MUTED = HexColor("#64748b")
CARD_BG = HexColor("#f8fafc")
BORDER = HexColor("#e2e8f0")

styles = getSampleStyleSheet()

kicker_style = ParagraphStyle("Kicker", parent=styles["Normal"], fontSize=9, leading=11,
                               alignment=TA_CENTER, textColor=RED, spaceAfter=4,
                               fontName="Helvetica-Bold")
title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=25, leading=29,
                              alignment=TA_CENTER, textColor=INK, spaceAfter=7)
tagline_style = ParagraphStyle("Tagline", parent=styles["Normal"], fontSize=12.5, leading=16,
                                alignment=TA_CENTER, textColor=SLATE, spaceAfter=3,
                                fontName="Helvetica")
intro_style = ParagraphStyle("Intro", parent=styles["Normal"], fontSize=9.8, leading=13.5,
                              alignment=TA_CENTER, textColor=SLATE, spaceAfter=2)
h1_style = ParagraphStyle("H1X", parent=styles["Heading1"], fontSize=13.5, leading=16,
                           spaceBefore=9, spaceAfter=2, textColor=INK)
h1_sub_style = ParagraphStyle("H1SubX", parent=styles["Normal"], fontSize=8.6, leading=11,
                               textColor=MUTED, spaceAfter=5)
feat_title_style = ParagraphStyle("FeatTitle", parent=styles["Normal"], fontSize=10.3, leading=12.5,
                                   textColor=INK, fontName="Helvetica-Bold", spaceAfter=2)
feat_body_style = ParagraphStyle("FeatBody", parent=styles["Normal"], fontSize=8.6, leading=11.6,
                                  textColor=SLATE)
step_num_style = ParagraphStyle("StepNum", parent=styles["Normal"], fontSize=12, leading=14,
                                 textColor=RED, fontName="Helvetica-Bold", alignment=TA_CENTER)
step_title_style = ParagraphStyle("StepTitle", parent=styles["Normal"], fontSize=9.8, leading=12,
                                   textColor=INK, fontName="Helvetica-Bold", spaceAfter=1)
step_body_style = ParagraphStyle("StepBody", parent=styles["Normal"], fontSize=8.6, leading=11.4,
                                  textColor=SLATE)
cta_style = ParagraphStyle("CTA", parent=styles["Normal"], fontSize=11.5, leading=15,
                            alignment=TA_CENTER, textColor=INK, fontName="Helvetica-Bold",
                            spaceBefore=8, spaceAfter=3)
cta_sub_style = ParagraphStyle("CTASub", parent=styles["Normal"], fontSize=8.8, leading=12,
                                alignment=TA_CENTER, textColor=MUTED)
footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7.3, leading=10,
                               alignment=TA_CENTER, textColor=MUTED, spaceBefore=12)

story = []

# ---- Hero ----
story.append(Paragraph("AI-DRIVEN ACADEMIC INTEGRITY &middot; BUILT FOR PHILIPPINE HIGHER ED", kicker_style))
story.append(Paragraph("AI ExamGuard", title_style))
story.append(Paragraph(
    "Real-time, AI-assisted proctoring for online exams &mdash; face verification, "
    "device detection, and behavior monitoring, with a transparent risk score "
    "instructors can actually see and audit.", tagline_style))
story.append(Paragraph(
    "Free to register. Any school can bring its instructors, courses, and students onto "
    "its own fully isolated space in minutes &mdash; no IT department, no procurement process.",
    intro_style))
story.append(Spacer(1, 0.05 * inch))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=1))

# ---- Why AI ExamGuard: feature grid ----
story.append(Paragraph("Why AI ExamGuard", h1_style))
story.append(Paragraph("Six things that make it a real proctoring system, not a mock-up.", h1_sub_style))

FEATURES = [
    ("Real-Time AI Monitoring",
     "Webcam-based face verification, YOLO-based object/phone detection trained on real exam "
     "footage, and tab/window-switch tracking &mdash; all running live during the exam, not "
     "reviewed after the fact."),
    ("A Risk Score You Can Actually Read",
     "Every session gets a transparent 0&ndash;100 risk score instructors can watch live, "
     "combining a trained model with clear, auditable rules &mdash; never a black box."),
    ("Fair by Design",
     "Built-in accommodations for students who need checks disabled, a full student appeal "
     "workflow on every flagged violation, and instructor review before any consequence."),
    ("Privacy-Conscious by Default",
     "Evidence auto-expires on a fixed retention window, every access is audit-logged, and "
     "admins have direct purge controls &mdash; proctoring without a permanent surveillance archive."),
    ("Your Own Branded Space, Instantly",
     "Register your school and get a fully isolated environment &mdash; your own login page, "
     "your own courses, students, and exams, completely separate from every other school."),
    ("Built for the Whole Exam Lifecycle",
     "Exam creation with bulk CSV question import, subject-scoped instructor assignment, "
     "rosters, live monitoring, and per-question analytics &mdash; not just the proctoring "
     "moment."),
]

feat_cells = []
row = []
for i, (t, b) in enumerate(FEATURES):
    cell = Table(
        [[Paragraph(t, feat_title_style)], [Paragraph(b, feat_body_style)]],
        colWidths=[2.42 * inch],
    )
    cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
    ]))
    row.append(cell)
    if len(row) == 3:
        feat_cells.append(row)
        row = []
if row:
    while len(row) < 3:
        row.append(Spacer(1, 1))
    feat_cells.append(row)

feat_table = Table(feat_cells, colWidths=[2.42 * inch] * 3, hAlign="CENTER")
feat_table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
]))
story.append(feat_table)

# ---- Get started ----
story.append(Paragraph("Get Started in Minutes", h1_style))
story.append(Paragraph("From zero to your first proctored exam.", h1_sub_style))

STEPS = [
    ("1", "Register your school",
     "Enter your school name and set up your admin account. Your school gets its own login "
     "URL immediately &mdash; no waiting, no sales call."),
    ("2", "Add your people",
     "Bring in instructors and assign them to subjects, add your courses, and either add "
     "students directly or share your course list so they can self-register."),
    ("3", "Create your first exam",
     "Build a question bank (or bulk-import via CSV), scope it to a course or a specific "
     "roster, and set a passing score &mdash; AI monitoring runs automatically once it's live."),
    ("4", "Watch it happen, live",
     "Instructors see a live risk feed as students take the exam, then get a full report: "
     "score distribution, pass rate, and per-question accuracy the moment it ends."),
]

step_rows = []
for num, title, body in STEPS:
    step_rows.append([
        Paragraph(num, step_num_style),
        [Paragraph(title, step_title_style), Paragraph(body, step_body_style)],
    ])

step_table = Table(step_rows, colWidths=[0.42 * inch, 6.3 * inch], hAlign="CENTER")
step_table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER),
]))
story.append(step_table)

# ---- CTA ----
story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=2))
story.append(Paragraph("Ready to bring real exam integrity to your school?", cta_style))
story.append(Paragraph("Register your school free &mdash; your own space is ready in minutes.", cta_sub_style))

story.append(Paragraph(
    "Content source for hero-page design &middot; every feature listed is implemented and "
    "tested in the running system, not a concept mock-up.", footer_style))

SimpleDocTemplate(
    OUT_FILE, pagesize=LETTER,
    topMargin=0.4 * inch, bottomMargin=0.4 * inch,
    leftMargin=0.55 * inch, rightMargin=0.55 * inch,
).build(story)
print(f"Wrote {OUT_FILE}")
