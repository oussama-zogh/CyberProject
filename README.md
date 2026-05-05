# CyberProject

Projet universitaire.

## Stack technique
- **Frontend** : React 18 + Vite + React Router
- **Backend** : FastAPI (Python)
- **Communication** : REST API (JSON + fichiers multipart)

## Lancement rapide

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

- Frontend : http://localhost:5173
- API Docs : http://localhost:8000/docs

## Modules

| Interface | Route |
|-----------|-------|
| Accueil | `/` |
| RSA Cryptography | `/rsa` |
| ECC Cryptography | `/ecc` |
| RSA Attack | `/rsa-attack` |
| ECC Attack | `/ecc-attack` |

## STRUCTURE DU PROJET

cyberproject/
├── backend/
│   ├── main.py                    ← Point d'entrée FastAPI 
│   ├── requirements.txt           ← Dépendances Python
│   └── routers/
│       ├── __init__.py
│       ├── rsa.py                 ←  Mohamed Oussama Zoghlami
│       ├── ecc.py                 ← Eya Mhiri 
│       ├── rsa_attack.py          ← Sarra Selmene 
│       └── ecc_attack.py          ← Youssef Hadjkacem
│
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── main.jsx               ← Entrée React 
        ├── App.jsx                ← Routes 
        ├── index.css              ← Variables CSS globales 
        ├── components/
        │   ├── Navbar.jsx         ← Navigation 
        │   └── Navbar.module.css
        └── pages/
            ├── home/            
            ├── rsa/               ← Mohamed Oussama Zoghlami 
            ├── ecc/               ← Eya Mhiri  
            ├── rsa_attack/        ← Sarra Selmene 
            └── ecc_attack/        ← Youssef Hadjkacem 



