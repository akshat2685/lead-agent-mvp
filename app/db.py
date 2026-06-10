import os
import json
from datetime import datetime
from sqlalchemy import create_engine, func, or_, and_
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base, Lead, LeadHistory, Conversion, User

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///lead_agent.db")

# Setup connection pooling for PostgreSQL, omit for SQLite
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL, 
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10"))
    )
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def init_database():
    Base.metadata.create_all(engine)

def get_session():
    return Session()

def insert_lead(payload):
    session = get_session()
    try:
        lead = Lead(**{k: v for k, v in payload.items() if hasattr(Lead, k)})
        session.add(lead)
        session.commit()
        session.refresh(lead)
        return lead.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def update_lead(lead_id, changes):
    session = get_session()
    try:
        lead = session.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return 0
        for key, value in changes.items():
            if hasattr(lead, key):
                setattr(lead, key, value)
        session.commit()
        return 1
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def query_lead(lead_id):
    session = get_session()
    try:
        lead = session.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            # Convert to dict for legacy compatibility
            return {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
        return None
    finally:
        session.close()

def find_duplicate(lead_data, source):
    session = get_session()
    try:
        phone = lead_data.get("phone")
        email = lead_data.get("email")
        query = session.query(Lead).filter(Lead.source != source)
        
        conditions = []
        if phone:
            conditions.append(Lead.phone == phone)
        if email:
            conditions.append(Lead.email == email)
            
        if not conditions:
            return None
            
        duplicate = query.filter(or_(*conditions)).order_by(Lead.created_at.desc()).first()
        if duplicate:
            return {c.name: getattr(duplicate, c.name) for c in duplicate.__table__.columns}
        return None
    finally:
        session.close()

def log_action(lead_id, action, notes="", changed_by="system"):
    session = get_session()
    try:
        history = LeadHistory(lead_id=lead_id, action=action, notes=notes, changed_by=changed_by)
        session.add(history)
        session.commit()
        return 1
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_lead_history(lead_id):
    session = get_session()
    try:
        histories = session.query(LeadHistory).filter(LeadHistory.lead_id == lead_id).order_by(LeadHistory.timestamp.desc()).all()
        return [{"action": h.action, "notes": h.notes, "changed_by": h.changed_by, "timestamp": h.timestamp} for h in histories]
    finally:
        session.close()

def list_pending_review():
    session = get_session()
    try:
        leads = session.query(Lead).filter(
            or_(
                Lead.status.in_(['pending_approval', 'reviewed']),
                Lead.manual_review_required == True
            )
        ).order_by(Lead.scored_at.desc(), Lead.created_at.desc()).all()
        return [{c.name: getattr(l, c.name) for c in l.__table__.columns} for l in leads]
    finally:
        session.close()

def count(query_placeholder=None):
    # Fallback for old count calls, might need refactoring if passed raw SQL
    session = get_session()
    try:
        return session.query(Lead).count()
    finally:
        session.close()

def fetch_all(query_placeholder=None):
    # Dummy fallback to avoid crashing old raw SQL, but should be replaced
    return []
