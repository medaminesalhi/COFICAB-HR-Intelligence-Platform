"""CLI d'extraction de CV PDF, basée sur le même service que l'API.

Par confidentialité, le résultat est affiché à l'écran par défaut. L'écriture
d'un JSON contenant des données personnelles doit être demandée explicitement.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.cv_extraction import extract_cv_from_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Extraire les informations d'un CV PDF.")
    parser.add_argument("pdf", type=Path, help="Chemin vers le CV PDF à analyser.")
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Chemin JSON de sortie (optionnel ; le fichier peut contenir des données personnelles).",
    )
    args = parser.parse_args()

    if not args.pdf.is_file():
        parser.error(f"Fichier introuvable : {args.pdf}")

    try:
        result = extract_cv_from_pdf(args.pdf.read_bytes())
    except ValueError as exc:
        parser.error(str(exc))

    serialized = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Résultat enregistré : {args.output}")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
