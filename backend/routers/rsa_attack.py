from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import math
import random
from fractions import Fraction

router = APIRouter()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MEMBRE 3 — RSA Attack
#  Routes disponibles sur /api/rsa-attack/...
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# ── Utilitaires mathématiques ────────────────────────────────────

def extended_gcd(a: int, b: int):
    if b == 0:
        return a, 1, 0
    g, x, y = extended_gcd(b, a % b)
    return g, y, x - (a // b) * y

def mod_inverse(e: int, phi: int) -> Optional[int]:
    g, x, _ = extended_gcd(e, phi)
    if g != 1:
        return None
    return x % phi

def isqrt(n: int) -> int:
    if n < 0:
        raise ValueError("Square root not defined for negative numbers")
    if n == 0:
        return 0
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x

def is_perfect_square(n: int) -> Optional[int]:
    s = isqrt(n)
    if s * s == n:
        return s
    return None

def integer_nth_root(k: int, n: int) -> int:
    """Calcule la racine n-ième entière de k."""
    if k == 0:
        return 0
    # Newton's method
    x = int(round(k ** (1.0 / n)))
    # Adjust around the estimate
    while True:
        x1 = ((n - 1) * x + k // (x ** (n - 1))) // n
        if x1 >= x:
            break
        x = x1
    # Fine-tune
    while x ** n > k:
        x -= 1
    while (x + 1) ** n <= k:
        x += 1
    return x

def continued_fraction_expansion(num: int, den: int) -> List[int]:
    """Développement en fractions continues de num/den."""
    coeffs = []
    while den:
        q = num // den
        coeffs.append(q)
        num, den = den, num - q * den
    return coeffs

def convergents(coeffs: List[int]):
    """Génère les convergents via la récurrence standard (100% entiers)."""
    n0, d0 = 1, 0  # h_{-1}, k_{-1}
    n1, d1 = coeffs[0], 1  # h_0, k_0
    yield n1, d1
    for c in coeffs[1:]:
        n0, n1 = n1, c * n1 + n0
        d0, d1 = d1, c * d1 + d0
        yield n1, d1

def crt(remainders: List[int], moduli: List[int]) -> int:
    """Théorème chinois des restes."""
    M = 1
    for m in moduli:
        M *= m
    result = 0
    for r, m in zip(remainders, moduli):
        Mi = M // m
        _, inv, _ = extended_gcd(Mi, m)
        inv = inv % m
        result += r * Mi * inv
    return result % M


# ── Modèles Pydantic ─────────────────────────────────────────────

class FactorizeRequest(BaseModel):
    n: int

class WienerRequest(BaseModel):
    e: int
    n: int

class HastadRequest(BaseModel):
    ciphertexts: List[int]
    moduli: List[int]
    e: int = 3

class WeakKeyGenRequest(BaseModel):
    bits: int = 16
    attack_type: str = "factorize"

class ManualFactorizeRequest(BaseModel):
    n: int
    e: Optional[int] = None        # optionnel : si fourni, on calcule d directement

class ManualWienerRequest(BaseModel):
    e: int
    n: int
    # p et q optionnels : si fournis, on vérifie si d est bien vulnérable
    p: Optional[int] = None
    q: Optional[int] = None

class ManualHastadRequest(BaseModel):
    ciphertexts: List[int]
    moduli: List[int]
    e: int = 3
    # message optionnel pour vérification
    message: Optional[int] = None


# ── Route status ─────────────────────────────────────────────────

@router.get("/status")
def rsa_attack_status():
    return {"module": "RSA Attack", "status": "✅ Implémenté — Membre 3"}


# ── 1. Génération de clés FAIBLES (pour la démo) ─────────────────

@router.post("/generate-weak-key")
def generate_weak_key(req: WeakKeyGenRequest):
    """
    Génère une paire de clés RSA intentionnellement faible pour la démo.
    - factorize : p et q de petite taille (bits=16 max)
    - wiener    : d choisi petit < n^0.25
    - hastad    : e=3, même message pour 3 clés différentes
    """
    steps = []

    if req.attack_type == "factorize":
        bits = min(req.bits, 20)  # cap à 20 bits pour la démo
        steps.append(f"Génération de p et q avec seulement {bits} bits chacun")

        def gen_prime(bits):
            while True:
                n = random.getrandbits(bits) | (1 << (bits - 1)) | 1
                if all(n % i != 0 for i in range(2, int(n**0.5) + 1)):
                    return n

        p = gen_prime(bits)
        q = gen_prime(bits)
        while q == p:
            q = gen_prime(bits)

        n = p * q
        phi = (p - 1) * (q - 1)
        e = 65537
        while math.gcd(e, phi) != 1:
            e = random.choice([3, 17, 257, 65537])
        d = mod_inverse(e, phi)

        steps.append(f"p = {p}, q = {q}")
        steps.append(f"n = p × q = {n}")
        steps.append(f"φ(n) = (p-1)(q-1) = {phi}")
        steps.append(f"e = {e}, d = {d}")
        steps.append("⚠️ Vulnérabilité : n est petit, factorisation triviale !")

        return {
            "attack_type": "factorize",
            "public_key": {"e": e, "n": n},
            "private_key": {"d": d, "p": p, "q": q},
            "steps": steps,
            "warning": f"n={n} peut être factorisé en quelques millisecondes !"
        }

    elif req.attack_type == "wiener":
        steps.append("Génération d'une clé RSA avec d petit (attaque de Wiener)")
        # 24 bits par premier -> n ~ 48 bits -> sous 2^53 (limite JSON/JS)
        bits = 24
        def gen_prime_w(b):
            while True:
                candidate = random.getrandbits(b) | (1 << (b - 1)) | 1
                if all(candidate % i != 0 for i in range(2, isqrt(candidate) + 1)):
                    return candidate

        p = gen_prime_w(bits)
        q = gen_prime_w(bits)
        while q == p:
            q = gen_prime_w(bits)

        n = p * q
        phi = (p - 1) * (q - 1)

        threshold = isqrt(isqrt(n))
        max_d = max(2, threshold // 3)
        d = random.randint(2, max_d)
        attempts = 0
        while math.gcd(d, phi) != 1:
            d = random.randint(2, max_d)
            attempts += 1
            if attempts > 1000:
                d = 2
                break

        e_val = mod_inverse(d, phi)
        if e_val is None:
            e_val = 65537
            d = mod_inverse(e_val, phi)

        steps.append(f"p = {p}, q = {q}")
        steps.append(f"n = {n}  (48 bits — sûr pour JSON)")
        steps.append(f"d choisi = {d}  (seuil n^0.25/3 = {max_d})")
        steps.append(f"e calculé = {e_val}")
        steps.append("⚠️ Vulnérabilité : d < n^0.25/3, l'attaque de Wiener s'applique !")

        return {
            "attack_type": "wiener",
            "public_key": {"e": e_val, "n": n},
            "private_key": {"d": d, "p": p, "q": q},
            "steps": steps,
            "warning": f"d={d} est trop petit ! (n^0.25 ≈ {threshold}, seuil/3 = {max_d})"
        }

    elif req.attack_type == "hastad":
        steps.append("Génération de 3 paires de clés RSA avec e=3 (attaque de Håstad)")
        e = 3
        keys = []

        def gen_prime_hastad(bits=24):
            while True:
                candidate = random.getrandbits(bits) | (1 << (bits - 1)) | 1
                if candidate % 3 != 0 and all(
                    candidate % i != 0 for i in range(2, min(500, int(candidate**0.5) + 1))
                ):
                    return candidate

        for i in range(3):
            p = gen_prime_hastad()
            q = gen_prime_hastad()
            while q == p:
                q = gen_prime_hastad()
            n = p * q
            phi = (p - 1) * (q - 1)
            d = mod_inverse(e, phi)
            keys.append({"p": p, "q": q, "n": n, "e": e, "d": d})
            steps.append(f"Clé {i+1} : n={n}, e={e}, d={d}")

        # Chiffrer un message commun
        message = random.randint(2, min(keys[0]["n"], keys[1]["n"], keys[2]["n"]) - 1)
        ciphertexts = [pow(message, e, k["n"]) for k in keys]
        steps.append(f"Message secret m = {message}")
        steps.append(f"c1 = m^e mod n1 = {ciphertexts[0]}")
        steps.append(f"c2 = m^e mod n2 = {ciphertexts[1]}")
        steps.append(f"c3 = m^e mod n3 = {ciphertexts[2]}")
        steps.append("⚠️ Vulnérabilité : e=3, même message → CRT révèle m³ → racine cubique = m !")

        return {
            "attack_type": "hastad",
            "keys": keys,
            "message": message,
            "ciphertexts": ciphertexts,
            "moduli": [k["n"] for k in keys],
            "e": e,
            "steps": steps,
            "warning": "Avec e=3 et 3 chiffrements du même message, m est récupérable !"
        }

    raise HTTPException(status_code=400, detail="Type d'attaque inconnu")


# ── 2. Factorisation de n ────────────────────────────────────────

@router.post("/factorize")
def factorize(req: FactorizeRequest):
    """
    Factorisation de n par force brute (√n) + algorithme de Fermat.
    Retrouve p et q, puis recalcule d.
    """
    n = req.n
    steps = []
    steps.append(f"Cible : n = {n}")
    steps.append(f"Seuil de recherche : √n ≈ {isqrt(n)}")

    if n < 4:
        raise HTTPException(status_code=400, detail="n doit être ≥ 4")
    if n > 10**14:
        raise HTTPException(status_code=400, detail="n trop grand pour la démo (max 10^14)")

    # Méthode 1 : Factorisation de Fermat
    steps.append("── Méthode : Factorisation de Fermat ──")
    steps.append("On cherche a, b tels que n = a² - b² = (a+b)(a-b)")
    a = isqrt(n)
    if a * a < n:
        a += 1

    found = False
    iterations = 0
    max_iter = 100000

    while iterations < max_iter:
        b2 = a * a - n
        b = is_perfect_square(b2)
        if b is not None:
            p = a + b
            q = a - b
            if q > 1 and p > 1:
                steps.append(f"Trouvé à l'itération {iterations + 1} : a={a}, b={b}")
                steps.append(f"p = a + b = {p}")
                steps.append(f"q = a - b = {q}")
                found = True
                break
        a += 1
        iterations += 1

    if not found:
        # Fallback : force brute
        steps.append("Fermat échoue, passage en force brute…")
        for i in range(2, isqrt(n) + 1):
            if n % i == 0:
                p, q = i, n // i
                steps.append(f"Diviseur trouvé : {i} (après {i-1} essais)")
                found = True
                break

    if not found:
        return {
            "success": False,
            "steps": steps,
            "result": {},
            "explanation": "Factorisation échouée — n est probablement trop grand ou premier."
        }

    phi = (p - 1) * (q - 1)
    steps.append(f"φ(n) = (p-1)(q-1) = {phi}")

    # On suppose e = 65537 ou on le retrouve avec différents e
    common_e = [3, 17, 257, 65537]
    d = None
    e_found = None
    for e_candidate in common_e:
        if math.gcd(e_candidate, phi) == 1:
            d_candidate = mod_inverse(e_candidate, phi)
            e_found = e_candidate
            d = d_candidate
            steps.append(f"Clé privée recalculée avec e={e_candidate} : d = {d}")
            break

    return {
        "success": True,
        "attack_name": "Factorisation de n (Fermat)",
        "result": {
            "p": p,
            "q": q,
            "phi": phi,
            "e": e_found,
            "d": d
        },
        "steps": steps,
        "complexity": f"O(√n) ≈ {isqrt(n)} itérations max",
        "explanation": (
            "Si n est le produit de deux premiers proches (p ≈ q), "
            "la factorisation de Fermat est quasi-instantanée. "
            "La vulnérabilité est de choisir des clés avec des petits nombres premiers."
        )
    }


# ── 3. Attaque de Wiener ─────────────────────────────────────────

@router.post("/wiener")
def wiener_attack(req: WienerRequest):
    """Attaque de Wiener avec tableau détaillé des fractions continues."""
    e, n = req.e, req.n
    threshold = isqrt(isqrt(n)) // 3
    table_rows = []  # tableau détaillé pour le frontend

    coeffs = continued_fraction_expansion(e, n)

    # Calcul manuel avec récurrence pour avoir les détails de chaque étape
    h_prev, h_curr = 1, coeffs[0]   # h_{-1}=1, h_0=a_0
    k_prev, k_curr = 0, 1           # k_{-1}=0, k_0=1

    # étape 0
    table_rows.append({
        "i": 0, "a": coeffs[0],
        "k_calc": f"k0={coeffs[0]}", "d_calc": f"d0=1",
        "k": h_curr, "d": k_curr,
        "fraction": f"{h_curr}/{k_curr}"
    })

    found = False
    result_data = {}
    steps = [f"e={e}, n={n}", f"Seuil Wiener : n^(1/4)/3 ≈ {threshold}",
             f"Coefficients FC : {coeffs[:10]}{'…' if len(coeffs)>10 else ''}"]

    for i, a in enumerate(coeffs[1:], start=1):
        h_new = a * h_curr + h_prev
        k_new = a * k_curr + k_prev

        table_rows.append({
            "i": i, "a": a,
            "k_calc": f"k{i}=({a}×{h_curr})+{h_prev}={h_new}",
            "d_calc": f"d{i}=({a}×{k_curr})+{k_prev}={k_new}",
            "k": h_new, "d": k_new,
            "fraction": f"{h_new}/{k_new}",
            "is_candidate": False
        })

        k_test, d_test = h_new, k_new
        if k_test > 0 and (e * d_test - 1) % k_test == 0:
            phi_c = (e * d_test - 1) // k_test
            b = n - phi_c + 1
            disc = b * b - 4 * n
            if disc >= 0:
                sq = is_perfect_square(disc)
                if sq is not None:
                    p = (b + sq) // 2
                    q = (b - sq) // 2
                    if p * q == n and p > 1 and q > 1:
                        table_rows[-1]["is_candidate"] = True
                        table_rows[-1]["found"] = True
                        steps.append(f"✅ d trouvé à l'étape {i} : d={d_test}")
                        found = True
                        result_data = {"d": d_test, "p": p, "q": q,
                                       "phi": phi_c, "convergent_index": i}
                        break

        h_prev, h_curr = h_curr, h_new
        k_prev, k_curr = k_curr, k_new

    if not found:
        steps.append("Wiener échoue — d n'est pas assez petit")

    return {
        "success": found,
        "attack_name": "Attaque de Wiener",
        "result": result_data,
        "steps": steps,
        "table": table_rows,
        "complexity": "O(log² n)",
        "explanation": (
            "L'attaque de Wiener exploite le théorème des fractions continues : "
            "si d < n^0.25/3, alors k/d apparaît parmi les convergents de e/n."
        )
    }
    


# ── 4. Attaque de Håstad (Broadcast Attack, e=3) ─────────────────

@router.post("/hastad")
def hastad_attack(req: HastadRequest):
    """
    Attaque de Håstad : si le même message m est chiffré avec e=3 pour 3 destinataires,
    on retrouve m³ via le CRT, puis on calcule la racine cubique entière.
    Référence : Håstad, J. (1988). "Solving Simultaneous Modular Equations of Low Degree."
    """
    ciphertexts = req.ciphertexts
    moduli = req.moduli
    e = req.e

    steps = []

    if len(ciphertexts) < e or len(moduli) < e:
        raise HTTPException(
            status_code=400,
            detail=f"Il faut au moins {e} chiffrés et {e} modules pour e={e}"
        )

    # Utiliser exactement e valeurs
    c = ciphertexts[:e]
    n = moduli[:e]

    steps.append(f"Exposant public : e = {e}")
    for i in range(e):
        steps.append(f"c{i+1} = {c[i]}  (mod n{i+1} = {n[i]})")

    # Vérifier que les modules sont copremiers deux à deux
    for i in range(e):
        for j in range(i + 1, e):
            g = math.gcd(n[i], n[j])
            if g != 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"n{i+1} et n{j+1} ne sont pas copremiers (gcd={g})"
                )

    steps.append("── Application du Théorème Chinois des Restes (CRT) ──")
    steps.append("On calcule M = c1·M1·y1 + c2·M2·y2 + c3·M3·y3 (mod N)")

    # CRT : retrouver m^e mod (n1*n2*...*ne)
    m_e = crt(c, n)
    N = 1
    for ni in n:
        N *= ni

    steps.append(f"N = n1 × n2 × … = {N}")
    steps.append(f"m^{e} ≡ {m_e} (mod N)")
    steps.append(f"── Calcul de la racine {e}-ième entière ──")

    # Racine e-ième entière de m_e
    m_recovered = integer_nth_root(m_e, e)

    # Vérification
    if m_recovered ** e == m_e:
        steps.append(f"✅ Racine exacte trouvée : m = {m_recovered}")
        steps.append(f"Vérification : {m_recovered}^{e} = {m_recovered**e} = m^{e} ✓")
        verified = True
    else:
        steps.append(f"⚠️ m ≈ {m_recovered} (vérification approximative)")
        verified = False

    return {
        "success": True,
        "attack_name": f"Attaque de Håstad (e={e})",
        "result": {
            "message": m_recovered,
            "m_cubed": m_e,
            "verified": verified
        },
        "steps": steps,
        "complexity": "O(e³ · log N)",
        "explanation": (
            f"Avec e={e} et le même message m chiffré pour {e} destinataires différents, "
            f"le CRT reconstruit m^{e} sans chiffrement cassé. "
            f"La racine {e}-ième entière donne m directement. "
            "Solution : utiliser du padding aléatoire (OAEP) qui rend chaque chiffré unique."
        )
    }


# ── 5. Encrypt/Decrypt simple (pour la démo des attaques) ────────

class EncryptRequest(BaseModel):
    message: int
    e: int
    n: int

class DecryptRequest(BaseModel):
    ciphertext: int
    d: int
    n: int

# ── Routes manuelles ─────────────────────────────────────────────

@router.post("/manual-factorize")
def manual_factorize(req: ManualFactorizeRequest):
    """
    Factorisation avec n saisi manuellement.
    Si e est fourni, calcule aussi d après factorisation.
    """
    steps = [f"Entrée manuelle : n = {req.n}"]
    if req.e:
        steps.append(f"e fourni : {req.e}")

    if req.n < 4:
        raise HTTPException(status_code=400, detail="n doit être ≥ 4")
    if req.n > 10**14:
        raise HTTPException(status_code=400, detail="n trop grand (max 10^14)")

    # Factorisation de Fermat
    a = isqrt(req.n)
    if a * a < req.n:
        a += 1
    found = False
    p = q = None
    for _ in range(200000):
        b2 = a * a - req.n
        b = is_perfect_square(b2)
        if b is not None:
            p, q = a + b, a - b
            if p > 1 and q > 1:
                found = True
                break
        a += 1
    if not found:
        for i in range(2, isqrt(req.n) + 1):
            if req.n % i == 0:
                p, q = i, req.n // i
                found = True
                break

    if not found:
        return {"success": False, "steps": steps, "result": {},
                "explanation": "Impossible de factoriser ce n — trop grand ou premier."}

    phi = (p - 1) * (q - 1)
    steps.append(f"p = {p}, q = {q}, φ(n) = {phi}")

    result = {"p": p, "q": q, "phi": phi}
    if req.e:
        if math.gcd(req.e, phi) != 1:
            steps.append(f"⚠️ pgcd(e={req.e}, φ(n))≠1 — e invalide pour ce n")
        else:
            d = mod_inverse(req.e, phi)
            result["e"] = req.e
            result["d"] = d
            steps.append(f"d = e⁻¹ mod φ(n) = {d}")
    else:
        for e_try in [3, 17, 257, 65537]:
            if math.gcd(e_try, phi) == 1:
                result["e"] = e_try
                result["d"] = mod_inverse(e_try, phi)
                steps.append(f"e supposé = {e_try}, d = {result['d']}")
                break

    return {"success": True, "attack_name": "Factorisation manuelle",
            "result": result, "steps": steps,
            "complexity": f"O(√n)", "explanation": "Factorisation réussie sur les valeurs saisies."}


@router.post("/manual-wiener")
def manual_wiener(req: ManualWienerRequest):
    """
    Attaque de Wiener sur e, n saisis manuellement.
    Si p et q sont fournis, on vérifie d'abord si la clé est vulnérable.
    """
    steps = [f"Entrée manuelle : e = {req.e}, n = {req.n}"]
    threshold = isqrt(isqrt(req.n)) // 3
    steps.append(f"Seuil Wiener : n^(1/4)/3 ≈ {threshold}")

    # Si p et q fournis : vérification préalable
    if req.p and req.q:
        if req.p * req.q != req.n:
            raise HTTPException(status_code=400, detail="p × q ≠ n — valeurs incohérentes")
        phi = (req.p - 1) * (req.q - 1)
        d_real = mod_inverse(req.e, phi)
        steps.append(f"p={req.p}, q={req.q} fournis → φ(n)={phi}, d réel={d_real}")
        if d_real and d_real <= threshold:
            steps.append(f"✅ d={d_real} < seuil={threshold} → clé vulnérable à Wiener !")
        else:
            steps.append(f"⚠️ d={d_real} ≥ seuil={threshold} → clé NON vulnérable à Wiener")

    # Lancer l'attaque
    coeffs = continued_fraction_expansion(req.e, req.n)
    steps.append(f"Coefficients FC : {coeffs[:10]}{'…' if len(coeffs)>10 else ''}")

    table_rows = []
    h_prev, h_curr = 1, coeffs[0]
    k_prev, k_curr = 0, 1
    table_rows.append({"i":0,"a":coeffs[0],"k_calc":f"k0={coeffs[0]}","d_calc":"d0=1","k":h_curr,"d":k_curr,"fraction":f"{h_curr}/{k_curr}","is_candidate":False,"found":False})

    found = False
    result_data = {}
    for i, a in enumerate(coeffs[1:], start=1):
        h_new = a * h_curr + h_prev
        k_new = a * k_curr + k_prev
        row = {"i":i,"a":a,"k_calc":f"k{i}=({a}×{h_curr})+{h_prev}={h_new}",
               "d_calc":f"d{i}=({a}×{k_curr})+{k_prev}={k_new}",
               "k":h_new,"d":k_new,"fraction":f"{h_new}/{k_new}","is_candidate":False,"found":False}
        if h_new > 0 and (req.e * k_new - 1) % h_new == 0:
            phi_c = (req.e * k_new - 1) // h_new
            b = req.n - phi_c + 1
            disc = b * b - 4 * req.n
            if disc >= 0:
                sq = is_perfect_square(disc)
                if sq is not None:
                    pp = (b + sq) // 2
                    qq = (b - sq) // 2
                    if pp * qq == req.n and pp > 1 and qq > 1:
                        row["is_candidate"] = True
                        row["found"] = True
                        found = True
                        result_data = {"d": k_new, "p": pp, "q": qq, "phi": phi_c, "convergent_index": i}
                        steps.append(f"✅ d trouvé à l'étape {i} : d={k_new}")
        table_rows.append(row)
        h_prev, h_curr = h_curr, h_new
        k_prev, k_curr = k_curr, k_new
        if found:
            break

    if not found:
        steps.append("Wiener échoue sur ces valeurs — d non vulnérable")

    return {"success": found, "attack_name": "Wiener (manuel)",
            "result": result_data, "steps": steps, "table": table_rows,
            "complexity": "O(log² n)",
            "explanation": "Attaque de Wiener sur valeurs saisies manuellement."}


@router.post("/manual-hastad")
def manual_hastad(req: ManualHastadRequest):
    """
    Attaque de Håstad sur ciphertexts/moduli saisis manuellement.
    Vérifie optionnellement contre le message fourni.
    """
    if len(req.ciphertexts) < req.e or len(req.moduli) < req.e:
        raise HTTPException(status_code=400, detail=f"Il faut au moins {req.e} chiffrés et modules")

    steps = [f"Entrée manuelle : e={req.e}"]
    c = req.ciphertexts[:req.e]
    n = req.moduli[:req.e]
    for i in range(req.e):
        steps.append(f"c{i+1}={c[i]} mod n{i+1}={n[i]}")
        for j in range(i+1, req.e):
            if math.gcd(n[i], n[j]) != 1:
                raise HTTPException(status_code=400, detail=f"n{i+1} et n{j+1} ne sont pas copremiers")

    m_e = crt(c, n)
    N = 1
    for ni in n: N *= ni
    steps.append(f"CRT → m^{req.e} = {m_e} mod N")

    m_recovered = integer_nth_root(m_e, req.e)
    verified = m_recovered ** req.e == m_e

    if req.message is not None:
        if m_recovered == req.message:
            steps.append(f"✅ Message vérifié : m={m_recovered} correspond au message fourni")
        else:
            steps.append(f"⚠️ m récupéré={m_recovered} ≠ message fourni={req.message}")

    steps.append(f"Racine {req.e}-ième : m = {m_recovered} {'✅' if verified else '≈'}")

    return {"success": True, "attack_name": f"Håstad manuel (e={req.e})",
            "result": {"message": m_recovered, "verified": verified},
            "steps": steps, "complexity": f"O(e³·log N)",
            "explanation": f"Attaque de Håstad sur valeurs saisies manuellement avec e={req.e}."}


@router.post("/encrypt")
def encrypt_demo(req: EncryptRequest):
    if req.message >= req.n:
        raise HTTPException(status_code=400, detail="Le message doit être < n")
    c = pow(req.message, req.e, req.n)
    return {"ciphertext": c, "message": req.message, "e": req.e, "n": req.n}

@router.post("/decrypt")
def decrypt_demo(req: DecryptRequest):
    m = pow(req.ciphertext, req.d, req.n)
    return {"message": m, "ciphertext": req.ciphertext}
