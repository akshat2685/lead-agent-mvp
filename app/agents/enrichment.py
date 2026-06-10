import os
import time
from datetime import datetime
from ..db import get_session
from ..models import Lead, LeadEnrichment

class EnrichmentEngine:
    def enrich(self, lead_id: int):
        session = get_session()
        try:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                return None
                
            # Check if already enriched
            if lead.enrichment:
                return lead.enrichment

            # Step 1: Email validation (ZeroBounce/Hunter mock)
            email_valid = True if lead.email and "@" in lead.email else False
            
            # Step 2: LinkedIn lookup (Proxycurl mock)
            linkedin_url = f"https://linkedin.com/in/{lead.name.replace(' ', '').lower()}" if lead.name else None
            job_title = "Unknown"
            
            # Step 3: Website scraping (industry, size mock)
            industry = "Education"
            size = "50-200"

            # Step 4: Merge into lead_enrichment table
            enrichment = LeadEnrichment(
                lead_id=lead_id,
                email_valid=email_valid,
                linkedin_profile_url=linkedin_url,
                job_title=job_title,
                company_industry=industry,
                company_size_scraped=size,
                enriched_at=datetime.utcnow()
            )
            session.add(enrichment)
            session.commit()
            
            # Mock rate-limit delay
            time.sleep(0.5)
            
            return enrichment
        finally:
            session.close()
