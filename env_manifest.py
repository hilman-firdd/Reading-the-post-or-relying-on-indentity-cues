#!/usr/bin/env python3
"""
env_manifest.py — record the run environment next to the outputs (reviewer item: OS, runtime, digests, dependencies).

  python env_manifest.py --out runs_repeat/rep2/manifest.json [--note "rep 2, uniform setting"]

Records only what can be read from this machine; anything that cannot be read is written as null with the reason.
Ollama server settings (OLLAMA_NUM_PARALLEL, OLLAMA_CONTEXT_LENGTH) belong to the *server* process. They are taken
from the environment of this shell, which is correct only when the server was started from it (as run_repeats.sh
asks); the value is therefore labelled "client_shell_env".
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request

BASE = os.environ.get("OLLAMA_HOST_URL", "http://localhost:11434")


def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip() or None
    except Exception as e:  # noqa: BLE001
        return f"unavailable: {type(e).__name__}"


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        return {"unavailable": f"{type(e).__name__}: {e}"}


def sha1(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def pkg_versions(names):
    out = {}
    for n in names:
        try:
            from importlib.metadata import version
            out[n] = version(n)
        except Exception:  # noqa: BLE001
            out[n] = None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    tags = get("/api/tags")
    models = [{"name": m.get("name"), "digest": (m.get("digest") or "")[:12], "size": m.get("size"),
               "quantization": (m.get("details") or {}).get("quantization_level"),
               "parameter_size": (m.get("details") or {}).get("parameter_size")}
              for m in tags.get("models", [])] if isinstance(tags, dict) and "models" in tags else tags
    man = {
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": a.note,
        "os": {"sw_vers": sh(["sw_vers"]), "uname": " ".join(x for i, x in enumerate(platform.uname()) if i != 1), "cpu": sh(["sysctl", "-n", "machdep.cpu.brand_string"]),
               "memory_bytes": sh(["sysctl", "-n", "hw.memsize"])},
        "ollama": {"cli_version": sh(["ollama", "--version"]), "server_version": get("/api/version"), "models": models,
                   "loaded_models_api_ps": get("/api/ps"),
                   "client_shell_env": {k: v for k, v in os.environ.items() if k.startswith("OLLAMA_")}},
        "python": {"version": sys.version, "executable": sys.executable.replace(os.path.expanduser("~"), "~"),
                   "packages": pkg_versions(["numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "openpyxl", "requests"])},
        "kit": {"git_head": sh(["git", "rev-parse", "HEAD"]), "git_dirty": bool(sh(["git", "status", "--porcelain"])),
                "sha1": {p: sha1(p) for p in ("items_llm600.jsonl", "results/e1_counterfactual/items_e1cf.jsonl",
                                              "run_llm.py", "data/dataset.json", "data/post_id_divisions.json")}},
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(man, f, indent=1)
    print("manifest:", a.out)


if __name__ == "__main__":
    main()
