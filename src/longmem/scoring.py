"""Answer-only EM and token F1; v0.1 normalization preserved."""
import re
import string
from collections import Counter


def score_answer(answer, gold):
    def normalize(text):
        text = text.casefold().translate(str.maketrans('', '', string.punctuation))
        return ' '.join(re.sub(r'\b(a|an|the)\b', ' ', text).split())
    a, b = normalize(answer), normalize(gold)
    common = sum((Counter(a.split()) & Counter(b.split())).values())
    return {'answer.exact_match': int(a == b),
            'answer.token_f1': 2 * common / (len(a.split()) + len(b.split())) if common else 0.0}

