#!/usr/bin/env python3
"""
Build the E1-CF v2 items (protocol: results/e1_counterfactual_v2/PROTOCOL.md, section 0 fixes every rule used here).

  python build_e1cf_v2.py   -> results/e1_counterfactual_v2/items_e1cf_v2.jsonl, swap_mapping.csv, build_summary.json
No model is called. Reads items_llm600.jsonl and the v1 items (REPLAY/NEU/PLC texts are reused unchanged, so v1 and v2 differ
only in the new SWAP and SWAP2 conditions).

SWAP: every identity token of group A in a post becomes a form of a group B with the same number and part of speech
(table FORMS, all forms are members of build_items.GROUP_TERMS so identity detection stays consistent).
"""
import csv, hashlib, importlib.util, json, os, random
from collections import Counter

OUT = "results/e1_counterfactual_v2"
spec = importlib.util.spec_from_file_location("bi", "build_items.py"); bi = importlib.util.module_from_spec(spec); spec.loader.exec_module(bi)
GROUP_OF = {t: g for g, ts in bi.GROUP_TERMS.items() for t in ts}

# class of every identity token: SG singular noun, PL plural noun, ADJ adjective (also used for tokens that are both noun and adjective),
# REL name of a religion. Fixed in PROTOCOL.md section 0.
TOKEN_CLASS = {
    "african": "ADJ", "black": "ADJ", "white": "ADJ", "islamic": "ADJ", "jewish": "ADJ", "asian": "ADJ", "chinese": "ADJ",
    "mexican": "ADJ", "hispanic": "ADJ", "gay": "ADJ", "homosexual": "ADJ",
    "muslim": "SG", "jew": "SG", "christian": "SG", "hindu": "SG", "arab": "SG", "woman": "SG", "man": "SG", "lesbian": "SG",
    "refugee": "SG", "immigrant": "SG",
    "africans": "PL", "blacks": "PL", "whites": "PL", "muslims": "PL", "jews": "PL", "christians": "PL", "hindus": "PL", "arabs": "PL",
    "hispanics": "PL", "mexicans": "PL", "asians": "PL", "women": "PL", "men": "PL", "gays": "PL", "homosexuals": "PL",
    "lesbians": "PL", "immigrants": "PL", "refugees": "PL",
    "islam": "REL", "christianity": "REL",
}
# one form per (group, class); a missing class means the group cannot replace a token of that class
FORMS = {
    "African": {"SG": "african", "PL": "africans", "ADJ": "black"},
    "Caucasian": {"SG": "white", "PL": "whites", "ADJ": "white"},
    "Asian": {"SG": "asian", "PL": "asians", "ADJ": "asian"},
    "Arab": {"SG": "arab", "PL": "arabs", "ADJ": "arab"},
    "Hispanic": {"SG": "hispanic", "PL": "hispanics", "ADJ": "hispanic"},
    "Islam": {"SG": "muslim", "PL": "muslims", "ADJ": "islamic", "REL": "islam"},
    "Jewish": {"SG": "jew", "PL": "jews", "ADJ": "jewish"},
    "Christian": {"SG": "christian", "PL": "christians", "ADJ": "christian", "REL": "christianity"},
    "Hindu": {"SG": "hindu", "PL": "hindus", "ADJ": "hindu"},
    "Women": {"SG": "woman", "PL": "women"},
    "Men": {"SG": "man", "PL": "men"},
    "Homosexual": {"SG": "homosexual", "PL": "homosexuals", "ADJ": "gay"},
    "Refugee": {"SG": "refugee", "PL": "refugees", "ADJ": "immigrant"},
}
SAME_TYPE = {"race": ["African", "Caucasian", "Asian", "Arab", "Hispanic"], "religion": ["Islam", "Jewish", "Christian", "Hindu"], "gender": ["Women", "Men"]}
TYPE_OF = {g: t for t, gs in SAME_TYPE.items() for g in gs}   # Homosexual and Refugee have no same-type partner: cross-type pool

def iid(*p): return hashlib.md5("|".join(map(str, p)).encode()).hexdigest()[:12]
def rng_for(item_id, tag): return random.Random(int(hashlib.sha1((item_id + tag).encode()).hexdigest(), 16))

def recase(src, new):
    return new.upper() if src.isupper() and len(src) > 1 else (new.capitalize() if src[:1].isupper() else new)

def choose(item_id, tag, groups_in_post, tokens_by_group, taken):
    """-> {A: B} or None. Per A, the pool is same-type groups (or all other groups for Homosexual/Refugee) that have a form for every
    class of A's tokens in this post; B is not any A of the post, and B's are distinct. Draws are in sorted(A) order."""
    rng, out = rng_for(item_id, tag), {}
    used = set(groups_in_post) | set(taken)
    for a in sorted(groups_in_post):
        need = {TOKEN_CLASS[t] for t in tokens_by_group[a]}
        pool = SAME_TYPE[TYPE_OF[a]] if a in TYPE_OF else sorted(FORMS)
        elig = sorted(b for b in pool if b not in used and need <= set(FORMS[b]))
        if not elig: return None
        out[a] = rng.choice(elig); used.add(out[a])
    return out

def swap_tokens(toks, mapping):
    res = []
    for t in toks:
        low = t.lower(); g = GROUP_OF.get(low)
        res.append(recase(t, FORMS[mapping[g]][TOKEN_CLASS[low]]) if g in mapping else t)
    return res

def main():
    os.makedirs(OUT, exist_ok=True)
    v1 = [json.loads(l) for l in open("results/e1_counterfactual/items_e1cf.jsonl")]
    by_post = {}
    for r in v1: by_post.setdefault(r["e1_item_id"], {})[r["cf_condition"]] = r
    rows, maprows, strata = [], [], Counter(); no_b = []
    for e1_id in sorted(by_post):
        conds = by_post[e1_id]; base = conds["REPLAY"]; toks = base["tokens"] if isinstance(base["tokens"], list) else json.loads(base["tokens"])
        tokens_by_group = {}
        for t in toks:
            g = GROUP_OF.get(t.lower())
            if g: tokens_by_group.setdefault(g, set()).add(t.lower())
        groups = sorted(tokens_by_group)
        m1 = choose(e1_id, "swap", groups, tokens_by_group, [])
        m2 = choose(e1_id, "swap2", groups, tokens_by_group, list(m1.values()) if m1 else [])
        stratum = "cross_type" if any(g not in TYPE_OF for g in groups) else ("multi_group" if len(groups) > 1 else "same_type")
        strata[stratum] += 1
        for cond in ("REPLAY", "NEU", "PLC"):
            if cond in conds:
                r = dict(conds[cond]); r["item_id"] = iid("E1CFv2", e1_id, cond); r["mr"] = "E1CFv2"; rows.append(r)
        for cond, m in (("SWAP", m1), ("SWAP2", m2)):
            if m is None:
                if cond == "SWAP": no_b.append(e1_id)
                continue
            tk = swap_tokens(toks, m)
            r = {k: base[k] for k in base if k not in ("item_id", "mr", "cf_condition", "text", "tokens", "cf_meta")}
            r.update({"item_id": iid("E1CFv2", e1_id, cond), "mr": "E1CFv2", "cf_condition": cond, "e1_item_id": e1_id, "text": " ".join(tk), "tokens": tk,
                      "cf_meta": {"swap_A_to_B": m, "stratum": stratum, "identity_tokens": sorted(t for ts in tokens_by_group.values() for t in ts)}})
            rows.append(r)
            maprows.append({"e1_item_id": e1_id, "condition": cond, "stratum": stratum, "A_to_B": json.dumps(m), "REPLAY_text": " ".join(toks), "SWAP_text": " ".join(tk)})
    with open(f"{OUT}/items_e1cf_v2.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    with open(f"{OUT}/swap_mapping.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(maprows[0])); w.writeheader(); w.writerows(maprows)
    sha = hashlib.sha1(open(f"{OUT}/items_e1cf_v2.jsonl", "rb").read()).hexdigest()
    summ = {"posts": len(by_post), "items": len(rows), "by_condition": dict(Counter(r["cf_condition"] for r in rows)), "strata": dict(strata),
            "posts_without_eligible_B_for_SWAP": no_b, "items_sha1": sha}
    json.dump(summ, open(f"{OUT}/build_summary.json", "w"), indent=1); print(json.dumps(summ))

if __name__ == "__main__":
    main()
