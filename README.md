# RAG Paper Pipeline

Pipeline local pour preparer une base RAG locale pour Open WebUI.

Il gere deux types de contenus:

- des articles scientifiques recuperes automatiquement par theme via OpenAlex, arXiv et Unpaywall;
- des references theoriques ajoutees manuellement en PDF, puis converties en Markdown.

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
- `base_theory`: liste des dossiers de theorie de base a creer/converter.

Les informations sensibles ne doivent pas être mises dans `themes.yaml`. Mets ton email dans un fichier `.env` local, ignoré par Git:

```bash
printf "RAG_PIPELINE_EMAIL=ton.vrai.email@example.com\n" > .env
```

Ou crée/modifie `.env` manuellement avec:

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

Par defaut, le script fonctionne en mode incremental: il ignore les themes scientifiques qui ont deja des fichiers dans `RAG/scientific_articles/<theme>/` et traite seulement les nouveaux themes ajoutes dans `themes.yaml`.

Exemple:

1. Tu ajoutes un nouveau thème dans `themes.yaml`.
2. Tu relances:

```bash
python scripts/pipeline.py --themes themes.yaml
```

Le script ne traite que ce nouveau thème. Les anciens thèmes déjà présents dans `RAG/scientific_articles/` sont ignorés.

Pour forcer le retraitement de tous les thèmes:

```bash
python scripts/pipeline.py --themes themes.yaml --force
```

## Structure RAG

Le script cree et utilise cette structure:

```text
RAG/
├── base_theory/
│   ├── boolean_algebra/
│   │   ├── pdf/
│   │   ├── md/
│   │   └── metadata/
│   ├── general_chemistry/
│   ├── organic_chemistry/
│   ├── electro_chemistry/
│   ├── graph_theory/
│   └── machine_learning_basics/
├── scientific_articles/
│   └── <theme>/
│       ├── pdf/
│       ├── md/
│       └── metadata/
└── clean_notes/
    ├── fiches_articles/
    └── syntheses_theoriques/
```

## Ajouter des references theoriques

Depose manuellement tes PDF de theorie dans le dossier `pdf/` correspondant.

Exemples:

```text
RAG/base_theory/boolean_algebra/pdf/
RAG/base_theory/general_chemistry/pdf/
RAG/base_theory/organic_chemistry/pdf/
RAG/base_theory/electro_chemistry/pdf/
RAG/base_theory/graph_theory/pdf/
RAG/base_theory/machine_learning_basics/pdf/
```

Puis convertis seulement la base theorique:

```bash
python scripts/pipeline.py --themes themes.yaml --base-theory-only
```

Les fichiers Markdown generes seront ecrits dans:

```text
RAG/base_theory/<theme>/md/
```

Pour reconvertir un PDF deja traite:

```bash
python scripts/pipeline.py --themes themes.yaml --base-theory-only --force
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

Les articles scientifiques sont ecrits dans:

```text
RAG/scientific_articles/
├── papers.csv
├── papers.json
└── <theme>/
    ├── pdf/
    ├── md/
    └── metadata/
```

Les fichiers Markdown peuvent ensuite etre importes dans Open WebUI Knowledge/RAG:

```text
RAG/scientific_articles/*/md/*.md
RAG/base_theory/*/md/*.md
```

## Notes

Le pipeline ne contourne pas les paywalls et ne scrape pas agressivement les editeurs. Si un PDF open access n'est pas disponible ou ne peut pas etre converti, un Markdown contenant les metadonnees et l'abstract est tout de meme genere.

Pour `RAG/base_theory`, ajoute seulement des PDF que tu as le droit d'utiliser localement.
