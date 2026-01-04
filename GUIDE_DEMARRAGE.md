# GUIDE DE DÉMARRAGE RAPIDE - QANOUNI AI (v1.2)

Ce guide vous explique comment lancer l'application Qanouni-AI (Backend et Frontend) sur votre machine locale.

## Prérequis
-   Python 3.10+ installé.
-   Un terminal (PowerShell ou CMD).
-   Les clés API configurées dans le fichier `.env` :
    -   `GEMINI_API_KEY` (Pour les Embeddings)
    -   `GROQ_API_KEY` (Pour la Génération Rapide)

## 1. Démarrer le Serveur Backend (API)

Le backend est construit avec **FastAPI**. Il gère la logique RAG, la connexion à la base de données et les appels aux modèles IA.

1.  Ouvrez un terminal.
2.  Accédez au dossier `backend` :
    ```powershell
    cd backend
    ```
3.  Lancez le serveur avec `uvicorn` :
    ```powershell
    uvicorn app.main:app --host 127.0.0.1 --port 8000
    ```
    *Si tout va bien, vous verrez : `Uvicorn running on http://127.0.0.1:8000`*

## 2. Démarrer le Frontend (Interface Utilisateur)

L'interface est une application web statique (HTML/JS) simple.

1.  Ouvrez un **deuxième** terminal.
2.  Accédez au dossier `frontend_new` :
    ```powershell
    cd frontend_new
    ```
3.  Lancez un serveur HTTP local (Python) :
    ```powershell
    python -m http.server 3000
    ```
    *Le message `Serving HTTP on :: port 3000` apparaîtra.*

## 3. Utilisation de l'Application

1.  Ouvrez votre navigateur web (Chrome, Edge, etc.).
2.  Allez à l'adresse : **[http://localhost:3000](http://localhost:3000)**
3.  **Connexion :**
    -   Utilisateur : `admin`
    -   Mot de passe : `admin`
4.  **Fonctionnalités :**
    -   Cliquez sur **"المستشار القانوني" (Conseiller Juridique)** dans le menu.
    -   Décrivez votre situation (ex: "نزاع ميراث").
    -   Appréciez la réponse instantanée générée par Groq ! 🚀

## En cas de problème

-   **Erreur "System Busy" :** Vérifiez votre connexion internet ou votre quota Groq/Gemini.
-   **Erreur de Connexion (Login) :** Assurez-vous que le Backend (Port 8000) est bien lancé.
-   **Rien ne s'affiche :** Vérifiez que vous êtes bien sur le port 3000 et non 8000 pour le navigateur.
