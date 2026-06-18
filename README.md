# RAG Paper Pipeline

Pipeline local pour préparer des articles scientifiques open access pour Open WebUI / RAG.

Il cherche des articles par thème via OpenAlex et arXiv, récupère les métadonnées, télécharge les PDFs open access disponibles légalement, convertit les PDFs en Markdown, puis sauvegarde les résultats par thème.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optionnel, pour disposer d'outils PDF supplémentaires sur macOS:

```bash
brew install poppler
```

## Configuration

Modifie `themes.yaml`, surtout:

- `settings.email`: remplace `ton.email@example.com` par ton vrai email.
- `settings.max_results_per_theme`: nombre d'articles par thème.
- `settings.year_from`: année minimale de publication.
- `themes`: liste des thèmes et requêtes scientifiques.

## Lancement

```bash
source .venv/bin/activate
python scripts/pipeline.py --themes themes.yaml
```

Les résultats sont écrits dans:

```text
output/
├── papers.csv
├── papers.json
└── themes/
    └── <theme>/
        ├── pdf/
        ├── md/
        └── metadata/
```

Les fichiers `output/themes/*/md/*.md` peuvent ensuite être importés dans Open WebUI Knowledge/RAG.

## Notes

Le pipeline ne contourne pas les paywalls et ne scrape pas agressivement les éditeurs. Si un PDF open access n'est pas disponible ou ne peut pas être converti, un Markdown contenant les métadonnées et l'abstract est tout de même généré.
