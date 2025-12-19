import os
from fastapi import Header

from datetime import date, timedelta, datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlmodel import Session, select

from .db import init_db, get_session
from .models import Conference, Task, Milestone, Person, Assignment, AuditLog, RoleTemplate
from .templates import MILESTONE_TEMPLATE, DEFAULT_TASKS

import json
from dotenv import load_dotenv

load_dotenv(override=True)  # ✅ main.py 맨 위쪽(전역)에 1번만

def get_admin_password() -> str:
    return (os.getenv("ADMIN_PASSWORD") or "").strip()

def require_admin(got_pw: str | None):
    expected = get_admin_password()
    if not expected:
        raise HTTPException(500, "ADMIN_PASSWORD is not set on server (.env not loaded)")
    if not got_pw or got_pw.strip() != expected:
        raise HTTPException(401, "Invalid admin password")

def to_date_obj(v):
    if v is None:
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        # "YYYY-MM-DD"
        return date.fromisoformat(v[:10])
    raise ValueError("Invalid date value")

def sanitize_for_json(obj):
    """
    AuditLog에 넣기 위한 JSON-safe 변환
    - date/datetime -> isoformat
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [sanitize_for_json(x) for x in obj]
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    return str(obj)


def audit(session: Session, conference_id: int, entity_type: str, entity_id: int,
          action: str, before: Dict[str, Any], after: Dict[str, Any]) -> None:
    row = AuditLog(
        conference_id=conference_id,
        actor_person_id=None,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=json.dumps(sanitize_for_json(before), ensure_ascii=False),
        after_json=json.dumps(sanitize_for_json(after), ensure_ascii=False),
        created_at=datetime.utcnow(),
    )
    session.add(row)
    session.commit()


app = FastAPI(title="Conference OS (MVP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# -----------------------
# Role Templates
# -----------------------
DEFAULT_ROLE_TEMPLATES = [
    {"key": "chair", "label": "조직위원장", "sort_order": 10},
    {"key": "vice_chair", "label": "부위원장", "sort_order": 20},
    {"key": "secretary", "label": "총무", "sort_order": 30},
    {"key": "program_chair", "label": "프로그램위원장", "sort_order": 40},
    {"key": "program_member", "label": "프로그램위원", "sort_order": 50},
    {"key": "review_chair", "label": "심사위원장", "sort_order": 60},
    {"key": "reviewer", "label": "심사위원", "sort_order": 70},
    {"key": "pr", "label": "홍보", "sort_order": 80},
    {"key": "sponsor", "label": "후원", "sort_order": 90},
    {"key": "staff", "label": "스태프", "sort_order": 100},
]


@app.post("/role-templates/seed")
def seed_role_templates(session: Session = Depends(get_session)):
    # 이미 있으면 아무 것도 안 함
    existing = session.exec(select(RoleTemplate)).all()
    if existing:
        return {"ok": True, "seeded": False, "count": len(existing)}

    for r in DEFAULT_ROLE_TEMPLATES:
        session.add(RoleTemplate(
            key=r["key"], label=r["label"], sort_order=r["sort_order"],
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        ))
    session.commit()
    return {"ok": True, "seeded": True}


@app.get("/role-templates", response_model=List[RoleTemplate])
def list_role_templates(session: Session = Depends(get_session)):
    rows = session.exec(select(RoleTemplate).order_by(RoleTemplate.sort_order, RoleTemplate.label)).all()
    return rows


@app.post("/role-templates", response_model=RoleTemplate)
def create_role_template(body: dict, session: Session = Depends(get_session)):
    key = (body.get("key") or "").strip()
    label = (body.get("label") or "").strip()
    sort_order = int(body.get("sort_order") or 100)

    if not key or not label:
        raise HTTPException(400, "key/label are required")

    # unique check
    exists = session.exec(select(RoleTemplate).where(RoleTemplate.key == key)).first()
    if exists:
        raise HTTPException(409, "key already exists")

    rt = RoleTemplate(
        key=key, label=label, sort_order=sort_order,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    session.add(rt)
    session.commit()
    session.refresh(rt)
    return rt


@app.patch("/role-templates/{rid}", response_model=RoleTemplate)
def patch_role_template(rid: int, body: dict, session: Session = Depends(get_session)):
    rt = session.get(RoleTemplate, rid)
    if not rt:
        raise HTTPException(404, "RoleTemplate not found")

    if "key" in body:
        key = (body["key"] or "").strip()
        if not key:
            raise HTTPException(400, "key cannot be empty")
        # unique check
        exists = session.exec(select(RoleTemplate).where(RoleTemplate.key == key, RoleTemplate.id != rid)).first()
        if exists:
            raise HTTPException(409, "key already exists")
        rt.key = key

    if "label" in body:
        rt.label = (body["label"] or "").strip()

    if "sort_order" in body:
        rt.sort_order = int(body["sort_order"] or 100)

    rt.updated_at = datetime.utcnow()
    session.add(rt)
    session.commit()
    session.refresh(rt)
    return rt


@app.delete("/role-templates/{rid}")
def delete_role_template(rid: int, session: Session = Depends(get_session)):
    rt = session.get(RoleTemplate, rid)
    if not rt:
        raise HTTPException(404, "RoleTemplate not found")

    # 주의: 이미 Assignment에 쓰인 key를 삭제하면 표시가 깨질 수 있음(프론트는 fallback)
    session.delete(rt)
    session.commit()
    return {"ok": True}


# -----------------------
# Conference
# -----------------------
@app.post("/conferences", response_model=Conference)
def create_conference(payload: dict, session: Session = Depends(get_session)):
    year = payload["year"]
    name = payload["name"]

    # ✅ 1) 중복 체크
    exists = session.exec(
        select(Conference).where(
            Conference.year == year,
            Conference.name == name
        )
    ).first()

    if exists:
        raise HTTPException(
            status_code=409,
            detail="Conference already exists"
        )

    # ✅ 2) 생성
    conf = Conference(
        year=year,
        name=name,
        theme=payload.get("theme"),
        start_date=to_date_obj(payload["start_date"]),
        end_date=to_date_obj(payload["end_date"]),
        venue_name=payload.get("venue_name"),
        venue_city=payload.get("venue_city"),
        timezone=payload.get("timezone") or "Asia/Seoul",
        status=payload.get("status") or "planning",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(conf)
    session.commit()
    session.refresh(conf)

    # 역할 템플릿 시드
    seed_role_templates(session)

    return conf


@app.get("/conferences", response_model=List[Conference])
def list_conferences(session: Session = Depends(get_session)):
    return session.exec(select(Conference).order_by(Conference.year.desc())).all()


@app.get("/conferences/{cid}", response_model=Conference)
def get_conference(cid: int, session: Session = Depends(get_session)):
    conf = session.get(Conference, cid)
    if not conf:
        raise HTTPException(404, "Conference not found")
    return conf

@app.delete("/conferences/{cid}")
def delete_conference(
    cid: int,
    session: Session = Depends(get_session),
    admin_pw: str | None = Header(default=None, alias="X-Admin-Password"),
):
    require_admin(admin_pw)

    conf = session.get(Conference, cid)
    if not conf:
        raise HTTPException(404, "Conference not found")

    # tasks
    tasks = session.exec(select(Task).where(Task.conference_id == cid)).all()
    task_ids = [t.id for t in tasks]

    # assignments
    if task_ids:
        assigns = session.exec(select(Assignment).where(Assignment.task_id.in_(task_ids))).all()
        for a in assigns:
            session.delete(a)

    # milestones
    miles = session.exec(select(Milestone).where(Milestone.conference_id == cid)).all()
    for m in miles:
        session.delete(m)

    # audit logs
    logs = session.exec(select(AuditLog).where(AuditLog.conference_id == cid)).all()
    for l in logs:
        session.delete(l)

    # tasks
    for t in tasks:
        session.delete(t)

    # conference
    session.delete(conf)
    session.commit()
    return {"ok": True}

# -----------------------
# People
# -----------------------
@app.post("/people", response_model=Person)
def create_person(p: Person, session: Session = Depends(get_session)):
    p.created_at = datetime.utcnow()
    p.updated_at = datetime.utcnow()
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@app.patch("/people/{pid}", response_model=Person)
def patch_person(pid: int, body: dict, session: Session = Depends(get_session)):
    p = session.get(Person, pid)
    if not p:
        raise HTTPException(404, "Person not found")
    for k in ["name", "affiliation", "role_title"]:
        if k in body:
            setattr(p, k, (body[k] or "").strip() if isinstance(body[k], str) else body[k])
    p.updated_at = datetime.utcnow()
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@app.delete("/people/{pid}")
def delete_person(pid: int, session: Session = Depends(get_session)):
    p = session.get(Person, pid)
    if not p:
        raise HTTPException(404, "Person not found")
    session.delete(p)
    session.commit()
    return {"ok": True}


@app.get("/people", response_model=List[Person])
def list_people(q: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(Person)
    if q:
        stmt = stmt.where(Person.name.contains(q))
    return session.exec(stmt.order_by(Person.name)).all()


# -----------------------
# Milestones (generate)
# -----------------------
@app.post("/conferences/{cid}/milestones/generate", response_model=List[Milestone])
def generate_milestones(cid: int, create_default_tasks: bool = True, session: Session = Depends(get_session)):
    conf = session.get(Conference, cid)
    if not conf:
        raise HTTPException(404, "Conference not found")

    existing = session.exec(select(Milestone).where(Milestone.conference_id == cid)).all()
    for m in existing:
        session.delete(m)
    session.commit()

    created = []
    for t in MILESTONE_TEMPLATE:
        target = conf.start_date + timedelta(days=t["relative_days"])
        m = Milestone(
            conference_id=cid,
            key=t["key"],
            name=t["name"],
            relative_days=t["relative_days"],
            target_date=target,
            locked=False
        )
        session.add(m)
        created.append(m)

    session.commit()
    for m in created:
        session.refresh(m)

    if create_default_tasks:
        for td in DEFAULT_TASKS:
            task = Task(
                conference_id=cid,
                task_group=td["task_group"],
                name=td["name"],
                status="todo",
                priority="med",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(task)
        session.commit()

    return session.exec(
        select(Milestone).where(Milestone.conference_id == cid).order_by(Milestone.target_date)
    ).all()


@app.get("/conferences/{cid}/milestones", response_model=List[Milestone])
def list_milestones(cid: int, session: Session = Depends(get_session)):
    return session.exec(select(Milestone).where(Milestone.conference_id == cid).order_by(Milestone.target_date)).all()


# -----------------------
# Tasks
# -----------------------
@app.post("/conferences/{cid}/tasks", response_model=Task)
def create_task(cid: int, task: Task, session: Session = Depends(get_session)):
    conf = session.get(Conference, cid)
    if not conf:
        raise HTTPException(404, "Conference not found")

    task.conference_id = cid
    task.created_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()

    session.add(task)
    session.commit()
    session.refresh(task)

    audit(session, cid, "task", task.id, "create", {}, task.model_dump())
    return task


@app.get("/conferences/{cid}/tasks", response_model=List[Task])
def list_tasks(cid: int, group: Optional[str] = None, status: Optional[str] = None,
               session: Session = Depends(get_session)):
    stmt = select(Task).where(Task.conference_id == cid)
    if group:
        stmt = stmt.where(Task.task_group == group)
    if status:
        stmt = stmt.where(Task.status == status)
    return session.exec(stmt.order_by(Task.updated_at.desc())).all()


@app.patch("/tasks/{task_id}", response_model=Task)
def patch_task(task_id: int, payload: dict, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    before = task.model_dump()

    allowed = {"task_group", "name", "description", "status", "priority", "start_date", "due_date"}
    for k, v in payload.items():
        if k not in allowed:
            continue
        if k in ("start_date", "due_date"):
            v = to_date_obj(v) if v else None
        setattr(task, k, v)

    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)

    action = "update"
    if "status" in payload:
        action = "update_status"
    if ("start_date" in payload) or ("due_date" in payload):
        action = "update_dates"

    audit(session, task.conference_id, "task", task.id, action, before, task.model_dump())
    return task


# -----------------------
# Assignment
# -----------------------
@app.post("/tasks/{task_id}/assign", response_model=Assignment)
def assign_task(task_id: int, body: dict, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    person_id = body.get("person_id")
    role_key = (body.get("responsibility") or "chair").strip()

    if not person_id:
        raise HTTPException(400, "person_id is required")

    p = session.get(Person, person_id)
    if not p:
        raise HTTPException(404, "Person not found")

    # ✅ 역할 키가 템플릿에 없으면 자동 생성(편의)
    rt = session.exec(select(RoleTemplate).where(RoleTemplate.key == role_key)).first()
    if not rt:
        session.add(RoleTemplate(
            key=role_key, label=role_key, sort_order=999,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        ))
        session.commit()

    a = Assignment(
        task_id=task_id,
        person_id=person_id,
        responsibility=role_key,
        created_at=datetime.utcnow(),
    )
    session.add(a)
    session.commit()
    session.refresh(a)

    audit(session, task.conference_id, "task", task.id, "assign",
          {"assignees": []},
          {"assignees": [{"person_id": person_id, "responsibility": role_key}]})
    return a


@app.get("/tasks/{task_id}/assignments")
def list_assignments(task_id: int, session: Session = Depends(get_session)):
    """
    ✅ 프론트가 바로 쓰게:
    - person name/affiliation 포함
    - role_label 포함
    """
    assigns = session.exec(select(Assignment).where(Assignment.task_id == task_id)).all()
    if not assigns:
        return []

    role_map = {r.key: r.label for r in session.exec(select(RoleTemplate)).all()}

    out = []
    for a in assigns:
        p = session.get(Person, a.person_id)
        out.append({
            "id": a.id,
            "task_id": a.task_id,
            "person_id": a.person_id,
            "name": p.name if p else "",
            "affiliation": p.affiliation if p else None,
            "responsibility": a.responsibility,
            "role_label": role_map.get(a.responsibility, a.responsibility),
        })
    return out


# -----------------------
# Audit logs
# -----------------------
@app.get("/conferences/{cid}/audit", response_model=List[AuditLog])
def list_audit(cid: int, limit: int = 200, session: Session = Depends(get_session)):
    stmt = select(AuditLog).where(AuditLog.conference_id == cid).order_by(AuditLog.created_at.desc()).limit(limit)
    return session.exec(stmt).all()
