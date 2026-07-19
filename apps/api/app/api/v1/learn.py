"""Learn CAT API (section 14)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.learn import GlossaryTerm, Lesson, LessonSummary
from app.services.learn import (
    get_glossary_term,
    get_lesson,
    list_glossary,
    list_lessons,
)

router = APIRouter(prefix="/learn", tags=["learn"])


@router.get("/lessons", response_model=list[LessonSummary])
def get_lessons() -> list[LessonSummary]:
    return list_lessons()


@router.get("/lessons/{lesson_id}", response_model=Lesson)
def get_lesson_detail(lesson_id: str) -> Lesson:
    lesson = get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.get("/glossary", response_model=list[GlossaryTerm])
def get_glossary() -> list[GlossaryTerm]:
    return list_glossary()


@router.get("/glossary/{term}", response_model=GlossaryTerm)
def get_term(term: str) -> GlossaryTerm:
    entry = get_glossary_term(term)
    if entry is None:
        raise HTTPException(status_code=404, detail="Glossary term not found")
    return entry
