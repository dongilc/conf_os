from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint


# =========================
# Conference
# =========================
class Conference(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("year", "name", name="uq_conference_year_name"),
    )

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

    # 🔥 관계 (List 쓰지 말 것!)
    tasks: list["Task"] = Relationship(
        back_populates="conference",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    milestones: list["Milestone"] = Relationship(
        back_populates="conference",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    audit_logs: list["AuditLog"] = Relationship(
        back_populates="conference",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


# =========================
# Task
# =========================
class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conference_id: int = Field(foreign_key="conference.id", index=True)

    task_group: str
    name: str
    description: Optional[str] = None

    status: str = "todo"
    priority: str = "med"

    start_date: Optional[date] = None
    due_date: Optional[date] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    conference: Optional[Conference] = Relationship(back_populates="tasks")
    assignments: list["Assignment"] = Relationship(
        back_populates="task",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


# =========================
# Person
# =========================
class Person(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    affiliation: Optional[str] = None
    role_title: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =========================
# Assignment
# =========================
class Assignment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    person_id: int = Field(index=True)

    responsibility: str = "chair"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    task: Optional[Task] = Relationship(back_populates="assignments")


# =========================
# RoleTemplate
# =========================
class RoleTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    label: str
    sort_order: int = 100

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =========================
# Milestone
# =========================
class Milestone(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conference_id: int = Field(foreign_key="conference.id", index=True)

    key: str
    name: str
    relative_days: int
    target_date: date
    locked: bool = False

    conference: Optional[Conference] = Relationship(back_populates="milestones")


# =========================
# AuditLog
# =========================
class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    conference_id: int = Field(foreign_key="conference.id", index=True)
    actor_person_id: Optional[int] = Field(default=None)

    entity_type: str
    entity_id: int
    action: str

    before_json: str = "{}"
    after_json: str = "{}"

    created_at: datetime = Field(default_factory=datetime.utcnow)

    conference: Optional[Conference] = Relationship(back_populates="audit_logs")
