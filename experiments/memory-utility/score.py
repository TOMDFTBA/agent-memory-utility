"""Conservative answer-only exact match and token F1; never substring-match gold."""
import re
import string
from collections import Counter


def normalize(text):
    text=text.casefold().translate(str.maketrans('', '', string.punctuation))
    return ' '.join(re.sub(r'\b(a|an|the)\b', ' ', text).split())


def score(answer, gold):
    a, b=normalize(answer), normalize(gold)
    common=sum((Counter(a.split()) & Counter(b.split())).values())
    f1=2*common/(len(a.split())+len(b.split())) if common else 0.0
    return dict(exact_match=int(a==b), f1=f1)
