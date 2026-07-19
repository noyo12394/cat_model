"""Learn CAT schemas (section 14)."""

from __future__ import annotations

from pydantic import BaseModel


class KnowledgeCheck(BaseModel):
    question: str
    options: list[str]
    answer_index: int
    explanation: str


class Lesson(BaseModel):
    lesson_id: str
    order: int
    title: str
    one_sentence: str
    plain_language: str
    technical_definition: str
    formula: str | None = None
    interactive_example: str
    common_mistake: str
    real_world_use: str
    platform_link: str
    knowledge_check: KnowledgeCheck


class LessonSummary(BaseModel):
    lesson_id: str
    order: int
    title: str
    one_sentence: str


class GlossaryTerm(BaseModel):
    term: str
    short: str
    detail: str
    related_lesson_id: str | None = None
