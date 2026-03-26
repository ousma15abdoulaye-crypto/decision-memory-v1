"""
Correction automatique du décalage d’horloge pour les clients S3 (R2 / AWS).

Si l’horloge locale est en retard/avance, boto3 signe avec une date fausse et R2
renvoie ``RequestTimeTooSkewed``. On mesure le décalage via l’en-tête ``Date``
d’une réponse HTTPS (Cloudflare), puis on applique un décalage pendant les appels
S3 : soit ``botocore.auth.get_current_datetime`` (anciennes versions botocore),
soit ``datetime.datetime.utcnow`` dans le module ``botocore.auth`` (versions
récentes où SigV4 lit l’heure ainsi). Un patch sur ``compat`` seul ne suffit pas.

Désactiver : ``S3_CLOCK_SKEW_AUTO=0`` (tests, ou confiance totale en NTP local).
"""

from __future__ import annotations

import datetime
import logging
import os
import types
import urllib.error
import urllib.request
from collections.abc import Callable, Generator
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
from typing import Any

logger = logging.getLogger(__name__)

# Réponse légère, même infra que R2 (temps cohérent avec l’écosystème Cloudflare)
_CLOCK_REFERENCE_URL = "https://www.cloudflare.com/"


def get_http_clock_skew_seconds() -> float:
    """
    Estime (temps UTC serveur HTTP ``Date``) - (temps UTC local utilisé par Python).

    Lève urllib.error.URLError si le réseau échoue.
    """
    req = urllib.request.Request(_CLOCK_REFERENCE_URL, method="HEAD")
    with urllib.request.urlopen(req, timeout=15) as resp:
        date_hdr = resp.headers.get("Date")
    if not date_hdr:
        raise ValueError("Réponse HTTP sans en-tête Date")

    server_dt = parsedate_to_datetime(date_hdr)
    if server_dt is None:
        raise ValueError(f"Date HTTP inparseable: {date_hdr!r}")

    if server_dt.tzinfo is not None:
        server_utc = server_dt.astimezone(datetime.UTC).replace(tzinfo=None)
    else:
        server_utc = server_dt

    local_utc = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    return (server_utc - local_utc).total_seconds()


def _datetime_module_proxy_for_auth(skew_seconds: float) -> types.ModuleType:
    """
    Remplace ``import datetime`` dans botocore.auth : sous-classe ``datetime.datetime``
    avec ``utcnow()`` décalé ; ``strptime`` reste celui de la classe de base (SigV4).
    """
    skew = datetime.timedelta(seconds=skew_seconds)

    class SkewedDatetime(datetime.datetime):
        @classmethod
        def utcnow(cls) -> datetime.datetime:
            return super().utcnow() + skew

    proxy = types.ModuleType("datetime")
    proxy.datetime = SkewedDatetime
    return proxy


@contextmanager
def botocore_clock_skew_context(skew_seconds: float) -> Generator[None, None, None]:
    """Applique un décalage fixe à l’horloge utilisée par SigV4 dans botocore."""
    if abs(skew_seconds) < 0.5:
        yield
        return

    import botocore.auth as auth_mod

    if hasattr(auth_mod, "get_current_datetime"):
        orig: Callable[..., Any] = auth_mod.get_current_datetime

        def patched_dt(remove_tzinfo: bool = True) -> datetime.datetime:
            dt = orig(remove_tzinfo=remove_tzinfo)
            return dt + datetime.timedelta(seconds=skew_seconds)

        auth_mod.get_current_datetime = patched_dt  # type: ignore[assignment]
        try:
            logger.info(
                "S3/R2 : correction d’horloge appliquée (skew ≈ %.1f s vs HTTP Date)",
                skew_seconds,
            )
            yield
        finally:
            auth_mod.get_current_datetime = orig  # type: ignore[assignment]
        return

    # Botocore récent : SigV4 utilise ``datetime.datetime.utcnow()`` (import local).
    # En Python 3.11+, ``utcnow`` n’est plus remplaçable sur la classe — on substitue
    # le module ``datetime`` vu par ``botocore.auth``.
    orig_dt_mod = auth_mod.datetime
    auth_mod.datetime = _datetime_module_proxy_for_auth(skew_seconds)
    try:
        logger.info(
            "S3/R2 : correction d’horloge appliquée (skew ≈ %.1f s vs HTTP Date)",
            skew_seconds,
        )
        yield
    finally:
        auth_mod.datetime = orig_dt_mod


@contextmanager
def auto_botocore_clock_skew_from_http() -> Generator[None, None, None]:
    """
    Si ``S3_CLOCK_SKEW_AUTO`` est activé (défaut), mesure le skew et l’applique.
    En cas d’échec réseau, continue sans patch (comportement boto3 par défaut).
    """
    raw = (os.environ.get("S3_CLOCK_SKEW_AUTO") or "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        yield
        return

    try:
        skew = get_http_clock_skew_seconds()
    except (urllib.error.URLError, OSError, ValueError) as e:
        logger.warning(
            "[CORPUS] Détection skew horloge HTTP impossible (%s) — "
            "signature S3 sans correction automatique",
            e,
        )
        yield
        return

    with botocore_clock_skew_context(skew):
        yield
