from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field


class Conference(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    year: int
    name: str
    theme: Optional[str] = None
    start_date: date
    end_date: date
    venue_name: Optional[str] = None
    venue_city: Optional[str] = None
    timezone: str = "Asia/Seoul"
    status: str = "planning"

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conference_id: int = Field(index=True)

    task_group: str  # PLAN / CFP_PR / PROGRAM / ...
    name: str
    description: Optional[str] = None

    status: str = "todo"      # todo/doing/done/blocked
    priority: str = "med"     # low/med/high

    start_date: Optional[date] = None
    due_date: Optional[date] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Person(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    affiliation: Optional[str] = None

    # 사람 "직함/역할" (예: 조직위원장, 총무 등) - 사람 관리 화면에서 편집
    role_title: Optional[str] = None

    # (선택) 연락처 확장하고 싶으면 여기서부터 추가하되, DB 마이그레이션 필요
    # email: Optional[str] = None
    # phone: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Assignment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True)
    person_id: int = Field(index=True)

    # ✅ 이제 lead/support가 아니라 role_key 저장 (chair, secretary, program_chair, ...)
    responsibility: str = "chair"

    created_at: datetime = Field(default_factory=datetime.utcnow)


class RoleTemplate(SQLModel, table=True):
    """
    ✅ 역할 템플릿(= assignment.responsibility에 들어갈 key와 UI 표시 label)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)       # ex) chair, secretary, program_chair
    label: str                                     # ex) 조직위원장, 총무, 프로그램위원장
    sort_order: int = 100
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Milestone(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conference_id: int = Field(index=True)
    key: str
    name: str
    relative_days: int
    target_date: date
    locked: bool = False


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    conference_id: int = Field(index=True)
    actor_person_id: Optional[int] = Field(default=None)

    entity_type: str
    entity_id: int
    action: str

    # ✅ dict 컬럼 금지(에러났던 부분). JSON 문자열로 저장.
    before_json: str = "{}"
    after_json: str = "{}"

    created_at: datetime = Field(default_factory=datetime.utcnow)
