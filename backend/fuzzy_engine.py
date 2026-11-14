"""
Fuzzy TOPSIS Engine for Chatbot Response Quality Assessment
============================================================
Implements Fuzzy TOPSIS with Triangular Fuzzy Numbers (TFNs)
and absolute ideal solutions (Chen 2000, adapted).

Linguistic scale (5-term):
  Very Poor (1) → Very Good (5)

Each rating r ∈ {1,2,3,4,5} maps to a TFN:
  TFN(r) = (max(0, r̃ - δ), r̃, min(1, r̃ + δ))
  where r̃ = (r-1)/4 and δ = 0.25
"""

import math
from dataclasses import dataclass


# ── Triangular Fuzzy Number ───────────────────────────────────────

@dataclass
class TFN:
    """Triangular Fuzzy Number (l, m, u) where l ≤ m ≤ u."""
    l: float  # lower bound
    m: float  # peak / most likely
    u: float  # upper bound

    def __add__(self, other: "TFN") -> "TFN":
        return TFN(self.l + other.l, self.m + other.m, self.u + other.u)

    def scale(self, w: float) -> "TFN":
        """Multiply by a crisp weight w ≥ 0."""
        return TFN(self.l * w, self.m * w, self.u * w)

    def centroid(self) -> float:
        """Defuzzify: g = (l + m + u) / 3."""
        return (self.l + self.m + self.u) / 3.0

    def distance_to(self, other: "TFN") -> float:
        """Vertex distance: d(ã, b̃) = √[(1/3)((l₁-l₂)² + (m₁-m₂)² + (u₁-u₂)²)]"""
        return math.sqrt(
            ((self.l - other.l) ** 2 +
             (self.m - other.m) ** 2 +
             (self.u - other.u) ** 2) / 3.0
        )

    def to_dict(self) -> dict:
        return {"l": round(self.l, 4), "m": round(self.m, 4), "u": round(self.u, 4)}


# ── Linguistic Scale ──────────────────────────────────────────────

LINGUISTIC_LABELS = {
    1: "Very Poor",
    2: "Poor",
    3: "Fair",
    4: "Good",
    5: "Very Good",
}

DELTA = 0.25

def rating_to_tfn(r: int) -> TFN:
    """
    Map a 1–5 rating to a TFN on [0, 1].
    r̃ = (r-1)/4, TFN = (max(0, r̃-δ), r̃, min(1, r̃+δ))
    """
    assert 1 <= r <= 5, f"Rating must be 1–5, got {r}"
    r_norm = (r - 1) / 4.0
    return TFN(
        l=max(0.0, r_norm - DELTA),
        m=r_norm,
        u=min(1.0, r_norm + DELTA),
    )


# ── Fuzzy TOPSIS ──────────────────────────────────────────────────

def normalize_weights(importance: list[int]) -> list[float]:
    """
    Normalize importance ratings (1–5 each) to crisp weights summing to 1.
    """
    total = sum(importance)
    return [w / total for w in importance]


def fuzzy_topsis(
    ratings: dict[str, list[int]],
    criteria_weights: list[int],
    criteria_names: list[str] | None = None,
) -> dict:
    """
    Run Fuzzy TOPSIS on chatbot response ratings.

    Args:
        ratings: {model_name: [rating_c1, rating_c2, ...]}
                 Each rating is 1–5 (linguistic scale).
        criteria_weights: importance of each criterion (1–5 each).
        criteria_names: optional labels for criteria.

    Returns:
        Dict with ranking, scores, distances, TFNs, and explanations.
    """
    model_names = list(ratings.keys())
    n_criteria = len(criteria_weights)

    if criteria_names is None:
        criteria_names = [f"C{i+1}" for i in range(n_criteria)]

    # Step 1: Normalize weights
    w = normalize_weights(criteria_weights)

    # Step 2: Build weighted fuzzy decision matrix
    # For each model, for each criterion: wTFN = w_j × TFN(r_ij)
    weighted_matrix = {}
    raw_tfn_matrix = {}
    for model in model_names:
        raw_tfns = [rating_to_tfn(r) for r in ratings[model]]
        raw_tfn_matrix[model] = raw_tfns
        weighted_matrix[model] = [tfn.scale(w[j]) for j, tfn in enumerate(raw_tfns)]

    # Step 3: Absolute ideal solutions (all criteria are benefit-type)
    # FPIS: each criterion's ideal is (w_j, w_j, w_j)
    # FNIS: each criterion's anti-ideal is (0, 0, 0)
    fpis = [TFN(w[j], w[j], w[j]) for j in range(n_criteria)]
    fnis = [TFN(0.0, 0.0, 0.0) for j in range(n_criteria)]

    # Step 4: Compute distances
    results = {}
    for model in model_names:
        d_plus = sum(
            weighted_matrix[model][j].distance_to(fpis[j])
            for j in range(n_criteria)
        )
        d_minus = sum(
            weighted_matrix[model][j].distance_to(fnis[j])
            for j in range(n_criteria)
        )

        # Closeness coefficient
        cc = d_minus / (d_plus + d_minus) if (d_plus + d_minus) > 0 else 0.0

        # Aggregate TFN (sum of weighted TFNs)
        agg = TFN(0, 0, 0)
        for j in range(n_criteria):
            agg = agg + weighted_matrix[model][j]

        results[model] = {
            "d_plus": round(d_plus, 4),
            "d_minus": round(d_minus, 4),
            "cc": round(cc, 4),
            "aggregate_tfn": agg.to_dict(),
            "centroid": round(agg.centroid(), 4),
            "weighted_tfns": {
                criteria_names[j]: weighted_matrix[model][j].to_dict()
                for j in range(n_criteria)
            },
            "raw_tfns": {
                criteria_names[j]: raw_tfn_matrix[model][j].to_dict()
                for j in range(n_criteria)
            },
        }

    # Step 5: Rank by CC (higher = better)
    ranking = sorted(model_names, key=lambda m: results[m]["cc"], reverse=True)

    # Generate explanation
    explanation = _generate_explanation(
        ranking, results, criteria_names, w, ratings
    )

    return {
        "ranking": ranking,
        "scores": {m: results[m] for m in model_names},
        "weights": {criteria_names[j]: round(w[j], 4) for j in range(n_criteria)},
        "explanation": explanation,
    }


def _generate_explanation(
    ranking: list[str],
    results: dict,
    criteria_names: list[str],
    weights: list[float],
    ratings: dict[str, list[int]],
) -> dict:
    """Generate human-readable explanation of the ranking."""
    best = ranking[0]
    best_cc = results[best]["cc"]

    # Per-criterion breakdown
    criterion_analysis = []
    for j, cname in enumerate(criteria_names):
        scores_for_criterion = {
            model: ratings[model][j] for model in ranking
        }
        winner = max(scores_for_criterion, key=scores_for_criterion.get)
        criterion_analysis.append({
            "criterion": cname,
            "weight": round(weights[j], 4),
            "scores": {m: {"rating": ratings[m][j], "label": LINGUISTIC_LABELS[ratings[m][j]]}
                       for m in ranking},
            "best": winner,
        })

    # Separability between top two
    sep = None
    if len(ranking) >= 2:
        second = ranking[1]
        cc_diff = best_cc - results[second]["cc"]
        if cc_diff < 0.05:
            confidence = "very close — practically tied"
        elif cc_diff < 0.15:
            confidence = "moderate difference"
        else:
            confidence = "clear winner"
        sep = {
            "cc_difference": round(cc_diff, 4),
            "confidence": confidence,
        }

    # Summary sentence
    summary = f"{best} ranks first with CC = {best_cc:.4f}."
    if sep:
        summary += f" The gap to {ranking[1]} is {sep['cc_difference']:.4f} ({sep['confidence']})."

    # What drove the result
    best_ratings = ratings[best]
    weighted_impacts = []
    for j, cname in enumerate(criteria_names):
        impact = weights[j] * best_ratings[j]
        weighted_impacts.append((cname, impact, weights[j], best_ratings[j]))
    weighted_impacts.sort(key=lambda x: x[1], reverse=True)

    drivers = [
        f"{name} (weight {w:.2f} × rating {r}/5)"
        for name, _, w, r in weighted_impacts[:2]
    ]

    return {
        "summary": summary,
        "winner": best,
        "criterion_breakdown": criterion_analysis,
        "separability": sep,
        "top_drivers": drivers,
        "ranking_detail": [
            {"rank": i + 1, "model": m, "cc": results[m]["cc"]}
            for i, m in enumerate(ranking)
        ],
    }


# ── Quick test ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = fuzzy_topsis(
        ratings={
            "Groq (Llama)": [4, 3, 4, 5],
            "Gemini": [3, 5, 3, 4],
        },
        criteria_weights=[5, 4, 3, 3],  # importance
        criteria_names=["Relevance", "Accuracy", "Completeness", "Clarity"],
    )
    print(f"Ranking: {result['ranking']}")
    for m in result['ranking']:
        s = result['scores'][m]
        print(f"  {m}: CC={s['cc']}, d⁺={s['d_plus']}, d⁻={s['d_minus']}")
    print(f"\n{result['explanation']['summary']}")
