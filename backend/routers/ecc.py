from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import io
import hashlib
import secrets
import struct
import time

router = APIRouter()

# ─────────────────────────────────────────────
#  Courbe secp256k1 (paramètres par défaut)
# ─────────────────────────────────────────────
DEFAULT_P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
DEFAULT_A  = 0
DEFAULT_B  = 7
DEFAULT_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
DEFAULT_Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
DEFAULT_N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# ─────────────────────────────────────────────
#  État en mémoire
# ─────────────────────────────────────────────
_current_key: dict = {}
_current_curve: dict = {
    "p": DEFAULT_P, "a": DEFAULT_A, "b": DEFAULT_B,
    "Gx": DEFAULT_Gx, "Gy": DEFAULT_Gy, "n": DEFAULT_N,
    "name": "secp256k1"
}

# ─────────────────────────────────────────────
#  Arithmétique sur la courbe
# ─────────────────────────────────────────────

def modinv(a: int, m: int) -> int:
    if a == 0:
        raise ValueError("Pas d'inverse pour 0")
    lm, hm = 1, 0
    low, high = a % m, m
    while low > 1:
        ratio = high // low
        nm = hm - lm * ratio
        new = high - low * ratio
        lm, low, hm, high = nm, new, lm, low
    return lm % m

def point_add(P1, P2, a, p):
    if P1 is None:
        return P2
    if P2 is None:
        return P1
    x1, y1 = P1
    x2, y2 = P2
    if x1 == x2:
        if y1 != y2:
            return None
        # Doublement : S = (3x1² + a) / (2y1)
        lam = (3 * x1 * x1 + a) * modinv(2 * y1, p) % p
    else:
        # Addition : S = (y2 - y1) / (x2 - x1)
        lam = (y2 - y1) * modinv(x2 - x1, p) % p
    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p
    return (x3, y3)

def scalar_mult(k: int, point, a: int, p: int):
    result = None
    addend = point
    while k:
        if k & 1:
            result = point_add(result, addend, a, p)
        addend = point_add(addend, addend, a, p)
        k >>= 1
    return result

def get_curve():
    """Retourne les paramètres de la courbe active."""
    c = _current_curve
    return c["p"], c["a"], c["b"], (c["Gx"], c["Gy"]), c["n"]

# ─────────────────────────────────────────────
#  Schémas Pydantic
# ─────────────────────────────────────────────

class CurveParams(BaseModel):
    p: str
    a: str
    b: str
    Gx: str
    Gy: str
    n: str
    name: Optional[str] = "custom"

class CurveResponse(BaseModel):
    name: str
    p: str
    a: str
    b: str
    Gx: str
    Gy: str
    n: str
    message: str

class KeyResponse(BaseModel):
    private_key: str
    public_key_x: str
    public_key_y: str
    curve: str
    execution_time: str
    message: str

class ECDHRequest(BaseModel):
    # Clé publique de l'autre partie (point β·G ou α·G)
    other_pub_x: str
    other_pub_y: str
    # Clé privée locale (optionnel, sinon mémoire)
    private_key: Optional[str] = ""

class ECDHResponse(BaseModel):
    shared_key_x: str
    shared_key_y: str
    execution_time: str
    message: str

class SignRequest(BaseModel):
    message: str
    private_key: Optional[str] = ""

class SignResponse(BaseModel):
    r: str
    s: str
    h: str
    execution_time: str
    message: str

class VerifyRequest(BaseModel):
    message: str
    r: str
    s: str
    public_key_x: Optional[str] = ""
    public_key_y: Optional[str] = ""

class VerifyResponse(BaseModel):
    valid: bool
    execution_time: str
    message: str

# ─────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────

# ── 0. Définir courbe custom ─────────────────
@router.post("/set-curve", response_model=CurveResponse)
def set_curve(params: CurveParams):
    """Définit les paramètres de la courbe elliptique."""
    global _current_curve
    try:
        p  = int(params.p,  16) if params.p.startswith("0x")  else int(params.p)
        a  = int(params.a,  16) if params.a.startswith("0x")  else int(params.a)
        b  = int(params.b,  16) if params.b.startswith("0x")  else int(params.b)
        Gx = int(params.Gx, 16) if params.Gx.startswith("0x") else int(params.Gx)
        Gy = int(params.Gy, 16) if params.Gy.startswith("0x") else int(params.Gy)
        n  = int(params.n,  16) if params.n.startswith("0x")  else int(params.n)
    except ValueError:
        raise HTTPException(status_code=400, detail="Paramètres invalides")

    _current_curve = {"p": p, "a": a, "b": b, "Gx": Gx, "Gy": Gy, "n": n, "name": params.name}

    return CurveResponse(
        name=params.name, p=hex(p), a=hex(a), b=hex(b),
        Gx=hex(Gx), Gy=hex(Gy), n=hex(n),
        message=f"Courbe '{params.name}' définie avec succès"
    )

# ── 1. Génération de clés ────────────────────
@router.post("/generate-key", response_model=KeyResponse)
def generate_key():
    """Génère une paire de clés ECC : k aléatoire, Q = k·G"""
    global _current_key
    p, a, b, G, n = get_curve()

    t0 = time.perf_counter()

    private_k = secrets.randbelow(n - 1) + 1
    public_Q  = scalar_mult(private_k, G, a, p)

    elapsed = time.perf_counter() - t0

    if public_Q is None:
        raise HTTPException(status_code=500, detail="Erreur calcul clé publique")

    Qx, Qy = public_Q
    _current_key = {
        "private_key":  hex(private_k),
        "public_key_x": hex(Qx),
        "public_key_y": hex(Qy),
        "curve": _current_curve["name"],
    }

    return KeyResponse(
        private_key=hex(private_k),
        public_key_x=hex(Qx),
        public_key_y=hex(Qy),
        curve=_current_curve["name"],
        execution_time=f"{elapsed*1000:.3f} ms",
        message="Paire de clés ECC générée avec succès"
    )

# ── 2. ECDH — Échange de clés ────────────────
@router.post("/ecdh", response_model=ECDHResponse)
def ecdh(req: ECDHRequest):
    """
    ECDH — Échange de clés (cours 5.1.4)
    Key = α·(β·G) = β·(α·G) = αβ·G
    """
    p, a, b, G, n = get_curve()

    # Résoudre clé privée locale
    if req.private_key:
        try:
            k = int(req.private_key, 16) if req.private_key.startswith("0x") else int(req.private_key)
        except ValueError:
            raise HTTPException(status_code=400, detail="Clé privée invalide")
    elif _current_key:
        k = int(_current_key["private_key"], 16)
    else:
        raise HTTPException(status_code=400, detail="Aucune clé privée. Générez d'abord une paire.")

    # Clé publique de l'autre partie
    try:
        other_x = int(req.other_pub_x, 16) if req.other_pub_x.startswith("0x") else int(req.other_pub_x)
        other_y = int(req.other_pub_y, 16) if req.other_pub_y.startswith("0x") else int(req.other_pub_y)
    except ValueError:
        raise HTTPException(status_code=400, detail="Clé publique invalide")

    t0 = time.perf_counter()

    # Key = k · (other_pub) = αβ·G
    shared = scalar_mult(k, (other_x, other_y), a, p)

    elapsed = time.perf_counter() - t0

    if shared is None:
        raise HTTPException(status_code=500, detail="Erreur ECDH : secret nul")

    return ECDHResponse(
        shared_key_x=hex(shared[0]),
        shared_key_y=hex(shared[1]),
        execution_time=f"{elapsed*1000:.3f} ms",
        message="Clé de session commune calculée via ECDH"
    )

# ── 3. ECDSA — Signature ─────────────────────
@router.post("/sign", response_model=SignResponse)
def sign(req: SignRequest):
    """
    ECDSA Signature (cours 5.1.5)
    h = hash(message)
    k aléatoire → Q = k·G
    r = Qx mod n
    s = (h + r·α) / k mod n
    """
    p, a, b, G, n = get_curve()

    # Clé privée α
    if req.private_key:
        try:
            alpha = int(req.private_key, 16) if req.private_key.startswith("0x") else int(req.private_key)
        except ValueError:
            raise HTTPException(status_code=400, detail="Clé privée invalide")
    elif _current_key:
        alpha = int(_current_key["private_key"], 16)
    else:
        raise HTTPException(status_code=400, detail="Aucune clé privée. Générez d'abord une paire.")

    t0 = time.perf_counter()

    # h = SHA256(message) converti en entier
    h = int(hashlib.sha256(req.message.encode()).hexdigest(), 16) % n

    # k aléatoire, Q = k·G, r = Qx mod n
    while True:
        k = secrets.randbelow(n - 1) + 1
        Q = scalar_mult(k, G, a, p)
        if Q is None:
            continue
        r = Q[0] % n
        if r == 0:
            continue
        # s = (h + r·α) / k mod n
        s = (h + r * alpha) * modinv(k, n) % n
        if s != 0:
            break

    elapsed = time.perf_counter() - t0

    return SignResponse(
        r=hex(r),
        s=hex(s),
        h=hex(h),
        execution_time=f"{elapsed*1000:.3f} ms",
        message="Signature ECDSA générée avec succès"
    )

# ── 4. ECDSA — Vérification ──────────────────
@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest):
    """
    ECDSA Vérification (cours 5.1.5)
    Q' = (h/s)·G + (r/s)·αG
    Valide si Q'x = r
    """
    p, a, b, G, n = get_curve()

    # Clé publique
    if req.public_key_x and req.public_key_y:
        try:
            Qx = int(req.public_key_x, 16) if req.public_key_x.startswith("0x") else int(req.public_key_x)
            Qy = int(req.public_key_y, 16) if req.public_key_y.startswith("0x") else int(req.public_key_y)
        except ValueError:
            raise HTTPException(status_code=400, detail="Clé publique invalide")
    elif _current_key:
        Qx = int(_current_key["public_key_x"], 16)
        Qy = int(_current_key["public_key_y"], 16)
    else:
        raise HTTPException(status_code=400, detail="Aucune clé publique.")

    pub = (Qx, Qy)

    try:
        r = int(req.r, 16) if req.r.startswith("0x") else int(req.r)
        s = int(req.s, 16) if req.s.startswith("0x") else int(req.s)
    except ValueError:
        raise HTTPException(status_code=400, detail="Signature (r, s) invalide")

    t0 = time.perf_counter()

    h = int(hashlib.sha256(req.message.encode()).hexdigest(), 16) % n

    # Q' = (h/s)·G + (r/s)·pub
    s_inv = modinv(s, n)
    u1 = (h * s_inv) % n
    u2 = (r * s_inv) % n

    point1 = scalar_mult(u1, G, a, p)
    point2 = scalar_mult(u2, pub, a, p)
    Q_prime = point_add(point1, point2, a, p)

    elapsed = time.perf_counter() - t0

    if Q_prime is None:
        return VerifyResponse(valid=False, execution_time=f"{elapsed*1000:.3f} ms", message="Signature invalide ❌")

    valid = (Q_prime[0] % n == r)

    return VerifyResponse(
        valid=valid,
        execution_time=f"{elapsed*1000:.3f} ms",
        message="Signature valide ✅" if valid else "Signature invalide ❌"
    )

# ── 5. Clé active ────────────────────────────
@router.get("/current-key")
def get_current_key():
    if not _current_key:
        return {"has_key": False}
    return {"has_key": True, **_current_key}

# ── 6. Chiffrement fichier (ECIES) ───────────
@router.post("/encrypt-file")
async def encrypt_file(
    file: UploadFile = File(...),
    pub_x: str = Form(default=""),
    pub_y: str = Form(default=""),
):
    p, a, b, G, n = get_curve()

    if pub_x and pub_y:
        try:
            Qx = int(pub_x, 16)
            Qy = int(pub_y, 16)
        except ValueError:
            raise HTTPException(status_code=400, detail="Clé publique invalide")
    elif _current_key:
        Qx = int(_current_key["public_key_x"], 16)
        Qy = int(_current_key["public_key_y"], 16)
    else:
        raise HTTPException(status_code=400, detail="Aucune clé publique. Générez d'abord une paire.")

    Q = (Qx, Qy)
    plaintext = await file.read()
    original_name = file.filename or "file"

    r = secrets.randbelow(n - 1) + 1
    C1 = scalar_mult(r, G, a, p)
    S  = scalar_mult(r, Q, a, p)

    if C1 is None or S is None:
        raise HTTPException(status_code=500, detail="Erreur ECIES")

    aes_key  = hashlib.sha256(S[0].to_bytes(32, "big")).digest()
    nonce    = secrets.token_bytes(16)
    ciphertext = _aes_ctr_crypt(aes_key, nonce, plaintext)

    name_bytes = original_name.encode("utf-8")
    out = io.BytesIO()
    out.write(struct.pack(">I", len(name_bytes)))
    out.write(name_bytes)
    out.write(C1[0].to_bytes(32, "big"))
    out.write(C1[1].to_bytes(32, "big"))
    out.write(nonce)
    out.write(ciphertext)
    out.seek(0)

    return StreamingResponse(
        out,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{original_name}.ecc"'},
    )

# ── 7. Déchiffrement fichier (ECIES) ─────────
@router.post("/decrypt-file")
async def decrypt_file(
    file: UploadFile = File(...),
    private_key: str = Form(default=""),
):
    p, a, b, G, n = get_curve()

    if private_key:
        try:
            k = int(private_key, 16)
        except ValueError:
            raise HTTPException(status_code=400, detail="Clé privée invalide")
    elif _current_key:
        k = int(_current_key["private_key"], 16)
    else:
        raise HTTPException(status_code=400, detail="Aucune clé privée.")

    data = await file.read()
    try:
        offset = 0
        (name_len,) = struct.unpack_from(">I", data, offset); offset += 4
        original_name = data[offset:offset + name_len].decode("utf-8"); offset += name_len
        C1x = int.from_bytes(data[offset:offset + 32], "big"); offset += 32
        C1y = int.from_bytes(data[offset:offset + 32], "big"); offset += 32
        nonce = data[offset:offset + 16]; offset += 16
        ciphertext = data[offset:]
    except Exception:
        raise HTTPException(status_code=400, detail="Fichier corrompu")

    S = scalar_mult(k, (C1x, C1y), a, p)
    if S is None:
        raise HTTPException(status_code=500, detail="Erreur ECIES déchiffrement")

    aes_key  = hashlib.sha256(S[0].to_bytes(32, "big")).digest()
    plaintext = _aes_ctr_crypt(aes_key, nonce, ciphertext)

    return StreamingResponse(
        io.BytesIO(plaintext),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{original_name}"'},
    )

# ─────────────────────────────────────────────
#  AES-CTR
# ─────────────────────────────────────────────
def _aes_ctr_crypt(key: bytes, nonce: bytes, data: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
        enc = cipher.encryptor()
        return enc.update(data) + enc.finalize()
    except ImportError:
        keystream = b""
        counter = 0
        while len(keystream) < len(data):
            keystream += hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
            counter += 1
        return bytes(a ^ b for a, b in zip(data, keystream[:len(data)]))
