#!/usr/bin/env python3
"""
Run LLM moderators on the MR items (OpenAI-compatible API: Ollama, vLLM, OpenAI, Groq...).

Subcommands
  paraphrase  fill I3 items: paraphrase the post with a helper model (different family),
              optional bidirectional equivalence judge
  run         query one system = model x prompt; resumable; stores raw output
  export      human-validation workbook (E1, E2, I1, I3 samples + ambiguous/control R2 cases)
  score       kappa / validity rate from the filled sheet -> invalid item list

Prompts
  direct   : policy + post -> verdict, quoted words, confidence
  evidence : quote the words that matter first, then decide only from the quotes

Examples (Ollama on your computer)
  python run_llm.py paraphrase --items items_llm600.jsonl --model llama3.1:8b --judge-model qwen2.5:7b \
      --base-url http://localhost:11434/v1
  python run_llm.py run --items items_llm600.jsonl --model qwen2.5:7b --prompt direct \
      --base-url http://localhost:11434/v1 --out runs/qwen7b_direct.jsonl
"""
import argparse, json, os, re, time, random, hashlib

V, NV, INS = "violating", "not_violating", "insufficient"

def call(prompt, model, base_url, key, temperature=0.0, retries=4, max_tokens=None):
    import requests
    body = {"model": model, "temperature": temperature, "seed": 42, "messages": [{"role": "user", "content": prompt}]}
    if max_tokens: body["max_tokens"] = max_tokens
    for k in range(retries):
        try:
            r = requests.post(base_url.rstrip("/") + "/chat/completions", json=body, timeout=300,
                              headers={"Authorization": f"Bearer {key}"} if key else {})
            r.raise_for_status(); return r.json()["choices"][0]["message"]["content"]
        except Exception:
            if k == retries - 1: raise
            time.sleep(2 ** k)

def jparse(t):
    m = re.search(r"\{.*\}", t or "", re.S)
    try: return json.loads(m.group(0)) if m else {}
    except Exception: return {}

def p_direct(it):
    return (f"You are a content moderator.\n{it['policy_text']}\n\n"
            "Decide whether the post violates the policy. Answer 'insufficient' if no policy is given or the post "
            "cannot be judged from its text. Quote the exact words from the post that your decision relies on.\n"
            "Return ONLY JSON: {\"verdict\": \"violating|not_violating|insufficient\", \"quotes\": [\"...\"], "
            "\"confidence\": 0.0-1.0}\n\nPOST: " + it["text"])

def p_evidence(it):
    return (f"You are a content moderator.\n{it['policy_text']}\n\n"
            "Step 1: copy the exact words from the post that are relevant to the policy (or none). "
            "Step 2: decide ONLY from those words and the policy. If no policy is given or the words do not settle "
            "the case, answer 'insufficient'.\n"
            "Return ONLY JSON: {\"quotes\": [\"...\"], \"verdict\": \"violating|not_violating|insufficient\", "
            "\"confidence\": 0.0-1.0}\n\nPOST: " + it["text"])

PROMPTS = {"direct": p_direct, "evidence": p_evidence}

REFUSAL_RE = re.compile(r"i (can'?t|cannot|can’t|won'?t|am unable to|'m unable to|am not able to|'m not able to)|cannot (assist|help|create|provide|fulfill)|can'?t (assist|help|fulfill)", re.I)

def parse(raw):
    o = jparse(raw)
    if not o and REFUSAL_RE.search(raw or ""):
        return {"verdict": "refused", "quotes": [], "confidence": None, "parse_ok": False, "refused": True}
    o = jparse(raw); v = str(o.get("verdict", "")).lower().strip().replace("-", "_").replace(" ", "_")
    v = {"violation": V, "violates": V, "non_violating": NV, "not_violation": NV, "insufficient_evidence": INS}.get(v, v)
    if v not in (V, NV, INS): v = INS
    try: c = max(0.0, min(1.0, float(o.get("confidence"))))
    except Exception: c = None
    return {"verdict": v, "quotes": [str(q) for q in o.get("quotes", []) if str(q).strip()], "confidence": c, "parse_ok": bool(o)}

def mock(it, prompt, profile):
    """Synthetic moderators with known defects (pipeline tests only; never report)."""
    rng = random.Random(int(hashlib.md5((it["item_id"] + profile + prompt).encode()).hexdigest(), 16) % 10**8)
    g = it["gold"]
    if profile == "policyblind" and it["axis"] == "R": g = V if it["label"] != "normal" else NV
    if profile == "evblind" and it["mr"] in ("E1", "E2"): g = V if it["label"] != "normal" else NV
    if profile == "stereotype" and it["mr"] == "I1" and rng.random() < .4: g = NV if g == V else V
    if rng.random() < .07: g = rng.choice([V, NV])
    q = (it["gold_evidence"][:3] if g == V else [])
    if profile == "evblind" and it["mr"] == "E1" and g == V: q = it.get("erased", [])[:2]
    return json.dumps({"verdict": g, "quotes": q, "confidence": round(rng.uniform(.5, 1), 2)})

def cmd_run(a):
    from concurrent.futures import ThreadPoolExecutor
    items = [json.loads(l) for l in open(a.items)]
    items = [i for i in items if i.get("text") and (not a.mrs or i["mr"] in a.mrs.split(","))]
    done = {json.loads(l)["item_id"] for l in open(a.out)} if os.path.exists(a.out) else set()
    key = os.environ.get(a.api_key_env, ""); system = f"{a.model}|{a.prompt}"
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    todo = [it for it in items if it["item_id"] not in done]
    def ask(it):
        if a.model.startswith("mock:"): return mock(it, a.prompt, a.model.split(":", 1)[1])
        return call(PROMPTS[a.prompt](it), a.model, a.base_url, key, a.temperature, max_tokens=a.max_tokens)
    with open(a.out, "a") as f, ThreadPoolExecutor(a.workers) as ex:
        for k, (it, raw) in enumerate(zip(todo, ex.map(ask, todo))):   # map keeps item order, so the file stays resumable
            f.write(json.dumps({"item_id": it["item_id"], "system": system, "model": a.model, "prompt": a.prompt,
                                **parse(raw), "raw": raw}) + "\n"); f.flush()
            if a.verbose and k % 50 == 0: print(k, len(todo), flush=True)
    print("saved", a.out)

PARA = ("You are helping build a test set for a hate-speech detection / content-moderation classifier. Test sets need "
        "meaning-preserving rewrites of real labelled posts, including offensive ones, to check whether the classifier is "
        "robust. This is a text-editing task on an existing research-corpus item; you are not endorsing it and the output "
        "is only used to evaluate a classifier.\n\nRewrite the post below with different wording but exactly the same "
        "meaning, tone and targets. Keep every insult, slur and group mention at the same intensity; do not soften, censor, "
        "add or remove anything. Return only the rewritten post, no comments.\n\nPOST: {t}")
REFUSAL = ("i can't", "i cannot", "i can’t", "i won't", "i'm sorry", "i am sorry", "i'm not able", "cannot fulfill",
           "can't fulfill", "as an ai", "here is the rewritten", "here's the rewritten")

CENSORED = re.compile(r"\[[^\]]{0,60}(slur|derogatory|racial|ethnic|expletive|profan|offensive|redact|censor|epithet|insult|term)[^\]]{0,60}\]|\*{2,}|\b\w\*+\w*\b", re.I)

def refused(orig, para):
    """Refusal, chat preamble, truncation, or censoring of slurs (violates 'do not soften')."""
    t = para.lower()
    return bool(CENSORED.search(para)) or not para.strip() or any(k in t for k in REFUSAL) or len(para) < 0.4 * len(orig)

EQUIV = ("Do posts A and B express the same meaning, tone and target group? Answer only JSON {{\"same\": true|false}}."
         "\nA: {a}\nB: {b}")

def cmd_paraphrase(a):
    items = [json.loads(l) for l in open(a.items)]; src = {i["item_id"]: i for i in items if i["mr"] == "ORIG"}
    key = os.environ.get(a.api_key_env, "")
    def save():  # atomic: a crash never leaves a half-written items file
        with open(a.items + ".tmp", "w") as f:
            for it in items: f.write(json.dumps(it) + "\n")
        os.replace(a.items + ".tmp", a.items)
    # two phases so Ollama loads each model once: (1) paraphrase everything, (2) judge everything; both resumable
    todo = [it for it in items if it.get("pending_paraphrase")]
    for k, it in enumerate(todo):
        o = src[it["source_id"]]["text"]
        p = o if a.model == "mock" else call(PARA.format(t=o), a.model, a.base_url, key, 0.3).strip()
        if a.model != "mock" and refused(o, p):   # keep the failure visible: no text -> not run, not exported, counted as unusable
            it.update(text=None, tokens=[], pending_paraphrase=False, pending_judge=False, refused=True, auto_valid=False, raw_paraphrase=p[:200])
        else:
            it.update(text=p, tokens=p.split(), pending_paraphrase=False, pending_judge=bool(a.judge_model))
        if (k + 1) % 25 == 0: save(); print(f"paraphrased {k + 1}/{len(todo)}", flush=True)
    save(); print("paraphrased", len(todo), "refused:", sum(bool(i.get("refused")) for i in items), flush=True)
    todo = [it for it in items if it.get("pending_judge")]
    for k, it in enumerate(todo):
        o, p = src[it["source_id"]]["text"], it["text"]
        if a.model != "mock" and refused(o, p):
            it.update(text=None, tokens=[], pending_judge=False, refused=True, auto_valid=False, raw_paraphrase=p[:200]); continue
        if a.judge_model == "mock": it["auto_valid"] = True
        else:
            j1 = jparse(call(EQUIV.format(a=o, b=p), a.judge_model, a.base_url, key)).get("same")
            j2 = jparse(call(EQUIV.format(a=p, b=o), a.judge_model, a.base_url, key)).get("same")
            it["auto_valid"] = bool(j1) and bool(j2)
        it["pending_judge"] = False
        if (k + 1) % 25 == 0: save(); print(f"judged {k + 1}/{len(todo)}", flush=True)
    save(); print("judged", len(todo))

def _r2_groups(items, data_path):
    """R2 items from 'offensive' posts: AMBIGUOUS = at least one annotator said hatespeech (reference label
    'not violating' under the narrowed policy is contestable); CONTROL = the rest."""
    r2 = [i for i in items if i["mr"] == "R2" and i["label"] == "offensive" and i.get("text")]
    if not os.path.exists(data_path):
        print(f"warning: {data_path} not found; cannot tell ambiguous R2 cases, treating all as control"); return [], r2
    d = json.load(open(data_path))
    amb = lambda i: any(x["label"] == "hatespeech" for x in d[i["post_id"]]["annotators"])
    return [i for i in r2 if amb(i)], [i for i in r2 if not amb(i)]

def cmd_export(a):
    import hitl_sheet
    rng = random.Random(42); items = [json.loads(l) for l in open(a.items)]; src = {i["item_id"]: i for i in items if i["mr"] == "ORIG"}
    rows, groups = [], {}
    def add(it, mr, **extra):
        rows.append({"item_id": it["item_id"], "mr": mr, "original": src[it["source_id"]]["text"], "transformed": it["text"],
                     **{k: it[k] for k in ("erased", "swapped", "auto_valid") if k in it}, **extra})
    for mr in ("E1", "E2", "I1", "I3"):
        pool = [i for i in items if i["mr"] == mr and i.get("text")]
        if not pool: print(f"warning: no {mr} items with text (run 'paraphrase' first for I3)")
        for it in rng.sample(pool, max(1, round(a.frac * len(pool)))) if pool else []: add(it, mr)
    amb, ctl = _r2_groups(items, a.data)
    ctl = rng.sample(ctl, min(len(ctl), max(1, round(a.frac * len(ctl))))) if ctl else []
    for grp, pool in (("ambiguous", amb), ("control", ctl)):
        for it in pool:
            add(it, "R2", original=it["text"], transformed=it["policy_text"],
                change="Postingan TIDAK diubah; kebijakan dipersempit. Label acuan: TIDAK melanggar.")
            groups[it["item_id"]] = grp
    order = {m: k for k, m in enumerate(("E1", "E2", "R2", "I1", "I3"))}
    rows.sort(key=lambda r: order[r["mr"]])   # sort is stable: within an MR the sampling order is kept
    hitl_sheet.build(rows, a.out, next(i["policy_text"] for i in items if i["policy"] == "original"))
    json.dump(groups, open(os.path.splitext(a.out)[0] + "_r2_groups.json", "w"), indent=1)
    print("wrote", a.out, len(rows), {m: sum(r["mr"] == m for r in rows) for m in order}, "R2 ambiguous/control:", len(amb), len(ctl))

def cmd_score(a):
    import pandas as pd, hitl_sheet
    if hitl_sheet.is_hitl(a.sheet):  # workbook from 'export' (rater sheets + adjudication sheet)
        rows = hitl_sheet.read(a.sheet); df = pd.DataFrame(rows)
        r1, r2 = [r["r1"] for r in rows], [r["r2"] for r in rows]
        cons = [x if x is not None and x == y else (r["adj"] if x is not None and y is not None else None)
                for x, y, r in zip(r1, r2, rows)]
    else:  # legacy flat sheet: rater1(1/0), rater2(1/0), notes with ADJ=1/0
        df = pd.read_excel(a.sheet); r1 = [None if pd.isna(x) else int(x) for x in df["rater1(1/0)"]]
        r2 = [None if pd.isna(x) else int(x) for x in df["rater2(1/0)"]]
        cons = []
        for x, y, n in zip(r1, r2, df["notes"]):
            m = re.search(r"ADJ=([01])", str(n)); cons.append(x if x == y else (int(m.group(1)) if m else None))
    pairs = [(x, y) for x, y in zip(r1, r2) if x is not None and y is not None]; n = len(pairs)
    po = sum(x == y for x, y in pairs) / n if n else None
    pe = ((sum(x for x, _ in pairs) / n) * (sum(y for _, y in pairs) / n) + (1 - sum(x for x, _ in pairs) / n) * (1 - sum(y for _, y in pairs) / n)) if n else None
    kappa = round((po - pe) / (1 - pe), 4) if n and pe < 1 else None
    out = {"n": len(df), "kappa": kappa, "pct_agree": round(po, 4) if po is not None else None,
           "validity_by_mr": {m: round(sum(c == 1 for c, mm in zip(cons, df["mr"]) if mm == m) / max(1, sum(mm == m and c is not None for c, mm in zip(cons, df["mr"]))), 4) for m in sorted(set(df["mr"]))},
           "invalid_items": sorted({i for i, c in zip(df["item_id"], cons) if c == 0})}
    json.dump(out, open(a.out, "w"), indent=1); print(json.dumps({k: v for k, v in out.items() if k != "invalid_items"}))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); sp = ap.add_subparsers(dest="cmd", required=True)
    def common(s):
        s.add_argument("--items", required=True); s.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"))
        s.add_argument("--api-key-env", default="OPENAI_API_KEY")
    s = sp.add_parser("run"); common(s); s.add_argument("--model", required=True); s.add_argument("--prompt", choices=PROMPTS, required=True)
    s.add_argument("--temperature", type=float, default=0.0); s.add_argument("--mrs"); s.add_argument("--out", required=True)
    s.add_argument("--workers", type=int, default=1); s.add_argument("--max-tokens", type=int, default=256)
    s.add_argument("--verbose", action="store_true"); s.set_defaults(f=cmd_run)
    s = sp.add_parser("paraphrase"); common(s); s.add_argument("--model", required=True); s.add_argument("--judge-model"); s.set_defaults(f=cmd_paraphrase)
    s = sp.add_parser("export"); s.add_argument("--items", required=True); s.add_argument("--frac", type=float, default=0.2)
    s.add_argument("--data", default="data/dataset.json"); s.add_argument("--out", default="human_validation.xlsx"); s.set_defaults(f=cmd_export)
    s = sp.add_parser("score"); s.add_argument("--sheet", required=True); s.add_argument("--out", default="validation.json"); s.set_defaults(f=cmd_score)
    a = ap.parse_args(); a.f(a)

if __name__ == "__main__":
    main()
