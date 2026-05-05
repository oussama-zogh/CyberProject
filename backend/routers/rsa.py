"""
RSA Module — CyberProject
Corrections v2:
  - Validation n > 255 dans generate_key  (CORRECTION PRINCIPALE)
      → RSA exige que tout bloc message m < n.
        Avec un chiffrement octet-par-octet (block_size=1), les octets
        vont de 0 à 255, donc n doit être > 255.
        Si n ≤ 255, pow(m, e, n) calcule en réalité pow(m % n, e, n),
        ce qui écrase des octets > n et rend le déchiffrement impossible.
  - rsa_encrypt_bytes : suppression du double-passage 'needs_rechiffre'
      (inutile si n > 255 est garanti, et la logique était incohérente)
  - Erreurs descriptives avec exemples de premiers valides
  - Reste identique : decrypt_file retourne JSON (base64),
    sig_int géré proprement, choose_e avec fallback linéaire complet
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
import math, struct, hashlib, time, base64

router = APIRouter()

# =======================================================================
#  CLE STATIQUE (signature / expediteur)
#  p=61, q=53 -> n=3233, phi=3120, e=17, d=2753
# =======================================================================
_STATIC = {"p": 61, "q": 53, "n": 3233, "phi": 3120, "e": 17, "d": 2753}

_dynamic_key = None   # cle generee par l'utilisateur


# ── Fonctions mathematiques RSA ─────────────────────────────────────────

def is_prime(n):
    if n < 2: return False
    if n < 4: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0: return False
        i += 6
    return True

def extended_gcd(a, b):
    if a == 0: return b, 0, 1
    g, x, y = extended_gcd(b % a, a)
    return g, y - (b // a) * x, x

def mod_inverse(e, phi):
    g, x, _ = extended_gcd(e, phi)
    if g != 1: raise ValueError("Inverse modulaire inexistant")
    return x % phi

def choose_e(phi):
    """Choisit e dans [65537,257,17,7,5,3] tel que gcd(e,phi)=1.
    Fallback lineaire si aucun ne convient (petits phi)."""
    for c in [65537, 257, 17, 7, 5, 3]:
        if 1 < c < phi and math.gcd(c, phi) == 1:
            return c
    # fallback
    e = 2
    while e < phi:
        if math.gcd(e, phi) == 1:
            return e
        e += 1
    raise ValueError("Aucun e valide pour phi=" + str(phi))


# ── Chiffrement / Dechiffrement par blocs ───────────────────────────────

def bytes_to_int(b):
    return int.from_bytes(b, "big")

def int_to_bytes_fixed(i, length):
    return i.to_bytes(length, "big")

def rsa_encrypt_bytes(raw: bytes, e: int, n: int) -> bytes:
    """
    Chiffre raw bytes avec (e, n).
    Format: [8 bytes: longueur originale][4 bytes: block_size][4 bytes: cipher_block_size][blocs...]

    PRÉ-CONDITION MATHÉMATIQUE : n > 255 (garantie par generate_key).
    Avec block_size = (n.bit_length()-1)//8 octets par bloc, chaque chunk
    représente un entier m tel que 0 ≤ m < 2^(block_size*8) ≤ n, donc m < n.
    RSA garantit alors : (m^e)^d ≡ m (mod n)  — déchiffrement parfait.

    Si n ≤ 255, des octets (0-255) seraient ≥ n, ce qui rendrait
    l'opération pow(m, e, n) = pow(m % n, e, n) irréversible (perte d'info).
    Cette situation est bloquée en amont par generate_key.
    """
    block_size = max(1, (n.bit_length() - 1) // 8)
    cipher_block_size = (n.bit_length() + 7) // 8

    blocks = []
    for i in range(0, len(raw), block_size):
        chunk = raw[i:i + block_size]
        m = bytes_to_int(chunk)
        # Invariant garanti par generate_key (n > 255) : m < n
        # On le vérifie ici en défense — ne devrait jamais se déclencher
        if m >= n:
            raise HTTPException(
                500,
                f"ERREUR INTERNE : bloc m={m} >= n={n}. "
                f"Cela ne devrait pas arriver si n > 255. "
                f"Régénérez une clé avec des premiers plus grands."
            )
        c = pow(m, e, n)
        blocks.append(int_to_bytes_fixed(c, cipher_block_size))

    metadata = struct.pack(">QII", len(raw), block_size, cipher_block_size)
    return metadata + b"".join(blocks)

def rsa_decrypt_bytes(raw: bytes, d: int, n: int) -> bytes:
    """
    Dechiffre raw bytes avec (d, n).
    Lit les 16 premiers bytes de metadonnees.
    """
    if len(raw) < 16:
        raise HTTPException(400, "Donnees chiffrees invalides. Mauvaise cle ou fichier corrompu.")

    try:
        original_length, block_size, cipher_block_size = struct.unpack(">QII", raw[:16])
    except struct.error:
        raise HTTPException(400, "Metadonnees invalides. Mauvaise cle ou fichier corrompu.")

    # Detection cle incorrecte
    expected_cbs = (n.bit_length() + 7) // 8
    if cipher_block_size != expected_cbs:
        raise HTTPException(400,
            f"Incompatibilite de cle : fichier chiffre avec une autre cle "
            f"(cipher_block_size attendu={expected_cbs}, trouve={cipher_block_size}).")

    cipher_data = raw[16:]
    decrypted = bytearray()
    for i in range(0, len(cipher_data), cipher_block_size):
        chunk = cipher_data[i:i + cipher_block_size]
        if not chunk: break
        c = bytes_to_int(chunk)
        m = pow(c, d, n)     # M = C^d mod n
        try:
            decrypted.extend(int_to_bytes_fixed(m, block_size))
        except Exception:
            raise HTTPException(400, "Dechiffrement impossible : cle incorrecte ou fichier corrompu.")

    return bytes(decrypted[:original_length])


# ── Signature ────────────────────────────────────────────────────────────

def sha256_reduced(data: bytes, n: int) -> int:
    """h = SHA-256(data) mod n"""
    return int(hashlib.sha256(data).hexdigest(), 16) % n

def sign_data(data: bytes, d_priv: int, n_priv: int) -> int:
    """Signature: sigma = h^d mod n  (cle PRIVEE statique, message ORIGINAL)"""
    h = sha256_reduced(data, n_priv)
    return pow(h, d_priv, n_priv)

def verify_sig(data: bytes, sigma: int, e_pub: int, n_pub: int) -> tuple[bool, int, int]:
    """Verification: h_extrait = sigma^e mod n, compare a h_recalc.
    Retourne (valide, h_recalc, h_extrait)."""
    h_recalc = sha256_reduced(data, n_pub)
    h_extrait = pow(sigma, e_pub, n_pub)
    return (h_recalc == h_extrait), h_recalc, h_extrait


# ── Modeles Pydantic ─────────────────────────────────────────────────────

class KeyGenRequest(BaseModel):
    p: int
    q: int

class MessageRequest(BaseModel):
    message: str

class MessageDecryptRequest(BaseModel):
    ciphertext_b64: str
    signature_b64: str


# =======================================================================
#  ROUTES
# =======================================================================

@router.get("/static-key")
def get_static_key():
    return {
        "p": _STATIC["p"], "q": _STATIC["q"],
        "n": _STATIC["n"], "phi": _STATIC["phi"],
        "e": _STATIC["e"], "d": _STATIC["d"],
        "public_key":  {"e": _STATIC["e"], "n": _STATIC["n"]},
        "private_key": {"d": _STATIC["d"], "n": _STATIC["n"]},
    }


@router.post("/generate-key")
def generate_key(req: KeyGenRequest):
    global _dynamic_key
    t0 = time.perf_counter()

    p, q = req.p, req.q
    if not is_prime(p): raise HTTPException(400, f"{p} n'est pas un nombre premier.")
    if not is_prime(q): raise HTTPException(400, f"{q} n'est pas un nombre premier.")
    if p == q:          raise HTTPException(400, "p et q doivent etre differents.")

    n   = p * q
    phi = (p - 1) * (q - 1)

    # ── VALIDATION MATHÉMATIQUE PRINCIPALE ──────────────────────────────
    # RSA chiffre par blocs d'octets. Avec block_size = (n.bit_length()-1)//8,
    # chaque bloc m représente au plus (n.bit_length()-1) bits, donc m < n.
    # Mais quand n ≤ 255, block_size = 0 → forcé à 1, et les octets (0-255)
    # peuvent dépasser n. pow(m, e, n) calcule alors pow(m % n, e, n), ce qui
    # réduit m de façon irréversible : le déchiffrement retourne (m % n) ≠ m.
    # → Règle : n doit être STRICTEMENT SUPÉRIEUR à 255.
    if n <= 255:
        raise HTTPException(
            400,
            f"n = p × q = {p} × {q} = {n} est trop petit. "
            f"RSA nécessite n > 255 pour chiffrer correctement tout octet (0–255). "
            f"Avec n ≤ 255, un octet m peut satisfaire m ≥ n, ce qui rend "
            f"pow(m, e, n) irréversible (perte d'information définitive). "
            f"Exemples de couples valides : (p=17, q=19 → n=323), "
            f"(p=5, q=53 → n=265), (p=13, q=23 → n=299)."
        )
    # ────────────────────────────────────────────────────────────────────

    e   = choose_e(phi)
    d   = mod_inverse(e, phi)
    verif = (e * d) % phi
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)

    _dynamic_key = {"p": p, "q": q, "n": n, "phi": phi, "e": e, "d": d}

    return {
        "p": p, "q": q, "n": n, "phi": phi, "e": e, "d": d,
        "public_key":  {"e": e, "n": n},
        "private_key": {"d": d, "n": n},
        "elapsed_ms": elapsed_ms,
        "message": "Cle RSA dynamique generee avec succes",
        "steps": [
            f"(1) p={p} est premier, q={q} est premier",
            f"(2) n = p x q = {p} x {q} = {n}",
            f"(3) phi(n) = (p-1)(q-1) = {p-1} x {q-1} = {phi}",
            f"(4) e = {e}  [choisi automatiquement, gcd({e}, {phi}) = {math.gcd(e, phi)}]",
            f"(5) d = e^-1 mod phi(n) = {e}^-1 mod {phi} = {d}  [Euclide etendu]",
            f"(6) Verification : e x d mod phi(n) = {e} x {d} mod {phi} = {verif}",
        ],
    }


@router.get("/current-key")
def get_current_key():
    if _dynamic_key is None:
        return {"has_key": False}
    return {"has_key": True, **_dynamic_key}


@router.post("/encrypt-file")
async def encrypt_file(file: UploadFile = File(...)):
    """
    1. SHA-256(fichier original)
    2. Signature: sigma = h^d_statique mod n_statique  (cle STATIQUE)
    3. Chiffrement: C = M^e_dyn mod n_dyn  (cle DYNAMIQUE)
    Retourne JSON avec ciphertext et signature en base64.
    """
    if _dynamic_key is None:
        raise HTTPException(400, "Generez d'abord une cle dynamique RSA.")

    raw = await file.read()
    file_hash = hashlib.sha256(raw).hexdigest()

    # Signature
    t1 = time.perf_counter()
    sigma = sign_data(raw, _STATIC["d"], _STATIC["n"])
    t_sign = round((time.perf_counter() - t1) * 1000, 3)
    sig_b64 = base64.b64encode(str(sigma).encode()).decode()

    # Chiffrement
    t2 = time.perf_counter()
    encrypted = rsa_encrypt_bytes(raw, _dynamic_key["e"], _dynamic_key["n"])
    t_enc = round((time.perf_counter() - t2) * 1000, 3)
    enc_b64 = base64.b64encode(encrypted).decode()

    h_val = sha256_reduced(raw, _STATIC["n"])

    return {
        "filename":   file.filename,
        "file_hash":  file_hash,
        "signature":  sig_b64,
        "ciphertext": enc_b64,
        "timing": {
            "signature_ms":   t_sign,
            "chiffrement_ms": t_enc,
        },
        "formulas": {
            "hash":        f"h = SHA-256(fichier) mod n_stat = {h_val}",
            "signature":   f"sigma = h^d mod n = {h_val}^{_STATIC['d']} mod {_STATIC['n']} = {sigma}",
            "chiffrement": f"C = M^e mod n  (e={_dynamic_key['e']}, n={_dynamic_key['n']}) bloc par bloc",
        },
        "message": "Chiffrement reussi",
    }


@router.post("/decrypt-file")
async def decrypt_file(file: UploadFile = File(...), signature: str = Form(...)):
    """
    1. Dechiffrement: M = C^d_dyn mod n_dyn  (cle DYNAMIQUE)
    2. SHA-256(M dechiffre)
    3. Verification: h_extrait = sigma^e_stat mod n_stat  (cle STATIQUE)
    Retourne JSON avec fichier dechiffre en base64.
    """
    if _dynamic_key is None:
        raise HTTPException(400, "Generez d'abord une cle dynamique RSA.")

    raw_upload = await file.read()

    # Decode base64 du fichier .enc
    try:
        encrypted = base64.b64decode(raw_upload)
    except Exception:
        raise HTTPException(400, "Fichier .enc invalide (base64 corrompu).")

    # Dechiffrement
    t1 = time.perf_counter()
    decrypted = rsa_decrypt_bytes(encrypted, _dynamic_key["d"], _dynamic_key["n"])
    t_dec = round((time.perf_counter() - t1) * 1000, 3)

    file_hash = hashlib.sha256(decrypted).hexdigest()

    # Verification signature
    t2 = time.perf_counter()
    sig_valid = False
    sigma = None
    h_recalc = 0
    h_extrait = 0
    try:
        sigma = int(base64.b64decode(signature.strip().encode()).decode())
        sig_valid, h_recalc, h_extrait = verify_sig(decrypted, sigma, _STATIC["e"], _STATIC["n"])
    except Exception:
        pass
    t_verif = round((time.perf_counter() - t2) * 1000, 3)

    # Fichier dechiffre en base64 pour le frontend
    dec_b64 = base64.b64encode(decrypted).decode()
    original_name = file.filename.replace(".enc", "").replace("encrypted_", "")

    return {
        "filename":       original_name,
        "file_hash":      file_hash,
        "decrypted_b64":  dec_b64,
        "signature_valid": sig_valid,
        "timing": {
            "dechiffrement_ms":      t_dec,
            "verification_sig_ms":   t_verif,
        },
        "formulas": {
            "dechiffrement": f"M = C^d mod n  (d={_dynamic_key['d']}, n={_dynamic_key['n']})",
            "hash":          f"h_recalc = SHA-256(M) mod n_stat = {h_recalc}",
            "verification":  f"h_extrait = sigma^e mod n = {sigma}^{_STATIC['e']} mod {_STATIC['n']} = {h_extrait} | {'VALIDE' if sig_valid else 'INVALIDE'}",
        },
        "message": "Dechiffrement reussi",
    }


@router.post("/encrypt-message")
def encrypt_message(req: MessageRequest):
    """
    1. SHA-256(message)
    2. Signature avec cle STATIQUE
    3. Chiffrement avec cle DYNAMIQUE
    """
    if _dynamic_key is None:
        raise HTTPException(400, "Generez d'abord une cle dynamique RSA.")

    raw = req.message.encode("utf-8")
    msg_hash = hashlib.sha256(raw).hexdigest()

    t1 = time.perf_counter()
    sigma = sign_data(raw, _STATIC["d"], _STATIC["n"])
    t_sign = round((time.perf_counter() - t1) * 1000, 3)
    sig_b64 = base64.b64encode(str(sigma).encode()).decode()

    t2 = time.perf_counter()
    encrypted = rsa_encrypt_bytes(raw, _dynamic_key["e"], _dynamic_key["n"])
    t_enc = round((time.perf_counter() - t2) * 1000, 3)
    enc_b64 = base64.b64encode(encrypted).decode()

    h_val = sha256_reduced(raw, _STATIC["n"])

    return {
        "original_message": req.message,
        "message_hash":     msg_hash,
        "signature":        sig_b64,
        "ciphertext_b64":   enc_b64,
        "timing": {
            "signature_ms":   t_sign,
            "chiffrement_ms": t_enc,
        },
        "formulas": {
            "hash":        f"h = SHA-256(message) mod n_stat = {h_val}",
            "signature":   f"sigma = h^d mod n = {h_val}^{_STATIC['d']} mod {_STATIC['n']} = {sigma}",
            "chiffrement": f"C = M^e mod n  (e={_dynamic_key['e']}, n={_dynamic_key['n']}) bloc par bloc",
        },
        "message": "Message chiffre avec succes",
    }


@router.post("/decrypt-message")
def decrypt_message(req: MessageDecryptRequest):
    """
    1. Dechiffrement avec cle DYNAMIQUE
    2. Recalcul hash
    3. Verification signature avec cle STATIQUE
    """
    if _dynamic_key is None:
        raise HTTPException(400, "Generez d'abord une cle dynamique RSA.")

    try:
        encrypted = base64.b64decode(req.ciphertext_b64)
    except Exception:
        raise HTTPException(400, "Ciphertext base64 invalide.")

    t1 = time.perf_counter()
    decrypted_bytes = rsa_decrypt_bytes(encrypted, _dynamic_key["d"], _dynamic_key["n"])
    t_dec = round((time.perf_counter() - t1) * 1000, 3)

    try:
        original_message = decrypted_bytes.decode("utf-8")
    except Exception:
        raise HTTPException(400, "Impossible de decoder le message en UTF-8. Cle incorrecte.")

    msg_hash = hashlib.sha256(decrypted_bytes).hexdigest()

    t2 = time.perf_counter()
    sig_valid = False
    sigma = None
    h_recalc = 0
    h_extrait = 0
    try:
        sigma = int(base64.b64decode(req.signature_b64.strip().encode()).decode())
        sig_valid, h_recalc, h_extrait = verify_sig(decrypted_bytes, sigma, _STATIC["e"], _STATIC["n"])
    except Exception:
        pass
    t_verif = round((time.perf_counter() - t2) * 1000, 3)

    return {
        "original_message": original_message,
        "message_hash":     msg_hash,
        "signature_valid":  sig_valid,
        "timing": {
            "dechiffrement_ms":    t_dec,
            "verification_sig_ms": t_verif,
        },
        "formulas": {
            "dechiffrement": f"M = C^d mod n  (d={_dynamic_key['d']}, n={_dynamic_key['n']})",
            "hash":          f"h_recalc = SHA-256(M) mod n_stat = {h_recalc}",
            "verification":  f"h_extrait = sigma^e mod n = {sigma}^{_STATIC['e']} mod {_STATIC['n']} = {h_extrait} | {'VALIDE' if sig_valid else 'INVALIDE'}",
        },
        "message": "Message dechiffre avec succes",
    }