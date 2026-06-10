from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="viewer") # admin, agent, viewer
    created_at = Column(DateTime, default=datetime.utcnow)

class Lead(Base):
    __tablename__ = 'leads'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone = Column(String)
    email = Column(String)
    company = Column(String)
    raw_text = Column(Text)
    response = Column(Text)
    score = Column(Integer)
    bucket = Column(String)
    status = Column(String, default='new')
    source = Column(String, default='telegram')
    source_timestamp = Column(DateTime, default=datetime.utcnow)
    deduplicated_with_id = Column(Integer, ForeignKey('leads.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    scored_at = Column(DateTime)
    approved_at = Column(DateTime)
    approved_by = Column(String)
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)
    scida_id = Column(String)
    assigned_channel = Column(String)
    call_queued_at = Column(DateTime)
    voice_call_id = Column(String)
    chat_queued_at = Column(DateTime)
    chat_message_id = Column(String)
    chat_delivered_at = Column(DateTime)
    chat_read_at = Column(DateTime)
    chat_replied_at = Column(DateTime)
    chat_reply = Column(Text)
    last_contact_date = Column(DateTime)
    call_duration = Column(Integer)
    call_transcript = Column(Text)
    call_sentiment = Column(String)
    outcome = Column(String)
    outcome_date = Column(DateTime)
    intent = Column(String)
    engagement = Column(String)
    company_size = Column(String)
    voice_script = Column(Text)
    script_generated_at = Column(DateTime)
    zoho_lead_id = Column(String)
    zoho_contact_id = Column(String)
    zoho_account_id = Column(String)
    zoho_deal_id = Column(String)
    zoho_owner_id = Column(String)
    zoho_synced_at = Column(DateTime)
    zoho_sync_status = Column(String)
    zoho_sync_payload = Column(Text)
    outreach_channel = Column(String)
    manual_review_required = Column(Boolean, default=False)
    
    # AI Scoring specific caching fields
    llm_reasoning = Column(Text)
    llm_confidence = Column(Float)
    llm_scored_at = Column(DateTime)

    history = relationship("LeadHistory", back_populates="lead")
    enrichment = relationship("LeadEnrichment", back_populates="lead", uselist=False)

class LeadEnrichment(Base):
    __tablename__ = 'lead_enrichment'
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False)
    email_valid = Column(Boolean)
    linkedin_profile_url = Column(String)
    job_title = Column(String)
    company_industry = Column(String)
    company_size_scraped = Column(String)
    enriched_at = Column(DateTime, default=datetime.utcnow)
    
    lead = relationship("Lead", back_populates="enrichment")

class LeadHistory(Base):
    __tablename__ = 'lead_history'
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False)
    action = Column(String, nullable=False)
    notes = Column(Text)
    changed_by = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    lead = relationship("Lead", back_populates="history")

class Conversion(Base):
    __tablename__ = 'conversions'
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False)
    predicted_score = Column(Integer)
    predicted_bucket = Column(String)
    actual_outcome = Column(String)
    features = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False)
    channel = Column(String) # voice, whatsapp, email
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    lead = relationship("Lead")
