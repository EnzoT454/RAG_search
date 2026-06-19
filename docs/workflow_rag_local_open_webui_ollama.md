# Workflow RAG local avec Open WebUI et Ollama

Ce guide explique comment utiliser les fichiers Markdown generes par le pipeline comme base de connaissances locale pour un LLM via Open WebUI et Ollama.

## 1. Verifier les fichiers Markdown generes

Depuis la racine du repo:

```bash
find RAG -name "*.md" | head -20
```

Compter le nombre de fichiers Markdown:

```bash
find RAG -name "*.md" | wc -l
```

Verifier la taille totale du dossier de sortie:

```bash
du -sh RAG
```

Ouvrir un dossier de fichiers Markdown pour verifier leur lisibilite:

```bash
code RAG/scientific_articles/electrochemistry_machine_learning/md
```

Ou sur macOS:

```bash
open RAG/scientific_articles/electrochemistry_machine_learning/md
```

Verifier que le texte est propre. Si les fichiers Markdown contiennent du texte trop melange, des colonnes cassees ou trop de references parasites, il vaut mieux creer des fiches de lecture propres a partir des fichiers bruts.

## 2. Organiser les fichiers par theme

La structure attendue ressemble a ceci:

```text
RAG/
├── base_theory/
│   ├── boolean_algebra/
│   │   ├── pdf/
│   │   └── md/
│   ├── general_chemistry/
│   ├── organic_chemistry/
│   ├── electro_chemistry/
│   ├── graph_theory/
│   └── machine_learning_basics/
├── scientific_articles/
│   ├── electrochemistry_machine_learning/
│   │   └── md/
│   ├── ai_electrochemical_impedance_spectroscopy/
│   │   └── md/
│   ├── deep_learning_battery/
│   │   └── md/
│   └── neural_network_corrosion/
│       └── md/
└── clean_notes/
    ├── fiches_articles/
    └── syntheses_theoriques/
```

Chaque dossier `md/` peut devenir une Knowledge base dans Open WebUI.

Exemples de correspondance:

| Dossier local | Knowledge base Open WebUI |
| --- | --- |
| `RAG/scientific_articles/electrochemistry_machine_learning/md` | `Electrochemistry_ML` |
| `RAG/scientific_articles/ai_electrochemical_impedance_spectroscopy/md` | `EIS_ML` |
| `RAG/scientific_articles/deep_learning_battery/md` | `Battery_Degradation_AI` |
| `RAG/scientific_articles/neural_network_corrosion/md` | `Corrosion_AI` |
| `RAG/base_theory/electro_chemistry/md` | `Electrochemistry_BASE` |

## 3. Demarrer Ollama et Open WebUI

Verifier qu'Ollama tourne:

```bash
curl http://localhost:11434
```

La reponse attendue est:

```text
Ollama is running
```

Verifier les modeles disponibles:

```bash
ollama list
```

Demarrer Open WebUI:

```bash
docker start open-webui
```

Verifier que le conteneur est actif:

```bash
docker ps
```

Ouvrir ensuite Open WebUI:

```text
http://localhost:3000
```

## 4. Creer une Knowledge base dans Open WebUI

Dans Open WebUI:

1. Aller dans `Workspace`.
2. Ouvrir `Knowledge`.
3. Cliquer sur `Create Knowledge`.
4. Creer une base par theme.

Exemples de noms:

- `EIS_ML`
- `Battery_Degradation_AI`
- `Corrosion_AI`
- `Electrochemistry_ML`

Puis, dans chaque base:

1. Cliquer sur `Add files` ou `Upload files`.
2. Ajouter les fichiers `.md` du dossier correspondant.

Exemple:

```text
RAG/scientific_articles/ai_electrochemical_impedance_spectroscopy/md/*.md
```

## 5. Utiliser la base RAG dans le chat

Dans une nouvelle conversation Open WebUI, selectionner le modele local, par exemple:

```text
qwen3:4b
```

Appeler ensuite la Knowledge base avec `#NomDeBase`.

Exemple:

```text
#EIS_ML Résume les approches de machine learning utilisées pour analyser les données EIS. Réponds en français. Ne devine pas. Si une information n’est pas dans les documents, dis “non trouvé”.
```

Autre exemple:

```text
#Battery_Degradation_AI Fais un tableau comparatif des méthodes de deep learning utilisées pour prédire la dégradation des batteries.
```

## 6. Creer des fiches propres a partir des Markdown bruts

Les fichiers Markdown generes automatiquement depuis les PDF sont utiles, mais rarement parfaits. Pour obtenir un meilleur RAG, il est recommande de produire des fiches de lecture propres.

Prompt possible dans Open WebUI:

```text
#EIS_ML À partir de ce document, crée une fiche de lecture en français.

Format :
1. Référence
2. Objectif scientifique
3. Méthode électrochimique
4. Méthode ML/AI utilisée
5. Données utilisées
6. Résultats principaux
7. Limites
8. Utilité pour mon projet
9. Mots-clés

Ne devine pas. Si une information manque, écris “non trouvé”.
```

Ensuite, sauvegarder la fiche dans un nouveau fichier Markdown, par exemple:

```text
notes/fiche_article_001.md
```

A long terme, les fiches propres seront souvent plus efficaces que les PDF convertis automatiquement.

## 7. Construire une base RAG propre

Structure recommandee:

```text
Scientific_RAG_Clean/
├── EIS_ML/
│   ├── raw_md/
│   └── clean_notes/
├── Battery_Degradation_AI/
│   ├── raw_md/
│   └── clean_notes/
├── Corrosion_AI/
│   ├── raw_md/
│   └── clean_notes/
└── Electrochemistry_ML/
    ├── raw_md/
    └── clean_notes/
```

Dans Open WebUI, il est possible de creer deux bases pour un meme theme:

| Knowledge base | Contenu |
| --- | --- |
| `EIS_ML_RAW` | Fichiers Markdown convertis automatiquement |
| `EIS_ML_CLEAN` | Fiches de lecture propres |

Pour les reponses fiables, utiliser en priorite la base `CLEAN`.

## 8. Prompts utiles pour interroger la base locale

### Synthese globale

```text
#Electrochemistry_ML Fais une synthèse des thèmes principaux dans ces documents. Réponds en français clair.
```

### Comparaison des methodes

```text
#EIS_ML Compare les méthodes ML utilisées dans ces documents : type de données, modèle, tâche, avantages, limites.
```

### Extraction de pipeline ML

```text
#Battery_Degradation_AI Extrais les pipelines ML mentionnés : données d’entrée, prétraitement, modèle, métriques, sortie prédite.
```

### Idees de projet

```text
#Corrosion_AI Propose 5 idées de mini-projets réalistes basées uniquement sur les documents. Pour chaque idée : objectif, données, méthode ML, difficulté, livrable.
```

### Verification stricte

```text
#EIS_ML Réponds seulement à partir des documents. Ne donne aucune information externe. Si ce n’est pas présent, écris “non trouvé”.
```

## 9. Reglages RAG a verifier dans Open WebUI

Dans les reglages RAG ou Documents, verifier les options suivantes:

- `chunk size`
- `chunk overlap`
- `top k`
- `citations`
- `reranking`
- `embedding model`

Pour un Mac M1 avec 8 Go de memoire, commencer leger:

| Reglage | Valeur recommandee |
| --- | --- |
| Chunk size | 800 a 1000 |
| Chunk overlap | 100 a 150 |
| Top K | 4 a 6 |
| Citations | Activees |
| Reranking | Active seulement si les performances restent correctes |

Si les reponses sont trop vagues, augmenter legerement `Top K`.

Si les reponses sont trop lentes, reduire `Top K`.

## 10. Workflow final recommande

Le cycle local recommande est:

1. Lancer le script pipeline pour telecharger les articles open access et generer les fichiers Markdown.
2. Verifier rapidement la qualite des fichiers Markdown.
3. Importer les fichiers dans Open WebUI, une Knowledge base par theme.
4. Poser des questions RAG avec `#NomDeBase`.
5. Generer des fiches de lecture propres.
6. Creer une nouvelle Knowledge base avec les fiches propres.
7. Utiliser cette base pour la synthese, le brainstorming et la preparation de stage ou de projet.

Le point le plus important: ne pas tout mettre dans une seule grosse base. Separer les documents par theme rend le RAG plus precis et plus rapide.
