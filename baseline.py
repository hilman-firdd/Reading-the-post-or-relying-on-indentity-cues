#!/usr/bin/env python3
"""
Local, non-generative moderation baselines (no LLM needed).

  word-LR : TF-IDF word 1-2 grams + logistic regression; evidence = up to 5 tokens of the
            post with the largest positive contribution to the 'violating' score
  char-LR : TF-IDF char 2-5 grams + logistic regression; gives no evidence

Both are trained on the HateXplain TRAIN split (binary: hatespeech/offensive = violating)
and never read the policy text, so they are policy-blind by construction. Outputs follow
the run format used by evaluate.py.
"""
import argparse, json, re
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

def majority(p):
    lab, c = Counter(a["label"] for a in p["annotators"]).most_common(1)[0]
    return lab if c >= 2 else None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--splits", required=True)
    ap.add_argument("--items", required=True); ap.add_argument("--out-prefix", required=True); a = ap.parse_args()
    d = json.load(open(a.data)); sp = json.load(open(a.splits))
    tr = [d[i] for i in sp["train"] if i in d and majority(d[i])]
    X = [" ".join(p["post_tokens"]) for p in tr]; y = [int(majority(p) != "normal") for p in tr]
    items = [json.loads(l) for l in open(a.items)]; items = [i for i in items if i.get("text")]
    texts = [i["text"] for i in items]
    for name, vec in {"word-LR": TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, token_pattern=r"\S+"),
                      "char-LR": TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True)}.items():
        Xtr = vec.fit_transform(X); clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced").fit(Xtr, y)
        Xte = vec.transform(texts); prob = clf.predict_proba(Xte)[:, 1]
        vocab = vec.vocabulary_; coef = clf.coef_[0]
        with open(f"{a.out_prefix}_{name}.jsonl", "w") as f:
            for it, pr, row in zip(items, prob, Xte):
                verdict = "violating" if pr >= 0.5 else "not_violating"
                quotes = []
                if name == "word-LR" and verdict == "violating":
                    contrib = {}
                    for t in set(it["text"].split()):
                        j = vocab.get(t)
                        if j is not None: contrib[t] = row[0, j] * coef[j]
                    quotes = [t for t, c in sorted(contrib.items(), key=lambda x: -x[1]) if c > 0][:5]
                f.write(json.dumps({"item_id": it["item_id"], "system": name, "verdict": verdict,
                                    "quotes": quotes, "confidence": round(float(max(pr, 1 - pr)), 4)}) + "\n")
        print(name, "done", len(items))

if __name__ == "__main__":
    main()
