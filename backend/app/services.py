from sqlmodel import Session
from fastapi.encoders import jsonable_encoder
from .models import AuditLog

def audit(session: Session, conference_id: int, entity_type: str, entity_id: int,
          action: str, before: dict, after: dict, actor_person_id=None):
    # ✅ datetime/date 등을 JSON 저장 가능한 형태로 변환
    before_safe = jsonable_encoder(before or {})
    after_safe  = jsonable_encoder(after or {})

    log = AuditLog(
        conference_id=conference_id,
        actor_person_id=actor_person_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=before_safe,
        after_json=after_safe,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
