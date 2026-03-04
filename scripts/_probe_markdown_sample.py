"""
Probe chirurgical : extrait UNIQUEMENT les 2 premières pages d'un PDF
pour inspecter le format Markdown réel sans gaspiller de crédits.

Sauvegarde dans data/imports/m5/cache/sample_probe_bougouni.md

Usage :
    $env:LLAMADMS = "..."; python scripts/_probe_markdown_sample.py
"""

import asyncio
import io
import os
import sys
from pathlib import Path

FILE_PATH = Path(
    "data/imports/m5/Mercuriale des prix 2023/Bulletin_Result_Bougouni2023.pdf"
)
CACHE_DIR = Path("data/imports/m5/cache")
OUT_FILE = CACHE_DIR / "sample_probe_bougouni.md"


async def _extract_2pages(file_path: Path, api_key: str) -> str:
    import httpx
    from llama_cloud import AsyncLlamaCloud
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(file_path))
    writer = PdfWriter()
    for i in range(min(2, len(reader.pages))):
        writer.add_page(reader.pages[i])
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)

    http_client = httpx.AsyncClient(verify=False)
    client = AsyncLlamaCloud(api_key=api_key, http_client=http_client)

    file_obj = await client.files.create(file=buf, purpose="parse")
    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier="agentic",
        version="latest",
        expand=["markdown_full"],
    )
    return result.markdown_full or ""


def main() -> None:
    api_key = os.environ.get("LLAMADMS", "").strip()
    if not api_key:
        print("ERREUR : LLAMADMS absent")
        sys.exit(1)

    if not FILE_PATH.exists():
        print(f"PDF introuvable : {FILE_PATH}")
        sys.exit(1)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Extraction 2 pages · {FILE_PATH.name} · coût ~6 crédits...")

    markdown = asyncio.run(_extract_2pages(FILE_PATH, api_key))

    OUT_FILE.write_text(markdown, encoding="utf-8")
    print(f"\nSauvegardé → {OUT_FILE}\n")
    print("=" * 60)
    print("MARKDOWN RÉEL (3000 premiers chars)")
    print("=" * 60)
    print(markdown[:3000])
    print("=" * 60)
    print(f"\nFichier complet : {OUT_FILE}")
    print("Copie-colle les 3000 chars au CTO pour calibrer le parser.")


if __name__ == "__main__":
    main()
