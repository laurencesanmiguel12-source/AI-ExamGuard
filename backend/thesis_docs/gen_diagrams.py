"""One-off script generating the two diagrams embedded in the thesis documentation PDF
(architecture + exam-session workflow). Not part of the app - a docs-generation utility only.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.patches import ConnectionStyle

OUT_DIR = "."


def box(ax, x, y, w, h, text, fc="#eef2f7", ec="#334155", fontsize=10, fontweight="normal"):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.4, edgecolor=ec, facecolor=fc
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
             fontsize=fontsize, fontweight=fontweight, color="#0f172a", wrap=True)


def arrow(ax, xy_from, xy_to, color="#334155", style="-|>", connectionstyle="arc3,rad=0.0"):
    a = FancyArrowPatch(
        xy_from, xy_to, arrowstyle=style, mutation_scale=14,
        color=color, linewidth=1.3, connectionstyle=connectionstyle
    )
    ax.add_patch(a)


def architecture_diagram():
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")

    box(ax, 0.4, 6.2, 4.2, 1.3, "Student / Instructor / Admin\nBrowser (React 19 SPA)", fc="#dbeafe", fontweight="bold")
    box(ax, 5.4, 6.2, 4.2, 1.3, "AI ExamGuard Tab Monitor\nBrowser Extension (Manifest V3)", fc="#dbeafe", fontweight="bold")

    box(ax, 2.4, 4.2, 5.2, 1.2, "FastAPI Backend (REST API)\nJWT auth · role-based access control", fc="#fef3c7", fontweight="bold")

    box(ax, 0.3, 2.2, 3.0, 1.5,
        "AI Monitoring Services\n\nYuNet + LBPH (face)\nYOLOv8s + phone-specialist\n+ pose re-check (objects)\nLogisticRegression (risk)",
        fc="#dcfce7", fontsize=8.5)

    box(ax, 3.6, 2.2, 2.7, 1.5, "PostgreSQL 18\nDatabase\n(17 migrations)", fc="#fee2e2")

    box(ax, 6.6, 2.2, 3.1, 1.5,
        "Local file storage\n(gitignored)\n\nface_models/\nviolation_evidence/",
        fc="#fee2e2", fontsize=8.5)

    box(ax, 2.4, 0.3, 5.2, 1.2, "Docker Compose\n(backend + Postgres 18 containers, dev/deploy)", fc="#ede9fe")

    arrow(ax, (2.5, 6.2), (4.5, 5.4))
    arrow(ax, (7.5, 6.2), (5.9, 5.4))
    arrow(ax, (3.8, 4.2), (2.2, 3.7))
    arrow(ax, (5.0, 4.2), (5.0, 3.7))
    arrow(ax, (6.2, 4.2), (8.0, 3.7))
    arrow(ax, (5.0, 2.2), (5.0, 1.5))

    ax.set_title("AI ExamGuard — System Architecture", fontsize=13, fontweight="bold", pad=14)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/architecture.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def workflow_diagram():
    fig, ax = plt.subplots(figsize=(9, 7.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11.5)
    ax.axis("off")

    steps = [
        (10.6, "Student logs in\n(JWT authentication)"),
        (9.4, "Views available exams\n(course-scoped, roster-narrowed)"),
        (8.2, "Pre-Exam Guidelines modal\n(rules, checklist, agreement)"),
        (7.0, "Browser extension\nconnection check"),
        (5.8, "Face verification\n(skipped if accommodated)"),
        (4.6, "Live exam session:\nanswer autosave · timer\n+ continuous proctoring"),
        (3.2, "Auto-submit on expiry\nor manual submit"),
        (2.0, "Real grading +\nresults / instructor report"),
    ]
    for y, text in steps:
        box(ax, 2.6, y, 4.8, 0.9, text, fc="#dbeafe", fontsize=9)

    for i in range(len(steps) - 1):
        y1 = steps[i][0]
        y2 = steps[i + 1][0]
        arrow(ax, (5.0, y1), (5.0, y2 + 0.9))

    box(ax, 7.9, 4.2, 2.0, 2.2,
        "Proctoring signals\n\nTab switch\nFullscreen exit\nCopy/paste\nFace lost\nPhone/multi-person\n→ risk score",
        fc="#fed7aa", fontsize=7.5)
    arrow(ax, (7.4, 5.0), (7.9, 5.0), color="#c2410c")

    box(ax, 0.1, 4.2, 2.2, 2.2,
        "Violation flagged\nwith evidence\n\n↓\nStudent may appeal\n↓\nInstructor/admin\nreviews & decides",
        fc="#fecaca", fontsize=7.5)
    arrow(ax, (2.6, 5.0), (2.3, 5.0), color="#b91c1c")

    ax.set_title("AI ExamGuard — Exam-Taking Workflow", fontsize=13, fontweight="bold", pad=14)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/workflow.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    architecture_diagram()
    workflow_diagram()
    print("wrote architecture.png and workflow.png")
