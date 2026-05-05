from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import rsa, ecc, rsa_attack, ecc_attack

app = FastAPI(title="CyberProject API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rsa.router, prefix="/api/rsa", tags=["RSA"])
app.include_router(ecc.router, prefix="/api/ecc", tags=["ECC"])
app.include_router(rsa_attack.router, prefix="/api/rsa-attack", tags=["RSA Attack"])
app.include_router(ecc_attack.router, prefix="/api/ecc-attack", tags=["ECC Attack"])

@app.get("/")
def root():
    return {"status": "CyberProject API running"}
