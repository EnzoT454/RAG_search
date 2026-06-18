# RAG Paper Pipeline

Pipeline local pour préparer des articles scientifiques open access pour Open WebUI / RAG.

Il cherche des articles par thème via OpenAlex et arXiv, récupère les métadonnées, télécharge les PDFs open access disponibles légalement, convertit les PDFs en Markdown, puis sauvegarde les résultats par thème.

## Installation

Le repo est sur le disque externe:

```bash
cd /Volumes/TOSHIBA_EXT/IFT3151-stage/RAG_search/RAG_search
```

Sur ce volume externe, la création d'un `.venv` local peut échouer avec `ensurepip` ou créer un `pip` incomplet. Garde donc le projet sur le disque externe, mais crée l'environnement Python sur le disque interne:

```bash
mkdir -p ~/.venvs
python3 -m venv ~/.venvs/rag_search
source ~/.venvs/rag_search/bin/activate
pip install -r requirements.txt
```

Optionnel, pour disposer d'outils PDF supplémentaires sur macOS:

```bash
brew install poppler
```

## Configuration

Modifie `themes.yaml`, surtout:

- `settings.max_results_per_theme`: nombre d'articles par thème.
- `settings.year_from`: année minimale de publication.
- `themes`: liste des thèmes et requêtes scientifiques.

Les informations sensibles ne doivent pas être mises dans `themes.yaml`. Mets ton email dans un fichier `.env` local, ignoré par Git:

```bash
cp .env.example .env
```

Puis modifie `.env`:

```bash
RAG_PIPELINE_EMAIL=ton.vrai.email@example.com
```

Le script lit automatiquement `RAG_PIPELINE_EMAIL`. Le fichier `.env` reste local et ne doit pas être commit.

## Lancement

```bash
cd /Volumes/TOSHIBA_EXT/IFT3151-stage/RAG_search/RAG_search
source ~/.venvs/rag_search/bin/activate
python scripts/pipeline.py --themes themes.yaml
```

Par défaut, le script fonctionne en mode incrémental: il ignore les thèmes qui ont déjà des fichiers dans `output/themes/<theme>/` et traite seulement les nouveaux thèmes ajoutés dans `themes.yaml`.

Exemple:

1. Tu ajoutes un nouveau thème dans `themes.yaml`.
2. Tu relances:

```bash
python scripts/pipeline.py --themes themes.yaml
```

Le script ne traite que ce nouveau thème. Les anciens thèmes déjà présents dans `output/themes/` sont ignorés.

Pour forcer le retraitement de tous les thèmes:

```bash
python scripts/pipeline.py --themes themes.yaml --force
```

Si un ancien `.venv` cassé existe dans le repo, supprime-le avant d'utiliser l'environnement interne:

```bash
rm -rf .venv
```

Pour vérifier que le bon Python est actif:

```bash
which python
which pip
python --version
pip --version
```

Les chemins doivent pointer vers `~/.venvs/rag_search/bin/...`.

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
