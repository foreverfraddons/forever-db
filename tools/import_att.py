"""AllTheThings' WoW Forever database (MIT; run with tools/att/run.lua) -> source json for
tools/merge.py. ATT is hand-curated Forever data: quest givers, quest levels, positions on
Forever's maps (uiMap, 0-1000 like spz), quest rewards, vendors and drops (no drop rates: 0).

  python tools/import_att.py work/att.json work/src-att.json
"""
import json, os, sys


def vals(v):
    if isinstance(v, dict):
        return [v[k] for k in sorted(v, key=lambda k: int(k) if str(k).isdigit() else 0)]
    return v if isinstance(v, list) else []


def main():
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    out = {k: {} for k in ["npc", "obj", "item", "quest", "qg", "qe", "drop", "odrop", "idrop", "vend", "rew", "start",
                           "world", "spw", "spz", "loc", "nyi"]}
    for t in ("npc", "obj", "item"):
        for k, row in d.get(t, {}).items():
            out[t][int(k)] = [vals(row)[0] if vals(row) else None]
    for k, row in d.get("quest", {}).items():
        r = row if isinstance(row, dict) else {}
        out["quest"][int(k)] = [r.get("1"), None, r.get("3")]
    for t in ("qg", "qe", "vend", "rew"):
        for k, lst in d.get(t, {}).items():
            out[t][int(k)] = vals(lst)
    for t in ("drop", "odrop"):
        for k, lst in d.get(t, {}).items():
            out[t][int(k)] = [[s, 0] for s in vals(lst)]
    for k, q in d.get("start", {}).items():
        out["start"][int(k)] = q
    # never implemented in WoW Forever (not obtainable): {"i<item>" / "q<quest>": 1}
    for kind, pre in (("item", "i"), ("quest", "q")):
        for k in (d.get("nyi") or {}).get(kind, {}) or {}:
            out["nyi"][pre + str(k)] = 1
    for key, maps in d.get("spz", {}).items():
        out["spz"][key] = {ui: vals(p) for ui, p in maps.items()}
    print("att", {k: len(v) for k, v in out.items()}, "files", d.get("files"), "errors", d.get("errors"))
    os.makedirs(os.path.dirname(sys.argv[2]) or ".", exist_ok=True)
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
