"""One-off script generating the system test script / user walkthrough PDF (UAT checklist +
usage guide, combined). Not part of the app - a docs-generation utility only, same convention as
gen_diagrams.py / gen_marketing_onepager.py / gen_related_literature.py. Every step below maps to
a real route/page in the running system (see backend/app/routes/*.py, frontend/src/pages/*) - no
invented screens or endpoints.
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)

OUT_FILE = "AI_ExamGuard_Test_Script.pdf"

RED = HexColor("#c8192e")
BLUE = HexColor("#1a4fa8")
INK = HexColor("#0f172a")
SLATE = HexColor("#334155")
MUTED = HexColor("#64748b")
HEAD_BG = HexColor("#0f172a")
ROW_BG = HexColor("#f8fafc")
BORDER = HexColor("#e2e8f0")

styles = getSampleStyleSheet()

title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=22, leading=26,
                              alignment=TA_CENTER, textColor=INK, spaceAfter=6)
kicker_style = ParagraphStyle("Kicker", parent=styles["Normal"], fontSize=9, leading=11,
                               alignment=TA_CENTER, textColor=RED, spaceAfter=4,
                               fontName="Helvetica-Bold")
intro_style = ParagraphStyle("Intro", parent=styles["Normal"], fontSize=9.5, leading=13.5,
                              alignment=TA_LEFT, textColor=SLATE, spaceAfter=4)
section_style = ParagraphStyle("Section", parent=styles["Heading1"], fontSize=14, leading=17,
                                spaceBefore=14, spaceAfter=2, textColor=INK)
section_sub_style = ParagraphStyle("SectionSub", parent=styles["Normal"], fontSize=8.6, leading=11,
                                    textColor=MUTED, spaceAfter=6, fontName="Helvetica-Oblique")
cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8.3, leading=11, textColor=SLATE)
cell_bold_style = ParagraphStyle("CellBold", parent=styles["Normal"], fontSize=8.3, leading=11,
                                  textColor=INK, fontName="Helvetica-Bold")
head_cell_style = ParagraphStyle("HeadCell", parent=styles["Normal"], fontSize=8.3, leading=11,
                                  textColor=HexColor("#ffffff"), fontName="Helvetica-Bold")
footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7.3, leading=10,
                               alignment=TA_CENTER, textColor=MUTED, spaceBefore=10)

COL_WIDTHS = [0.32 * inch, 2.55 * inch, 2.85 * inch, 0.55 * inch]
HEADER_ROW = [
    Paragraph("#", head_cell_style),
    Paragraph("Action (what to do)", head_cell_style),
    Paragraph("Expected result", head_cell_style),
    Paragraph("Pass?", head_cell_style),
]


def section_table(rows):
    data = [HEADER_ROW]
    for i, (action, expected) in enumerate(rows, start=1):
        data.append([
            Paragraph(str(i), cell_bold_style),
            Paragraph(action, cell_style),
            Paragraph(expected, cell_style),
            Paragraph("&#9744;", cell_style),  # checkbox glyph
        ])
    t = Table(data, colWidths=COL_WIDTHS, repeatRows=1, hAlign="CENTER")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for r in range(1, len(data)):
        if r % 2 == 0:
            style.append(("BACKGROUND", (0, r), (-1, r), ROW_BG))
    t.setStyle(TableStyle(style))
    return t


story = []

# ---- Title ----
story.append(Paragraph("MANUAL TEST SCRIPT &amp; USER WALKTHROUGH", kicker_style))
story.append(Paragraph("AI ExamGuard", title_style))
story.append(Paragraph(
    "This document is both a step-by-step guide to using AI ExamGuard and a manual test "
    "script: work through each numbered step in order, perform the action against a real "
    "(or staging) deployment, and check the box once the actual result matches the expected "
    "result. Every step below corresponds to a real page or API route in the running system "
    "&mdash; nothing here describes planned or mocked functionality. Steps are grouped by the "
    "role that performs them: Admin, Instructor, Student, then a final cross-cutting section "
    "covering multi-tenant isolation and accommodation checks that don't belong to a single role.",
    intro_style))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=4))

# ---- Admin ----
story.append(Paragraph("Part A &mdash; Admin", section_style))
story.append(Paragraph("Onboarding a school and running it day to day.", section_sub_style))
story.append(section_table([
    ("Go to /schools/register and register a new school (school name + your admin account).",
     "School is created with its own login URL (schoolSlug); you land on the admin login/dashboard for that school only."),
    ("Log in at /&lt;schoolSlug&gt;/login with the admin account.",
     "Admin Dashboard loads with navigation for Courses, Subjects, Students, Instructors, Reports, and Analytics."),
    ("Create a Subject on the Subjects page.",
     "Subject appears in the subject list immediately, scoped to this school."),
    ("Create a Course on the Courses page.",
     "Course appears in the course list; can be linked to a subject."),
    ("Add an Instructor on the Instructors page and assign them to the Subject created above.",
     "Instructor is saved with that subject assignment; an instructor with no subject assignment cannot author exams in it (see Part B, step 2)."),
    ("Add a Student on the Students page.",
     "Student is saved and can log in at /&lt;schoolSlug&gt;/login with the issued credentials."),
    ("On a student's record, set an accommodation (e.g. tick skip_face_check or skip_object_check, or set extra_time_minutes / accommodation_notes).",
     "Change is saved to the student; an UPDATE_ACCOMMODATION entry is written to the audit log (see next step)."),
    ("Open the Audit Log.",
     "The UPDATE_ACCOMMODATION entry from the previous step appears, scoped to this school's activity only."),
    ("Open the Analytics tab (school-wide view).",
     "School-wide pass-rate and risk aggregates display, plus a per-instructor breakdown that flags outliers by pass rate or risk score."),
    ("Open Retention settings and run a purge preview (do not confirm the purge unless you intend to delete evidence).",
     "Preview lists violation evidence older than the retention window that is eligible for deletion; confirming purge removes exactly that evidence, nothing newer."),
]))

story.append(PageBreak())

# ---- Instructor ----
story.append(Paragraph("Part B &mdash; Instructor", section_style))
story.append(Paragraph("Authoring an exam and monitoring/reviewing a live sitting.", section_sub_style))
story.append(section_table([
    ("Log in as the instructor created in Part A.",
     "Instructor Dashboard loads, scoped to this instructor's assigned subjects/courses only."),
    ("Create an exam under a subject you are assigned to; then try creating one under a subject you are NOT assigned to.",
     "First exam saves normally. Second attempt is rejected (403) &mdash; exam authorship requires the instructor-subject assignment, it is not admin-equivalent."),
    ("On the exam's Content page, add questions manually, then bulk-import a question set via CSV.",
     "Manually added questions and choices appear immediately; a valid CSV imports all rows, and a malformed CSV is rejected with row-level errors, not a silent partial import."),
    ("Build the exam roster on the Exam Roster page.",
     "Only students added to the roster can open the take-exam link for this exam."),
    ("Have a test student take the exam (or open the take-exam link yourself) while watching the Live Sessions view.",
     "Live risk feed updates in real time as the session runs, and any triggered violations (tab switch, face lost, object detected) appear on the feed within a few seconds."),
    ("Open the evidence for one logged violation.",
     "Evidence snapshot loads and is viewable, until it ages out under the retention window from Part A."),
    ("Have the test student file an appeal on a violation (Part C, step 5), then review it here.",
     "Appeal is visible for review; approving or denying it records the decision against the violation."),
    ("After the session ends, open the exam's Report.",
     "Report shows score distribution, pass rate, per-question accuracy, a violation-type breakdown, and the risk-score distribution for this exam."),
    ("Open Analytics (instructor view).",
     "Cross-exam summary covers this instructor's own exams only &mdash; no other instructor's exam data appears."),
]))

story.append(PageBreak())

# ---- Student ----
story.append(Paragraph("Part C &mdash; Student", section_style))
story.append(Paragraph("Taking a proctored exam end to end.", section_sub_style))
story.append(section_table([
    ("Log in with the credentials the admin issued in Part A (or self-register at /&lt;schoolSlug&gt;/register if the school allows it).",
     "Account authenticates and lands on the student dashboard."),
    ("Complete Face Enrollment before attempting an exam (skip this step for a student with the skip_face_check accommodation set in Part A).",
     "Enrollment is saved and required before the first exam attempt; an accommodated student is not blocked by a missing enrollment."),
    ("Open the take-exam link for the exam built in Part B and start the session.",
     "Webcam face verification, the tab-monitoring browser extension, and object (phone) detection all activate at session start."),
    ("During the exam, switch away from the tab, and (unless accommodated) hold a phone in frame.",
     "Each triggers a logged violation visible to the instructor's Live Sessions view; an accommodated student with skip_object_check set does NOT get a violation for the phone."),
    ("Finish and submit the exam, then review a violation you believe was wrongly flagged and file an appeal.",
     "Results page shows your score; the appeal is recorded and becomes visible to the instructor for review in Part B."),
]))

story.append(PageBreak())

# ---- Cross-cutting ----
story.append(Paragraph("Part D &mdash; Cross-Cutting Checks", section_style))
story.append(Paragraph("Multi-tenant isolation, accommodations, and UI conventions that span all three roles.", section_sub_style))
story.append(section_table([
    ("Register a second school (School B) with its own admin, at least one exam, and one student attempt.",
     "School B gets its own schoolSlug and login URL, fully separate from School A."),
    ("While logged in as School A's admin, check Reports, Analytics, and the Audit Log.",
     "Only School A's data appears in all three views &mdash; none of School B's exams, students, or activity leak through."),
    ("As School A's instructor, attempt to view or grade an exam belonging to School B (e.g. by editing the exam ID in the URL).",
     "Request is rejected; cross-tenant access is not possible regardless of URL manipulation."),
    ("Trigger any destructive admin action (e.g. deleting a student).",
     "The app's own ConfirmDialog appears for confirmation &mdash; never a native browser confirm()/alert() popup."),
    ("Re-run the retention purge preview from Part A after some time has passed.",
     "Only evidence that has newly aged past the retention window appears as newly eligible; nothing purged earlier reappears."),
]))

story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=6, spaceAfter=2))
story.append(Paragraph(
    "Every step above targets a real page or API route in the running system (see backend/app/routes/ "
    "and frontend/src/pages/) &mdash; no step describes planned or mocked functionality.",
    footer_style))

SimpleDocTemplate(
    OUT_FILE, pagesize=LETTER,
    topMargin=0.5 * inch, bottomMargin=0.5 * inch,
    leftMargin=0.55 * inch, rightMargin=0.55 * inch,
).build(story)
print(f"Wrote {OUT_FILE}")
