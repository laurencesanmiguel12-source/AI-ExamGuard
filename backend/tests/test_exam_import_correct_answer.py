"""An imported question must have exactly one correct answer.

Defense panel: "Exam Import should have validation that there is only 1 correct answer."

The old rule was "at least one choice must be marked correct", which accepted a question with two.
That matters because grading is single-select - StudentAnswerService records one chosen choice and
scores it with `is_correct = choice.is_correct` - so two correct choices means two different
answers both earn full marks, silently, with no answer key that explains the result.
"""
import pytest
from fastapi import HTTPException

from app.services.csv_import_service import CSVImportService

HEADER = ("question_text,question_type,points,order_number,"
          "choice_1,choice_1_correct,choice_2,choice_2_correct,choice_3,choice_3_correct\n")


def _csv(*rows):
    return (HEADER + "".join(r + "\n" for r in rows)).encode("utf-8")


def _run(exam, db, body):
    return CSVImportService.import_questions(exam, body, db)


def test_two_correct_answers_are_rejected(db, make_exam):
    exam = make_exam()

    result = _run(exam, db, _csv(
        "What is 2+2?,Multiple Choice,1,1,Four,true,Four again,true,Five,false",
    ))

    assert result.created == 0
    assert len(result.errors) == 1
    assert "exactly one" in result.errors[0].message


def test_the_error_says_how_many_were_marked(db, make_exam):
    exam = make_exam()

    result = _run(exam, db, _csv(
        "Pick one,Multiple Choice,1,1,A,true,B,true,C,true",
    ))

    # "invalid row" would leave someone hunting a spreadsheet for the problem.
    assert "3" in result.errors[0].message


def test_no_correct_answer_is_still_rejected(db, make_exam):
    exam = make_exam()

    result = _run(exam, db, _csv(
        "Pick one,Multiple Choice,1,1,A,false,B,false,C,false",
    ))

    assert result.created == 0
    assert "exactly one" in result.errors[0].message


def test_exactly_one_correct_answer_imports(db, make_exam):
    exam = make_exam()

    result = _run(exam, db, _csv(
        "What is 2+2?,Multiple Choice,1,1,Four,true,Five,false,Six,false",
    ))

    assert result.created == 1
    assert result.errors == []


def test_true_false_is_held_to_the_same_rule(db, make_exam):
    """Both live choice-based types are single-answer; neither may have two correct options."""
    exam = make_exam()

    result = _run(exam, db, _csv(
        "The sky is blue,True/False,1,1,True,true,False,true,,",
    ))

    assert result.created == 0
    assert "exactly one" in result.errors[0].message


def test_identification_questions_are_unaffected(db, make_exam):
    """They carry no choices at all, so the rule must not apply to them."""
    exam = make_exam()

    result = _run(exam, db, _csv(
        "Name the capital of the Philippines,Identification,2,1,,,,,,",
    ))

    assert result.created == 1
    assert result.errors == []


def test_one_bad_question_does_not_block_the_good_ones(db, make_exam):
    exam = make_exam()

    result = _run(exam, db, _csv(
        "Good question,Multiple Choice,1,1,A,true,B,false,C,false",
        "Bad question,Multiple Choice,1,2,A,true,B,true,C,false",
        "Also good,Multiple Choice,1,3,A,false,B,true,C,false",
    ))

    assert result.created == 2
    assert len(result.errors) == 1
    assert result.errors[0].row == 3   # the line number in their spreadsheet


def test_too_few_choices_is_still_its_own_error(db, make_exam):
    exam = make_exam()

    result = _run(exam, db, _csv("Only one option,Multiple Choice,1,1,A,true,,,,"))

    assert "at least 2" in result.errors[0].message
