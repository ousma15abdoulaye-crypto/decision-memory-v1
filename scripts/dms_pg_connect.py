"""Connexion PostgreSQL pour scripts DMS — psycopg v3 uniquement (DMS V4.1.0 : zero ORM).

Evite SQLAlchemy pour les lectures SQL ponctuelles. Alembic (sous-processus) continue
d'utiliser DATABASE_URL ; ce module reconstruit une URL avec mot de passe encode
correctement (caracteres speciaux dans le mot de passe Railway).
"""

from __future__ import annotations

import os
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlunparse


def get_raw_database_url(cli_url: str | None = None) -> str:
    """Lit RAILWAY_DATABASE_URL, DATABASE_URL, ou l'override CLI."""
    url = (
        (cli_url or "").strip()
        or os.environ.get("RAILWAY_DATABASE_URL", "").strip()
        or os.environ.get("DATABASE_URL", "").strip()
    )
    if not url:
        raise ValueError("Definir RAILWAY_DATABASE_URL, DATABASE_URL, ou --db-url.")
    url = url.replace("\r", "").replace("\n", "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


def _parsed_url_to_parts(
    url: str,
) -> tuple[str, str, str, int, str, dict[str, str]]:
    """Parse postgresql URL ; user/mot de passe decode (unquote).

    Si le mot de passe contient un caractere ``@`` non encode, ``urlparse`` ne voit
    plus de hostname — on retombe sur une coupe au **dernier** ``@`` (RFC 3986 :
    userinfo doit etre encode ; en pratique les collages Railway peuvent etre bruts).
    """
    u = url.strip()
    for prefix in ("postgresql+psycopg://", "postgresql://"):
        if u.startswith(prefix):
            u = "postgresql://" + u.split("://", 1)[1]
            break
    if not u.startswith("postgresql://"):
        raise ValueError("URL PostgreSQL invalide : schema attendu postgresql://")

    parsed = urlparse(u)
    if parsed.hostname:
        user = unquote(parsed.username or "")
        password = unquote(parsed.password or "")
        path = (parsed.path or "").lstrip("/")
        dbname = path.split("/")[0] if path else "postgres"
        port = parsed.port or 5432
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        return user, password, dbname, port, parsed.hostname, q

    return _parsed_url_rsplit_userinfo(u)


def _parsed_url_rsplit_userinfo(
    u: str,
) -> tuple[str, str, str, int, str, dict[str, str]]:
    """postgresql://user:password avec @ dans password — dernier @ separe host:port/db."""
    without_scheme = u[len("postgresql://") :]
    query: dict[str, str] = {}
    if "?" in without_scheme:
        without_scheme, qstr = without_scheme.split("?", 1)
        query = dict(parse_qsl(qstr, keep_blank_values=True))
    if "@" not in without_scheme:
        raise ValueError(
            "URL PostgreSQL invalide : hostname manquant "
            "(verifier guillemets PowerShell et un seul /railway en fin de chemin)."
        )
    cred_part, host_part = without_scheme.rsplit("@", 1)
    if not host_part.strip():
        raise ValueError("URL PostgreSQL invalide : partie hote vide.")
    if ":" not in cred_part:
        user, password = cred_part, ""
    else:
        idx = cred_part.index(":")
        user, password = cred_part[:idx], cred_part[idx + 1 :]
    user, password = unquote(user), unquote(password)

    if "/" in host_part:
        hostport, path_rest = host_part.split("/", 1)
        dbname = (path_rest.split("/")[0] or "postgres").strip() or "postgres"
    else:
        hostport = host_part
        dbname = "postgres"

    hostport = hostport.strip()
    if hostport.startswith("["):
        # IPv6 [addr]:port
        bracket_end = hostport.find("]")
        if bracket_end == -1:
            raise ValueError("URL PostgreSQL invalide : IPv6 mal formee.")
        host = hostport[: bracket_end + 1]
        rest = hostport[bracket_end + 1 :].lstrip(":")
        port = int(rest) if rest else 5432
    elif ":" in hostport:
        host, port_str = hostport.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError as exc:
            raise ValueError("URL PostgreSQL invalide : port incorrect.") from exc
    else:
        host, port = hostport, 5432

    host = host.strip("[]")
    return user, password, dbname, port, host, query


def psycopg_connect_kwargs(raw_url: str) -> dict:
    """Parametres pour psycopg.connect() — SQL parametre, pas d'ORM."""
    user, password, dbname, port, host, query = _parsed_url_to_parts(raw_url)
    kwargs: dict = {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
    }
    sslmode = query.get("sslmode")
    if (
        not sslmode
        and host
        and ("proxy.rlwy.net" in host or host.endswith(".railway.app"))
    ):
        kwargs["sslmode"] = "require"
    elif sslmode:
        kwargs["sslmode"] = sslmode
    connect_timeout = query.get("connect_timeout")
    if connect_timeout:
        kwargs["connect_timeout"] = int(connect_timeout)
    return kwargs


def alembic_database_url(raw_url: str) -> str:
    """URL pour variable DATABASE_URL des sous-processus alembic (mot de passe encode)."""
    user, password, dbname, port, host, query = _parsed_url_to_parts(raw_url)
    user_q = quote(user, safe="")
    pass_q = quote(password, safe="")
    # IPv6 littérale : crochets obligatoires dans netloc (sinon URL invalide)
    host_netloc = host
    if ":" in host and not host.startswith("["):
        host_netloc = f"[{host}]"
    netloc = f"{user_q}:{pass_q}@{host_netloc}:{port}"
    path = f"/{dbname}"
    query_str = urlencode(sorted(query.items())) if query else ""
    rebuilt = urlunparse(("postgresql+psycopg", netloc, path, "", query_str, ""))
    return rebuilt


def safe_target_hint(raw_url: str) -> str:
    """Affichage sans secret : ...@host:port/db."""
    try:
        _u, _pw, dbname, port, host, _q = _parsed_url_to_parts(raw_url)
        return f"...@{host}:{port}/{dbname}"
    except Exception:
        return "..."
