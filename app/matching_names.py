from rapidfuzz import fuzz, process
import unicodedata


def normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = unicodedata.normalize("NFKD", name)
    return "".join([c for c in name if not unicodedata.combining(c)])


def match_names(input_name, db_names, threshold=85):
    input_norm = normalize_name(input_name)
    db_norms = [normalize_name(n) for n in db_names]

    _, score, idx = process.extractOne(
        input_norm, db_norms, scorer=fuzz.token_sort_ratio
    )

    if score >= threshold:
        return db_names[idx], score
    return None, score
