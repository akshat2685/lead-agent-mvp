import html
import re
import urllib.request
from html.parser import HTMLParser


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.text_parts = []
        self.links = []
        self._tag = ""
        self._skip = False

    def handle_starttag(self, tag, attrs):
        self._tag = tag
        self._skip = tag in ("script", "style", "noscript", "svg")
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name", "").lower() == "description":
            self.description = attrs.get("content", "")
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == self._tag:
            self._tag = ""
            self._skip = False

    def handle_data(self, data):
        if self._skip:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._tag == "title":
            self.title = cleaned
        elif len(cleaned) > 2:
            self.text_parts.append(cleaned)


def analyze_lead_source(lead):
    return analyze_lead_source_result(lead)["message"]


def analyze_lead_source_result(lead):
    source = lead["external_id"] or extract_url(lead["notes"])
    if not source:
        return {"message": "No source URL found for this lead.", "candidate": ""}
    if not source.startswith(("http://", "https://")):
        source = f"https://{source}"
    try:
        page = fetch_page(source)
        return summarize_page(lead, source, page)
    except Exception as exc:
        return {"message": fallback_guidance(lead, source, str(exc)), "candidate": ""}


def fetch_page(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 LeadAgentMVP/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read(250000).decode("utf-8", errors="ignore")
    parser = PageParser()
    parser.feed(raw)
    text = html.unescape(" ".join(parser.text_parts))
    return {
        "title": html.unescape(parser.title),
        "description": html.unescape(parser.description),
        "text": text[:5000],
        "links": parser.links[:100],
    }


def summarize_page(lead, source, page):
    text = " ".join([page["title"], page["description"], page["text"], " ".join(page["links"])])
    emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
    phones = sorted(set(re.findall(r"\+?\d[\d\s().-]{7,}\d", text)))
    contact_links = [link for link in page["links"] if any(word in link.lower() for word in ("contact", "about", "team", "linkedin", "mailto:"))][:5]
    signals = lead_signals(text)
    recommendation = recommendation_for(lead, emails, phones, contact_links, signals)
    candidate = best_candidate(phones, emails, contact_links, source)
    lines = [
        f"Web research for lead #{lead['id']}: {lead['name']}",
        f"Source: {source}",
        "",
        f"Title: {page['title'] or 'Not found'}",
    ]
    if page["description"]:
        lines.extend(["", f"Description: {page['description'][:450]}"])
    lines.extend(
        [
            "",
            "Contact signals:",
            f"- Emails: {', '.join(emails[:3]) if emails else 'None found'}",
            f"- Phones: {', '.join(phones[:3]) if phones else 'None found'}",
            f"- Useful links: {', '.join(contact_links) if contact_links else 'None found'}",
            "",
            "Buying/fit signals:",
            f"- {', '.join(signals) if signals else 'No strong page signals found'}",
            "",
            "Recommended next step:",
            recommendation,
        ]
    )
    if candidate:
        lines.extend(["", f"Suggested contact update: {candidate}"])
    return {"message": "\n".join(lines), "candidate": candidate}


def fallback_guidance(lead, source, error):
    return "\n".join(
        [
            f"Could not browse lead #{lead['id']} automatically.",
            f"Source: {source}",
            f"Reason: {error}",
            "",
            "Manual research checklist:",
            "- Open the source URL",
            "- Look for email, phone, website, LinkedIn, or contact page",
            "- If contact is found, use: set phone for lead ID ...",
            "- If no route exists, use: no contact found for lead ID",
        ]
    )


def lead_signals(text):
    lowered = text.lower()
    signals = []
    checks = [
        ("voice agent", "Voice agent interest"),
        ("automation", "Automation interest"),
        ("appointment", "Appointment/booking need"),
        ("lead generation", "Lead generation interest"),
        ("customer support", "Customer support automation"),
        ("asap", "Urgent language"),
        ("pricing", "Pricing intent"),
        ("demo", "Demo intent"),
    ]
    for needle, label in checks:
        if needle in lowered:
            signals.append(label)
    return signals[:5]


def recommendation_for(lead, emails, phones, contact_links, signals):
    if phones:
        return "Phone found. Add it to the lead, then move to call approval."
    if emails:
        return "Email found. Add it as contact info or use manual outreach before calling."
    if contact_links:
        return "Open the contact/team link and capture phone, email, or decision-maker profile."
    if signals and lead["priority"] == "Hot":
        return "High-priority lead, but no direct contact found. Research manually before rejecting."
    return "No useful contact found from automatic browsing. Consider marking no contact found after manual check."


def best_candidate(phones, emails, contact_links, source):
    if phones:
        return phones[0]
    if emails:
        return emails[0]
    absolute_links = [absolute_url(link, source) for link in contact_links]
    return absolute_links[0] if absolute_links else ""


def absolute_url(link, source):
    if link.startswith(("http://", "https://", "mailto:")):
        return link
    if link.startswith("/"):
        match = re.match(r"https?://[^/]+", source)
        return f"{match.group(0)}{link}" if match else link
    return link


def extract_url(text):
    match = re.search(r"https?://\S+|[A-Za-z0-9.-]+\.[A-Za-z]{2,}/\S*", text or "")
    return match.group(0) if match else ""
