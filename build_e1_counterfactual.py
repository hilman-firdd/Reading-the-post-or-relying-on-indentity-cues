#!/usr/bin/env python3
"""
Build the E1 identity-term counterfactual items (protocol: results/e1_counterfactual/PROTOCOL.md).

  python build_e1_counterfactual.py      -> results/e1_counterfactual/items_e1cf.jsonl (+ ORIG items, needed by nothing
                                            but kept so every file is self-contained)
Reads items_llm600.jsonl only. Conditions per E1 post that still contains an identity token:
  REPLAY  unchanged E1 text            NEU     identity tokens -> people/person
  PLC     k random content tokens -> the same neutral nouns     DEL  identity tokens deleted
  PLCDEL  k random content tokens deleted
"""
import hashlib, importlib.util, json, os, random

OUT = "results/e1_counterfactual"
spec = importlib.util.spec_from_file_location("bi", "build_items.py"); bi = importlib.util.module_from_spec(spec); spec.loader.exec_module(bi)
IDENT = set().union(*bi.GROUP_TERMS.values())
STOP = set("the and for are but not you all any can had her was one our out has him his how its may new now old see two who "
           "did get got let put say she too use that this with have from they will would there their what about which when "
           "were been more some them than then these those just like your into over also only very even such because".split())
PLURAL = {"men", "women"}

def neutral(tok): return "people" if (tok in PLURAL or tok.endswith("s")) else "person"
def is_content(t): return t.isalpha() and len(t) >= 3 and t not in IDENT and t not in STOP

def iid(*p): return hashlib.md5("|".join(map(str, p)).encode()).hexdigest()[:12]

def variants(it):
    toks = it["text"].split(); low = [t.lower() for t in toks]
    idx = [i for i, t in enumerate(low) if t in IDENT]
    if not idx: return None
    rng = random.Random(int(hashlib.sha1(it["item_id"].encode()).hexdigest(), 16))
    cand = [i for i, t in enumerate(low) if is_content(t)]
    k = len(idx); plc = sorted(rng.sample(cand, k)) if len(cand) >= k else None
    repl = [neutral(low[i]) for i in idx]            # the multiset of neutral nouns NEU inserts
    neu = [neutral(t) if i in idx else t for i, t in zip(range(len(toks)), toks)]
    out = {"REPLAY": toks, "NEU": neu, "DEL": [t for i, t in enumerate(toks) if i not in idx]}
    if plc is not None:
        m = dict(zip(plc, repl)); out["PLC"] = [m.get(i, t) for i, t in enumerate(toks)]
        out["PLCDEL"] = [t for i, t in enumerate(toks) if i not in set(plc)]
    meta = {"identity_tokens": [low[i] for i in idx], "k": k, "placebo_tokens": [low[i] for i in plc] if plc else None}
    return out, meta

def main():
    os.makedirs(OUT, exist_ok=True)
    items = [json.loads(l) for l in open("items_llm600.jsonl")]
    rows, skipped = [], []
    for it in items:
        if it["mr"] != "E1" or not it.get("text"): continue
        v = variants(it)
        if v is None: continue
        texts, meta = v
        if "PLC" not in texts: skipped.append(it["item_id"]); continue
        for cond, tk in texts.items():
            rows.append({**{k: it[k] for k in ("source_id", "post_id", "axis", "relation", "policy", "policy_text", "label", "gold",
                                                "accept", "accept_lenient", "gold_evidence", "targets", "erased")},
                         "item_id": iid(it["item_id"], "E1CF", cond), "mr": "E1CF", "cf_condition": cond, "e1_item_id": it["item_id"],
                         "text": " ".join(tk), "tokens": tk, "cf_meta": meta})
    with open(f"{OUT}/items_e1cf.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    posts = {r["e1_item_id"] for r in rows}
    print(f"posts={len(posts)} items={len(rows)} skipped_no_placebo_candidates={len(skipped)}")
    json.dump({"posts": len(posts), "items": len(rows), "skipped_insufficient_content_tokens": skipped},
              open(f"{OUT}/build_summary.json", "w"), indent=1)

if __name__ == "__main__":
    main()
