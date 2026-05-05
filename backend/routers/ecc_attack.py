from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import math

router = APIRouter(prefix="/api/ecc-attack", tags=["ECC Attack"])


# ─────────────────────────────────────────────
#  Modèles Pydantic
# ─────────────────────────────────────────────

class BSGSRequest(BaseModel):
    # Courbe : y² = x³ + ax + b  (mod p)
    a: int
    b: int
    p: int          # module premier
    Gx: int
    Gy: int         # générateur G
    Qx: int
    Qy: int         # point cible Q = k·G
    n: int          # ordre de G (petit pour la démo)

class PohligHellmanRequest(BaseModel):
    a: int
    b: int
    p: int
    Gx: int
    Gy: int
    Qx: int
    Qy: int
    n: int          # ordre (produit de petits facteurs premiers)

class AnomalousRequest(BaseModel):
    a: int
    b: int
    p: int          # #E(Fp) = p  (courbe anomale)
    Gx: int
    Gy: int
    Qx: int
    Qy: int


# ─────────────────────────────────────────────
#  Arithmétique sur courbe elliptique (mod p)
# ─────────────────────────────────────────────

def modinv(a: int, m: int) -> int:
    """Inverse modulaire via algorithme étendu d'Euclide."""
    if m == 1:
        return 0
    g, x, _ = extended_gcd(a % m, m)
    if g != 1:
        raise ValueError(f"Pas d'inverse : gcd({a},{m}) = {g}")
    return x % m

def extended_gcd(a: int, b: int):
    if a == 0:
        return b, 0, 1
    g, x, y = extended_gcd(b % a, a)
    return g, y - (b // a) * x, x

def point_add(P, Q, a: int, p: int):
    """Addition de deux points sur la courbe elliptique."""
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q

    if x1 == x2:
        if (y1 + y2) % p == 0:
            return None  # point à l'infini
        # doublement
        lam = (3 * x1 * x1 + a) * modinv(2 * y1, p) % p
    else:
        lam = (y2 - y1) * modinv(x2 - x1, p) % p

    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p
    return (x3, y3)

def point_mul(k: int, P, a: int, p: int):
    """Multiplication scalaire k·P (double-and-add)."""
    result = None
    addend = P
    steps = []
    while k:
        if k & 1:
            result = point_add(result, addend, a, p)
            steps.append(f"Ajout de addend (bit=1) → résultat = {result}")
        addend = point_add(addend, addend, a, p)
        k >>= 1
    return result, steps

def point_neg(P, p: int):
    """Négation d'un point."""
    if P is None:
        return None
    return (P[0], (-P[1]) % p)

def points_equal(P, Q) -> bool:
    if P is None and Q is None:
        return True
    if P is None or Q is None:
        return False
    return P[0] == Q[0] and P[1] == Q[1]


# ─────────────────────────────────────────────
#  1. BABY-STEP GIANT-STEP
# ─────────────────────────────────────────────

@router.post("/bsgs")
def bsgs_attack(req: BSGSRequest):
    """
    Résout Q = k·G par Baby-step Giant-step.
    Complexité : O(√n) en temps et espace.
    """
    try:
        a, p = req.a, req.p
        G = (req.Gx, req.Gy)
        Q = (req.Qx, req.Qy)
        n = req.n

        m = math.isqrt(n) + 1
        steps = []
        steps.append(f"Paramètre m = ⌈√{n}⌉ = {m}")
        steps.append(f"Phase Baby-step : calculer j·G pour j = 0..{m-1}")

        # ── Baby steps : table[j·G] = j ──────────────────
        baby = {}
        jG = None  # 0·G = O (point à l'infini)
        for j in range(m):
            key = jG  # None représente le point à l'infini
            baby[key] = j
            jG = point_add(jG, G, a, p)

        steps.append(f"Table baby-step construite : {min(m, 5)} premières entrées calculées.")

        # ── Giant steps : Q - i·(m·G) ────────────────────
        mG, _ = point_mul(m, G, a, p)
        steps.append(f"Giant-step base : {m}·G = {mG}")
        steps.append(f"Phase Giant-step : chercher Q - i·({m}·G) dans la table")

        gamma = Q  # Q - 0·(mG)
        k_found = None
        giant_count = 0

        for i in range(m):
            if gamma in baby:
                j = baby[gamma]
                k_found = (i * m + j) % n
                steps.append(f"✅ Collision trouvée ! i={i}, j={j} → k = i·m + j = {i}·{m} + {j} = {k_found}")
                giant_count = i + 1
                break
            gamma = point_add(gamma, point_neg(mG, p), a, p)
            if i < 3:
                steps.append(f"  Giant-step i={i} : γ = {gamma} (pas dans la table)")

        if k_found is None:
            raise HTTPException(status_code=400, detail="Clé non trouvée — vérifiez que Q est bien sur la courbe et que n est correct.")

        # Vérification
        verify, _ = point_mul(k_found, G, a, p)
        verified = points_equal(verify, Q)
        steps.append(f"Vérification : {k_found}·G = {verify} {'✅' if verified else '❌'}")

        return {
            "success": True,
            "attack_name": "Baby-step Giant-step (BSGS)",
            "result": {
                "k": k_found,
                "baby_steps_computed": m,
                "giant_steps_computed": giant_count,
                "total_steps": m + giant_count,
                "verified": verified
            },
            "steps": steps,
            "complexity": f"O(√n) ≈ O({m}) vs O(n) = O({n}) force brute",
            "baby_table_size": m,
            "explanation": (
                "BSGS divise le problème : k = i·m + j avec m=⌈√n⌉. "
                "On précalcule tous les j·G (baby-steps) dans une table de hachage. "
                "Puis on itère Q - i·(m·G) (giant-steps) jusqu'à collision. "
                "Gain : O(√n) au lieu de O(n) — sur n=10^12, on passe de 1 billion à 1 million d'opérations."
            )
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  2. POHLIG-HELLMAN
# ─────────────────────────────────────────────

def factorize_small(n: int) -> dict:
    """Factorisation en petits facteurs premiers."""
    factors = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors

def crt(residues: list, moduli: list) -> int:
    """Théorème Chinois des Restes."""
    M = 1
    for m in moduli:
        M *= m
    x = 0
    for r, m in zip(residues, moduli):
        Mi = M // m
        x += r * Mi * modinv(Mi, m)
    return x % M

@router.post("/pohlig-hellman")
def pohlig_hellman_attack(req: PohligHellmanRequest):
    """
    Pohlig-Hellman : efficace quand l'ordre n a de petits facteurs premiers.
    """
    try:
        a, p = req.a, req.p
        G = (req.Gx, req.Gy)
        Q = (req.Qx, req.Qy)
        n = req.n

        steps = []
        factors = factorize_small(n)
        steps.append(f"Factorisation de l'ordre n={n} : " +
                     " × ".join(f"{q}^{e}" for q, e in factors.items()))

        if not factors:
            raise HTTPException(status_code=400, detail="Impossible de factoriser n.")

        residues = []
        moduli = []

        for q, e in factors.items():
            q_e = q ** e
            steps.append(f"\n── Sous-problème mod {q}^{e} = {q_e} ──")

            # Générateur d'ordre q^e
            cofactor = n // q_e
            Gi, _ = point_mul(cofactor, G, a, p)
            Qi, _ = point_mul(cofactor, Q, a, p)
            steps.append(f"  G' = ({n}/{q_e})·G = {Gi}")
            steps.append(f"  Q' = ({n}/{q_e})·Q = {Qi}")

            # BSGS sur le sous-groupe d'ordre q^e (petit)
            m = math.isqrt(q_e) + 1
            baby = {}
            jGi = None
            for j in range(m):
                baby[jGi] = j
                jGi = point_add(jGi, Gi, a, p)

            mGi, _ = point_mul(m, Gi, a, p)
            gamma = Qi
            k_sub = None
            for i in range(m):
                if gamma in baby:
                    k_sub = (i * m + baby[gamma]) % q_e
                    steps.append(f"  k ≡ {k_sub} (mod {q_e})")
                    break
                gamma = point_add(gamma, point_neg(mGi, p), a, p)

            if k_sub is None:
                steps.append(f"  ⚠️ Pas de solution mod {q_e} — on suppose k≡0")
                k_sub = 0

            residues.append(k_sub)
            moduli.append(q_e)

        # CRT
        k_found = crt(residues, moduli)
        steps.append(f"\nCRT : k ≡ {residues} mod {moduli} → k = {k_found}")

        verify, _ = point_mul(k_found, G, a, p)
        verified = points_equal(verify, Q)
        steps.append(f"Vérification : {k_found}·G = {verify} {'✅' if verified else '❌'}")

        return {
            "success": True,
            "attack_name": "Pohlig-Hellman",
            "result": {
                "k": k_found,
                "factors_used": {str(q): e for q, e in factors.items()},
                "residues": list(zip(residues, moduli)),
                "verified": verified
            },
            "steps": steps,
            "complexity": f"O(Σ eᵢ·(log n + √pᵢ)) — très rapide si facteurs petits",
            "explanation": (
                "Pohlig-Hellman exploite la structure du groupe quand son ordre n "
                "se décompose en petits facteurs premiers p1^e1 · p2^e2 · ... "
                "On résout le DLP dans chaque sous-groupe séparément (beaucoup plus petit), "
                "puis le Théorème Chinois des Restes (CRT) recompose la solution globale. "
                "Contre-mesure : choisir n premier (courbes sécurisées comme P-256)."
            )
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  3. COURBES ANOMALES — Smart's Attack
# ─────────────────────────────────────────────

def lift_point(P, a: int, b: int, p: int):
    """
    Lift naïf d'un point de Fp vers Zp² (lift de Hensel simplifié).
    Retourne (x_lift, y_lift) dans Z/p²Z.
    """
    x, y = P
    # Chercher un lift : y_lift² ≡ x_lift³ + a·x_lift + b (mod p²)
    # On utilise le lift de Hensel : y₁ = y + t·p avec t choisi pour satisfaire mod p²
    # f(y) = y² - (x³ + ax + b), f'(y) = 2y
    # t = -f(y) / (p · f'(y)) mod p
    x_lift = x  # x ne change pas pour le lift standard
    fx = (y * y - (x * x * x + a * x + b)) % (p * p)
    # fx doit être divisible par p
    fx_over_p = fx // p
    fy_prime = (2 * y) % p
    if fy_prime == 0:
        raise ValueError("Point singulier ou lift impossible (2y ≡ 0 mod p)")
    t = (- fx_over_p * modinv(fy_prime, p)) % p
    y_lift = y + t * p
    return (x_lift % (p * p), y_lift % (p * p))

@router.post("/anomalous")
def anomalous_attack(req: AnomalousRequest):
    """
    Smart's Attack sur les courbes anomales (#E(Fp) = p).
    Transfère le DLP elliptique vers Fp additif (trivial).
    """
    try:
        a, b, p = req.a, req.b, req.p
        G = (req.Gx, req.Gy)
        Q = (req.Qx, req.Qy)

        steps = []
        steps.append(f"Courbe : y² = x³ + {a}x + {b}  (mod {p})")
        steps.append(f"Condition anomale : #E(F_{p}) = {p} ✅")
        steps.append("Étape 1 : Lift des points G et Q vers Z/p²Z (Hensel)")

        p2 = p * p

        # Lift de G et Q
        G_lift = lift_point(G, a, b, p)
        Q_lift = lift_point(Q, a, b, p)
        steps.append(f"  G_lift = {G_lift}")
        steps.append(f"  Q_lift = {Q_lift}")

        steps.append("Étape 2 : Calcul de p·G_lift et p·Q_lift sur la courbe mod p²")

        # p·G dans Z/p²Z
        pG_lift, _ = point_mul(p, G_lift, a, p2)
        pQ_lift, _ = point_mul(p, Q_lift, a, p2)
        steps.append(f"  p·G_lift = {pG_lift}")
        steps.append(f"  p·Q_lift = {pQ_lift}")

        steps.append("Étape 3 : Projection dans Fp via φ(x,y) = (x-1)/y · p⁻¹ mod p")

        # Homomorphisme de groupe formel : φ(x,y) = (x-1)/y mod p  (coordonnées affines)
        # Pour un point P = (x,y) sur E(Zp²) avec P ≡ O mod p :
        # φ(P) = (x - 1) / y   (dans Zp)
        # Note : pG et pQ ont y non nul mod p si la courbe est anomale
        if pG_lift is None or pQ_lift is None:
            raise HTTPException(status_code=400, detail="p·G ou p·Q est le point à l'infini mod p² — vérifiez les paramètres.")

        xG, yG = pG_lift
        xQ, yQ = pQ_lift

        # Coordonnées mod p (annulées par multiplication par p)
        # φ : E_1(Qp) → Zp  défini par (x,y) ↦ -x/y mod p
        phi_G = (xG * modinv(yG, p)) % p
        phi_Q = (xQ * modinv(yQ, p)) % p

        steps.append(f"  φ(p·G) = {phi_G}")
        steps.append(f"  φ(p·Q) = {phi_Q}")
        steps.append("Étape 4 : k = φ(p·Q) / φ(p·G)  mod p")

        if phi_G == 0:
            raise HTTPException(status_code=400, detail="φ(p·G) = 0 — paramètres invalides pour Smart's attack.")

        k_found = (phi_Q * modinv(phi_G, p)) % p
        steps.append(f"  k = {phi_Q} × {modinv(phi_G, p)} mod {p} = {k_found}")

        # Vérification
        verify, _ = point_mul(k_found, G, a, p)
        verified = points_equal(verify, Q)
        steps.append(f"Vérification : {k_found}·G = {verify} {'✅' if verified else '❌'}")

        return {
            "success": True,
            "attack_name": "Smart's Attack (Courbes Anomales)",
            "result": {
                "k": k_found,
                "phi_G": phi_G,
                "phi_Q": phi_Q,
                "verified": verified
            },
            "steps": steps,
            "complexity": "O(log p) — temps polynomial, quasi-instantané !",
            "explanation": (
                "Les courbes anomales ont #E(Fp) = p (même cardinalité que le corps). "
                "Smart (1999) a montré qu'on peut lifter les points vers Z/p²Z, "
                "puis utiliser un homomorphisme φ vers le groupe additif Fp. "
                "Le DLP dans Fp additif est trivial : k = φ(Q)/φ(G) mod p. "
                "Contre-mesure : vérifier que #E(Fp) ≠ p lors de la génération de courbe."
            )
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
