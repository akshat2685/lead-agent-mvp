import json
from datetime import datetime, timedelta
from .llm_client import llm
from ..db import get_session
from ..models import Lead
from .enrichment import EnrichmentEngine

SYSTEM_PROMPT = """You are an admissions sales expert. Score this lead for an education sales team.

Lead Data:
- Name: {name}
- Source: {source}
- Notes: {notes}
- Intent Signals: {intent_signals}
- Prospect Type: {prospect_type}
- Engagement History: {engagement}
- Fit Indicators: {fit}

Return ONLY a JSON object:
{
  "score": <0-100 integer>,
  "bucket": "Hot" | "Warm" | "Nurture" | "Cold",
  "confidence": <0.0-1.0>,
  "reasoning": "<2 sentence explanation>"
}

Hot = 80-100, Warm = 60-79, Nurture = 40-59, Cold = 0-39"""

class LeadScorer:
    def score_lead(self, lead_data: dict) -> dict:
        lead_id = lead_data.get("id")
        
        # Check cache (24 hours)
        session = get_session()
        try:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if lead and lead.llm_scored_at and lead.llm_scored_at > datetime.utcnow() - timedelta(hours=24):
                return {
                    "score": lead.score,
                    "bucket": lead.bucket,
                    "confidence": lead.llm_confidence,
                    "reasoning": lead.llm_reasoning
                }
        finally:
            session.close()

        # Step 5: Feed enriched data to scoring engine
        enrichment_data = ""
        if lead_id:
            enricher = EnrichmentEngine()
            enrichment = enricher.enrich(lead_id)
            if enrichment:
                enrichment_data = f"\nEnriched Job Title: {enrichment.job_title}\nEnriched Industry: {enrichment.company_industry}\nEnriched Size: {enrichment.company_size_scraped}"

        # Build prompt
        prompt = SYSTEM_PROMPT.format(
            name=lead_data.get("name", "Unknown"),
            source=lead_data.get("source", "Unknown"),
            notes=lead_data.get("raw_text", "") + enrichment_data,
            intent_signals=lead_data.get("intent", ""),
            prospect_type="Education Lead",
            engagement=lead_data.get("engagement", ""),
            fit=lead_data.get("company_size", "")
        )

        result = llm.call(prompt, "Score this lead.", require_json=True)
        
        # Cache the result
        if lead_id:
            session = get_session()
            try:
                lead = session.query(Lead).filter(Lead.id == lead_id).first()
                if lead:
                    lead.score = result.get("score", 0)
                    lead.bucket = result.get("bucket", "Cold")
                    lead.llm_confidence = result.get("confidence", 0.0)
                    lead.llm_reasoning = result.get("reasoning", "")
                    lead.llm_scored_at = datetime.utcnow()
                    
                    if lead.llm_confidence < 0.7:
                        lead.manual_review_required = True
                        lead.status = "pending_approval"
                    
                    session.commit()
            finally:
                session.close()
                
        return result
