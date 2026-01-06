# 📚 Documentation Technique - QANOUNI AI (v1.2)

> **Système de Conseil Juridique Intelligent basé sur l'IA Générative (RAG)**
> 
> Ce document est destiné aux développeurs souhaitant comprendre, maintenir ou étendre l'application.

---

## 1. Présentation Générale

**Qanouni-AI** est une application **RAG (Retrieval-Augmented Generation)** spécialisée dans le droit algérien. Elle permet aux utilisateurs de :
- Effectuer des **recherches juridiques** dans un corpus de textes de loi.
- Obtenir des **consultations juridiques** personnalisées.
- (Futur) Générer des **mémoires de plaidoirie** et analyser la **jurisprudence**.

### Architecture Hybride (v1.2)
L'application utilise une architecture **hybride multi-modèles** pour optimiser la vitesse et la qualité :

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| **Embeddings** | Google Gemini `text-embedding-004` | Vectorisation sémantique du texte (768 dimensions) |
| **Génération** | **Groq API** `llama-3.3-70b-versatile` | Rédaction des réponses (ultra-rapide) |
| **Recherche Lexicale** | BM25 (Python, en mémoire) | Recherche par mots-clés exacts |
| **Base de Données** | Supabase (PostgreSQL + pgvector) | Stockage des chunks et vecteurs |
| **Backend** | FastAPI (Python 3.10+) | API REST |
| **Frontend** | HTML/CSS/JS (Vanilla) | Interface utilisateur |

---

## 2. Structure du Projet

```
QUANOUNI/new/
├── backend/                    # Code serveur (FastAPI)
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py       # Endpoints: /query, /upload, /login
│   │   │   └── legal.py        # Endpoints: /legal-consultant, /legal/pleading
│   │   ├── core/
│   │   │   └── config.py       # Chargement des variables d'environnement
│   │   ├── services/
│   │   │   ├── rag.py          # ⭐ Pipeline RAG principal (Hybrid Search + Generation)
│   │   │   ├── bm25_service.py # Moteur de recherche lexicale (BM25)
│   │   │   ├── vector_store.py # Interface avec Supabase/pgvector
│   │   │   └── embedding.py    # Appels à l'API Gemini Embedding
│   │   └── main.py             # Point d'entrée FastAPI
│   └── requirements.txt
│
├── frontend_new/               # Interface utilisateur
│   ├── index.html              # Page principale
│   ├── login.html              # Page de connexion
│   ├── style.css               # Styles (Glassmorphism, RTL)
│   └── app.js                  # Logique frontend (fetch API, affichage)
│
├── data/                       # Corpus de textes juridiques (315 fichiers .txt)
├── scripts/                    # Outils de maintenance
│   ├── ingest_pilot.py         # Ingestion des documents
│   └── clear_db.py             # Nettoyage de la base
│
├── .env                        # ⚠️ Clés API (NE PAS COMMITER)
├── Dockerfile                  # Image Docker pour le déploiement
├── render.yaml                 # Configuration Render.com
└── GUIDE_DEMARRAGE.md          # Guide de démarrage rapide
```

---

## 3. Fichier `.env` (Variables d'Environnement)

```ini
# Google Gemini (Embeddings uniquement)
GEMINI_API_KEY=your_gemini_api_key

# Supabase (Base de données)
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key

# Groq (Génération de texte - PRINCIPAL)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# Gemini Models (pour compatibilité)
VITE_GEMINI_CHAT_MODEL=models/gemini-1.5-flash
VITE_GEMINI_EMBEDDING_MODEL=text-embedding-004
```

---

## 4. Pipeline RAG (Fichier `rag.py`)

### 4.1 Flux de Traitement d'une Requête

```
Requête Utilisateur
       │
       ▼
┌─────────────────────────────────────────────┐
│  1. RETRIEVE (Récupération)                 │
│     ├─ Recherche Vectorielle (Supabase)     │
│     └─ Recherche BM25 (Mots-clés)           │
│                                             │
│  2. RRF FUSION                              │
│     └─ Combine les scores (k=60)            │
│                                             │
│  3. RERANK (Optionnel, via Gemini)          │
│     └─ Réévalue la pertinence (0-10)        │
│                                             │
│  4. GENERATE (Génération)                   │
│     └─ Appel à Groq (llama-3.3-70b)         │
└─────────────────────────────────────────────┘
       │
       ▼
   Réponse Formatée (Markdown + Sources)
```

### 4.2 Fonction `generate_with_retry`

Cette fonction gère la génération de texte avec **basculement automatique** :
1. **Priorité** : Groq API (si `GROQ_API_KEY` est défini).
2. **Fallback** : Gemini (si Groq échoue ou n'est pas configuré).

```python
# Extrait simplifié de rag.py
def generate_with_retry(model, prompt, retries=5, delay=4):
    # 1. Essayer Groq en premier
    if settings.GROQ_API_KEY:
        response = requests.post("https://api.groq.com/...", ...)
        if response.ok:
            return GenerationResponse(text=response.json()['choices'][0]['message']['content'])
    
    # 2. Fallback sur Gemini
    return model.generate_content(prompt)
```

---

## 5. Endpoints API

### 5.1 Chercheur Juridique Intelligent (Smart Researcher)
```
POST /api/query
Content-Type: application/json

{
    "query": "ما هي عقوبة السرقة الموصوفة؟"
}

Response:
{
    "query": "...",
    "answer": "...",  // Réponse générée (Markdown)
    "sources": [...]  // Liste des sources utilisées
}
```

### 5.2 Consultation Juridique
```
POST /api/legal-consultant
Content-Type: application/json

{
    "situation": "نزاع حول الميراث بين إخوة..."
}

Response:
{
    "consultation": "...",  // Analyse + Conseils
    "sources": [...]
}
```

### 5.3 Authentification (JWT + Bcrypt)
```
POST /api/register
POST /api/login
```
- **Sécurité**:
    - Mots de passe hashés avec `bcrypt 3.2.2` (via `passlib`).
    - Tokens JWT (HS256) avec expiration 24h.
    - Isolation des données (Multi-tenancy): Chaque utilisateur accède uniquement à ses propres dossiers (`cases`).
    - Policies RLS (Row Level Security) configurées sur Supabase.

POST /api/login response:
{
    "success": true,
    "token": "eyJhbGciOiJIUzI1Ni...",
    "user": { "username": "...", "role": "premium" }
}
```

---

## 6. Frontend

### 6.1 Structure des Pages
- `login.html` → Authentification (redirige vers `index.html`).
- `index.html` → Dashboard avec sidebar (modes: Recherche, Consultant, etc.).

### 6.2 Fichier `app.js`
- Gère les appels API (`fetch`).
- Utilise `marked.js` pour le rendu Markdown.
- Stockage local (`localStorage`) pour la session utilisateur.

---

## 7. Base de Données (Supabase)

### Tables Principales
```sql
-- Table des documents sources
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename TEXT,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table des chunks (avec vecteurs)
CREATE TABLE chunk (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    content TEXT,
    embedding VECTOR(768),
    metadata JSONB
);
```

### Fonction de Recherche Vectorielle
```sql
CREATE FUNCTION match_documents(query_embedding VECTOR(768), match_count INT)
RETURNS TABLE(id INT, content TEXT, similarity FLOAT)
AS $$
    SELECT id, content, 1 - (embedding <=> query_embedding) AS similarity
    FROM chunk
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
### 4.2 Gestion des Accès (RBAC)
Une gestion des rôles (Role-Based Access Control) a été implémentée pour sécuriser les fonctionnalités sensibles.

- **Rôles :**
    - `normal` / `premium` : Accès à la recherche et consultation.
    - `admin` : Accès complet + **Upload de documents**.

- **Création d'Admin :**
    Un script backend sécurisé est disponible pour créer ou promouvoir un administrateur :
    ```bash
    python backend/create_admin.py <username> <password> [email]
    ```
    *Note : L'API publique `/register` ne permet pas de créer un rôle admin.*

---

## 5. Interface Utilisateur (Frontend)

### 5.1 Design & Thème
- **Thème :** "Deep Indigo" (Glassmorphism sombre).
- **Visuel :** Gradient d'arrière-plan (`#0f172a` → `#1e1b4b`) pour une immersion professionnelle.
- **Navigation :** Sidebar avec logo intégré, optimisée pour le flux de travail (Recherche → Consultation → Plaidoirie).

### 5.2 Fonctionnalités
- **Mode Sombre** par défaut.
- **Menu Contextuel :** Les options "Upload" sont masquées pour les non-admins.
- **Support RTL :** Interface entièrement adaptée à l'arabe.

### 5.3 Page d'Accueil (Dashboard)
- **Concept :** Une "Landing Page" interne qui accueille l'utilisateur avec un design premium.
- **Contenu :** Grille de raccourcis compacte (une seule ligne) et centrée, avec slogan inspirant.
- **Expérience :** Aucune sélection par défaut au démarrage, invitant l'utilisateur à choisir son module ("Smart Researcher", "Consultant", "Pleading").

### Local (Développement)
```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 - Frontend
cd frontend_new
python -m http.server 3000
```

### Production (Render/Railway)
Le `Dockerfile` et `render.yaml` sont prêts. Le déploiement nécessite :
1. Définir les variables d'environnement (`.env`) dans le dashboard cloud.
2. `docker build -t qanouni .`
3. `docker run -p 8000:8000 qanouni`

---

## 9. Évolutions Futures (TODO)

| Priorité | Fonctionnalité | Description |
|----------|----------------|-------------|
| 🔴 Haute | Authentification Réelle | Remplacer le mock par Supabase Auth (JWT) |
| 🟠 Moyenne | Mode Plaidoirie | Compléter `/api/legal/pleading` (génération de mémoires) |
| 🟠 Moyenne | Mode Jurisprudence | Filtrer par `category='jurisprudence'` |
| 🟢 Basse | Streaming | Affichage progressif des réponses (SSE) |
| 🟢 Basse | Historique | Sauvegarder les conversations en base |

---

## 10. Contacts & Ressources

- **Groq API**: [console.groq.com](https://console.groq.com)
- **Supabase**: [supabase.com](https://supabase.com)
- **Google AI Studio**: [aistudio.google.com](https://aistudio.google.com)

---

*Documentation générée le 04/01/2026 - Version 1.2 (Hybrid Groq Engine)*
