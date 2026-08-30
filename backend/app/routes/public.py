import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pymongo.asynchronous.database import AsyncDatabase

from app.config.config import config
from app.config.database import get_db
from app.services.seo import job_url, slugify

router = APIRouter(tags=["Public / SEO"])
_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


async def _get_public_outcome(db: AsyncDatabase, outcome_id: str):
    outcome = await db.outcomes.find_one({"_id": outcome_id, "is_public": True})
    return outcome


def _escape_script_close(raw_json: str) -> str:
    # Prevent a title/description containing "</script>" from breaking out of the JSON-LD block.
    return raw_json.replace("</", "<\\/")


@router.get("/jobs/{outcome_id}")
async def job_canonical_redirect(outcome_id: str, db: AsyncDatabase = Depends(get_db)):
    outcome = await _get_public_outcome(db, outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Job not found")
    return RedirectResponse(url=f"/jobs/{outcome_id}/{slugify(outcome['title'])}", status_code=301)


@router.get("/jobs/{outcome_id}/{slug}", response_class=HTMLResponse)
async def job_page(outcome_id: str, slug: str, request: Request, db: AsyncDatabase = Depends(get_db)):
    outcome = await _get_public_outcome(db, outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Job not found")

    canonical_url = job_url(config.PUBLIC_BASE_URL, outcome["_id"], outcome["title"])
    description = outcome.get("description") or ""
    meta_description = (description[:157] + "...") if len(description) > 160 else description
    created_at = outcome.get("created_at")
    posted_date = created_at.strftime("%B %d, %Y") if created_at else ""

    json_ld = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": outcome["title"],
        "description": description or outcome["title"],
        "identifier": {
            "@type": "PropertyValue",
            "name": "Recruvoskill",
            "value": outcome["_id"],
        },
        "datePosted": created_at.date().isoformat() if created_at else None,
        "hiringOrganization": {
            "@type": "Organization",
            "name": "Recruvoskill",
            "sameAs": config.FRONTEND_BASE_URL,
        },
        # Outcomes are proof-of-work based and not tied to a physical office by default.
        "jobLocationType": "TELECOMMUTE",
        "applicantLocationRequirements": {
            "@type": "Country",
            "name": "Anywhere",
        },
        "employmentType": "CONTRACTOR",
    }
    json_ld = {k: v for k, v in json_ld.items() if v is not None}

    return templates.TemplateResponse(
        request=request,
        name="job.html",
        context={
            "title": outcome["title"],
            "description": description,
            "meta_description": meta_description or outcome["title"],
            "canonical_url": canonical_url,
            "posted_date": posted_date,
            "tasks": outcome.get("tasks") or [],
            "apply_url": f"{config.FRONTEND_BASE_URL.rstrip('/')}/submit-proof/{outcome['_id']}",
            "frontend_base_url": config.FRONTEND_BASE_URL,
            "json_ld": _escape_script_close(json.dumps(json_ld)),
        },
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /jobs/",
        "Allow: /sitemap.xml",
        "Disallow: /admin",
        "Disallow: /reviewer",
        "Disallow: /learning",
        "Disallow: /candidate/applications",
        "Disallow: /dashboard/",
        "Disallow: /evaluation/",
        f"Sitemap: {config.PUBLIC_BASE_URL.rstrip('/')}/sitemap.xml",
    ]
    return "\n".join(lines)


@router.get("/sitemap.xml")
async def sitemap_xml(db: AsyncDatabase = Depends(get_db)):
    cursor = db.outcomes.find({"is_public": True})
    outcomes = await cursor.to_list(length=None)
    urls = "".join(
        f"<url><loc>{job_url(config.PUBLIC_BASE_URL, o['_id'], o['title'])}</loc>"
        f"<lastmod>{o['created_at'].date().isoformat()}</lastmod></url>"
        for o in outcomes
        if o.get("created_at")
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>' \
          f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return PlainTextResponse(content=xml, media_type="application/xml")
