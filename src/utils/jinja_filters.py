"""Jinja2 filters for enterprise PV rendering."""

from __future__ import annotations

from datetime import datetime

from babel.dates import format_date as babel_format_date
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup


def format_date_fr(value) -> str:
    """Format an ISO datetime or datetime object in French locale."""
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    date_part = babel_format_date(value, format="d MMMM yyyy", locale="fr_FR")
    return f"{date_part} à {value.strftime('%H:%M')} UTC"


def format_xof(value) -> str:
    """Format monetary value in XOF with thin-space thousands separator."""
    if value is None:
        return "N/D"
    try:
        return f"{int(float(value)):,} XOF".replace(",", "\u202f")
    except (ValueError, TypeError):
        return str(value)


def format_score(value, unit: str | None = None) -> str:
    """Format a score according to business unit."""
    if value is None:
        return "N/D"
    unit = unit or ""
    if unit == "XOF":
        return format_xof(value)
    if unit == "days":
        return f"{value} j"
    if unit == "score_10":
        try:
            return f"{float(value):.1f}\u202f/\u202f10"
        except (ValueError, TypeError):
            return str(value)
    if unit == "percent":
        return f"{value}\u202f%"
    return str(value)


def confidence_badge(value) -> Markup:
    """Return an HTML badge classed by confidence threshold (Markup for autoescape)."""
    if value is None:
        return Markup('<span class="badge badge--muted">N/D</span>')
    try:
        pct = int(float(value) * 100)
    except (ValueError, TypeError):
        return Markup('<span class="badge badge--muted">?</span>')
    if float(value) >= 0.8:
        css_cls = "badge--green"
    elif float(value) >= 0.5:
        css_cls = "badge--amber"
    else:
        css_cls = "badge--red"
    return Markup(f'<span class="badge {css_cls}">{pct}\u202f%</span>')


def translate_role(role: str) -> str:
    """Translate committee roles to enterprise French labels."""
    mapping = {
        "supplychain": "Supply Chain",
        "supply_chain": "Supply Chain",
        "finance": "Finance",
        "technical": "Technique",
        "budget_holder": "Porteur de budget",
        "audit": "Audit interne",
        "admin": "Administration",
        "legal": "Juridique",
        "security": "Sécurité",
        "pharma": "Pharmacie",
        "observer": "Observateur",
        "secretary": "Secrétariat",
    }
    return mapping.get(role, role.replace("_", " ").capitalize())


def translate_event(event_type: str) -> str:
    """Translate deliberation event types to French labels."""
    mapping = {
        "session_activated": "Session ouverte",
        "member_added": "Membre ajouté",
        "comment_added": "Commentaire délibératif",
        "clarification_requested": "Demande de clarification",
        "clarification_response": "Réponse à clarification",
        "objection": "Objection formelle",
        "session_sealed": "Scellement de la session",
        "deliberation_opened": "Délibération ouverte",
        "deliberation_closed": "Délibération close",
        "member_removed": "Membre retiré",
    }
    return mapping.get(event_type, event_type.replace("_", " ").capitalize())


def build_jinja_env(templates_dir: str) -> Environment:
    """Build Jinja environment with all mandatory BLOC7 filters."""
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    env.filters["format_date_fr"] = format_date_fr
    env.filters["format_xof"] = format_xof
    env.filters["format_score"] = format_score
    env.filters["confidence_badge"] = confidence_badge
    env.filters["translate_role"] = translate_role
    env.filters["translate_event"] = translate_event
    return env
