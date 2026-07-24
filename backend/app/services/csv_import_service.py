import csv
import io

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.choice import Choice
from app.models.exam import Exam
from app.models.question import Question
from app.schemas.csv_import import CSVImportResponse, CSVImportRowError

VALID_QUESTION_TYPES = {"Multiple Choice", "True/False", "Identification"}
MAX_CHOICE_COLUMNS = 6
TRUE_VALUES = {"true", "yes", "1"}
FALSE_VALUES = {"false", "no", "0"}


def _parse_bool(value: str):
    v = value.strip().lower()
    if v in TRUE_VALUES:
        return True
    if v in FALSE_VALUES:
        return False
    return None


class CSVImportService:

    @staticmethod
    def import_questions(exam: Exam, file_bytes: bytes, db: Session) -> CSVImportResponse:

        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded.")

        reader = csv.DictReader(io.StringIO(text))

        errors = []
        staged = []

        for i, row in enumerate(reader):
            row_number = i + 2  # header is row 1
            row_errors = []

            question_text = (row.get("question_text") or "").strip()
            if not question_text:
                row_errors.append("question_text is required")

            question_type = (row.get("question_type") or "").strip()
            if question_type not in VALID_QUESTION_TYPES:
                row_errors.append(
                    f"question_type must be one of {sorted(VALID_QUESTION_TYPES)}, got '{question_type}'"
                )

            points = None
            points_raw = (row.get("points") or "").strip()
            try:
                points = int(points_raw)
                if points <= 0:
                    row_errors.append("points must be a positive integer")
            except ValueError:
                row_errors.append("points must be a positive integer")

            order_raw = (row.get("order_number") or "").strip()
            if order_raw:
                try:
                    order_number = int(order_raw)
                except ValueError:
                    row_errors.append("order_number must be an integer if provided")
                    order_number = i + 1
            else:
                order_number = i + 1

            choices = []
            if question_type != "Identification":
                for n in range(1, MAX_CHOICE_COLUMNS + 1):
                    text_val = (row.get(f"choice_{n}") or "").strip()
                    if not text_val:
                        continue
                    correct_raw = (row.get(f"choice_{n}_correct") or "").strip()
                    is_correct = _parse_bool(correct_raw) or False
                    choices.append((text_val, is_correct))

                if len(choices) < 2:
                    row_errors.append("at least 2 non-blank choices are required")
                elif not any(is_correct for _text, is_correct in choices):
                    row_errors.append("at least one choice must be marked correct")

            if row_errors:
                errors.append(CSVImportRowError(row=row_number, message="; ".join(row_errors)))
                continue

            staged.append({
                "question_text": question_text,
                "question_type": question_type,
                "points": points,
                "order_number": order_number,
                "choices": choices,
            })

        created = 0

        if staged:
            try:
                for item in staged:
                    question = Question(
                        exam_id=exam.id,
                        question_text=item["question_text"],
                        question_type=item["question_type"],
                        points=item["points"],
                        order_number=item["order_number"],
                    )
                    db.add(question)
                    db.flush()

                    for choice_text, is_correct in item["choices"]:
                        db.add(Choice(
                            question_id=question.id,
                            choice_text=choice_text,
                            is_correct=is_correct,
                        ))
                    created += 1

                db.commit()
            except Exception as e:
                db.rollback()
                return CSVImportResponse(
                    created=0,
                    errors=errors + [CSVImportRowError(row=0, message=f"Import failed: {e}")]
                )

        return CSVImportResponse(created=created, errors=errors)
