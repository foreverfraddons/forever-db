"""Merge every source database into one base, cross-checking them against each other.

  python tools/merge.py --out work/base.json --report dist/report.json \
      questie=work/src-questie.json vmangos=work/src-vmangos.json \
      cmangos=work/src-cmangos.json pfquest=work/src-pfquest.json

Sources are listed in priority order (first = most trusted). A source named in FOREVER is
WoW Forever data and wins any field it has; for the rest each field is decided by a vote
(the value most sources agree on; a tie goes to the higher-priority source). Every entry any
source has is kept, so each source adds what the others are missing.

  npc / obj / item / quest   field-by-field vote (names, levels, rank, quality, ...)
  qg / qe / vend / rew       union
  start                      vote
  drop / odrop / idrop       union of sources; chance = median of the sources that give a rate
                             (0 = known to drop there, rate unknown)
  world                      lowest level any source gives
  spw                        world coordinates, union, near-duplicates dropped
  spz                        Forever map positions (uiMap, 0-1000), Forever source first
  loc                        translated names (union, first source per locale wins)
  src                        which sources have each npc/obj/item/quest: bit k = k-th source

The report lists per source how many entries it had, how many only it had, and every field
where sources disagreed (with examples), so the data can be checked.
"""
import argparse, json, os, statistics
from collections import Counter, defaultdict

FOREVER = {"client", "questie", "att", "recordings"}   # WoW Forever data: wins any field it has
ENTITY = ["npc", "obj", "item", "quest"]
UNION = ["qg", "qe", "vend", "rew"]
DROPS = ["drop", "odrop", "idrop"]
PASS = ["qx", "nfac", "dng", "ind",    # single-source detail tables: first source that has a key wins
        # Forever client tables (tools/import_client.py)
        "taxi", "umap", "umaa", "area", "ach", "ctree", "crit", "mtree", "hol", "sla", "ieff", "seff", "tset",
        "bpet", "ctun", "wmo",
        # LegacyForever and Shortest Path Forever data (tools/import_extra.py)
        "legacy", "lcrit", "explore", "spf",
        # zone and sub-zone borders from the Forever client's terrain (tools/import_terrain.py)
        "zbord", "abord", "agrid",
        "qrw", "ptl", "qwk",
        "qgreet"]                                                   # questgiver greetings (MaNGOS dumps)                                        # quest rewards (MaNGOS dumps): money, XP, choice / fixed items
FIELDS = {"npc": ["name", "sub", "minLv", "maxLv", "rank"], "obj": ["name"],
          "item": ["name", "quality", "reqLevel", "ilvl", "class", "subclass", "slot", "icon", "classes", "skill",
                   "skillRank", "races", "minFaction", "minRep"],
          "quest": ["title", "level", "minLevel"]}
SPAWN_CAP = 120
NEAR_WORLD = 8          # yards: world spawn points closer than this are one point
NEAR_MAP = 6            # 0-1000 map units
EXAMPLES = 25
RATE_GAP = 3.0          # rates differing more than this factor count as a disagreement


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {t: {(int(k) if isinstance(k, str) and k.lstrip("-").isdigit() else k): v for k, v in (d.get(t) or {}).items()}
            for t in d if isinstance(d.get(t), dict)}


def norm(v):
    if isinstance(v, str):
        return " ".join(v.split()).casefold()
    return v


def vote(cands):
    """cands: [(source_index, value)] in priority order -> (value, disagreement?)"""
    vals = [(i, v) for i, v in cands if v is not None and v != ""]
    if not vals:
        return None, False
    forever = [v for i, v in vals if NAMES[i] in FOREVER]
    distinct = {norm(v) for _, v in vals}
    if forever:
        return forever[0], len(distinct) > 1
    counts = Counter(norm(v) for _, v in vals)
    best = max(counts.values())
    for _, v in vals:                       # priority order breaks ties
        if counts[norm(v)] == best:
            return v, len(distinct) > 1
    return vals[0][1], False


def near_dupe(pts, x, y, d):
    for j in range(0, len(pts), 2):
        if abs(pts[j] - x) <= d and abs(pts[j + 1] - y) <= d:
            return True
    return False


def merge(sources):
    global NAMES
    NAMES = [n for n, _ in sources]
    data = [d for _, d in sources]
    out = {t: {} for t in ENTITY + UNION + DROPS + PASS + ["start", "world", "spw", "spz", "loc", "src", "qtext"]}
    rep = {"sources": {}, "conflicts": {}, "rates": {"compared": 0, "disagree": 0, "examples": []},
           "forever_only": {}, "added_by": {}}
    conflicts = defaultdict(lambda: {"count": 0, "examples": []})

    # ---------------- entities
    for t in ENTITY:
        ids = set()
        for d in data:
            ids |= set((d.get(t) or {}).keys())
        nf = len(FIELDS[t])
        only = Counter()
        forever_only = 0
        for e in sorted(ids):
            have = [(i, (d.get(t) or {}).get(e)) for i, d in enumerate(data)]
            have = [(i, r) for i, r in have if r is not None]
            mask = 0
            for i, _ in have:
                mask |= 1 << i
            out["src"].setdefault(t, {})[e] = mask
            if len(have) == 1:
                only[NAMES[have[0][0]]] += 1
                if NAMES[have[0][0]] in FOREVER:
                    forever_only += 1
            row = []
            for k in range(nf):
                val, dis = vote([(i, r[k] if k < len(r) else None) for i, r in have])
                row.append(val)
                if dis:
                    c = conflicts["%s.%s" % (t, FIELDS[t][k])]
                    c["count"] += 1
                    if len(c["examples"]) < EXAMPLES:
                        c["examples"].append({"id": e, "chosen": val,
                                              "values": {NAMES[i]: r[k] for i, r in have if k < len(r) and r[k] is not None}})
            out[t][e] = row
        for n in NAMES:
            rep["sources"].setdefault(n, {})[t] = len(data[NAMES.index(n)].get(t) or {})
            rep["added_by"].setdefault(n, {})[t] = only.get(n, 0)
        rep["forever_only"][t] = forever_only

    # ---------------- relations (union)
    for t in UNION:
        for d in data:
            for k, lst in (d.get(t) or {}).items():
                cur = out[t].setdefault(k, [])
                for v in lst:
                    if v not in cur:
                        cur.append(v)
    starts = defaultdict(list)
    for i, d in enumerate(data):
        for k, q in (d.get("start") or {}).items():
            starts[k].append((i, q))
    for k, c in starts.items():
        out["start"][k], dis = vote(c)
        if dis:
            cc = conflicts["start"]
            cc["count"] += 1
            if len(cc["examples"]) < EXAMPLES:
                cc["examples"].append({"id": k, "values": {NAMES[i]: q for i, q in c}})
    for d in data:
        for k, lv in (d.get("world") or {}).items():
            out["world"][k] = lv if k not in out["world"] else min(out["world"][k], lv)

    # ---------------- drops
    for t in DROPS:
        acc = defaultdict(lambda: defaultdict(list))
        for i, d in enumerate(data):
            for item, lst in (d.get(t) or {}).items():
                for src, ch in lst:
                    acc[item][src].append((i, ch))
        for item, by in acc.items():
            res = []
            for src, cs in by.items():
                rates = [ch for _, ch in cs if ch and ch > 0]
                if len(rates) >= 2:
                    rep["rates"]["compared"] += 1
                    if max(rates) > RATE_GAP * max(1, min(rates)):
                        rep["rates"]["disagree"] += 1
                        if len(rep["rates"]["examples"]) < EXAMPLES:
                            rep["rates"]["examples"].append({"table": t, "item": item, "source": src,
                                                             "values": {NAMES[i]: ch for i, ch in cs}})
                ch = int(statistics.median(rates)) if rates else 0
                res.append([src, ch])
            res.sort(key=lambda p: -p[1])
            out[t][item] = res

    # ---------------- spawns
    for d in data:
        for key, groups in (d.get("spw") or {}).items():
            cur = {g[0]: g[1:] for g in out["spw"].get(key, [])}
            total = sum(len(p) // 2 for p in cur.values())
            for g in groups:
                m, pts = g[0], cur.setdefault(g[0], [])
                for j in range(1, len(g) - 1, 2):
                    if total >= SPAWN_CAP:
                        break
                    if not near_dupe(pts, g[j], g[j + 1], NEAR_WORLD):
                        pts += [g[j], g[j + 1]]
                        total += 1
            out["spw"][key] = [[m] + p for m, p in sorted(cur.items(), key=lambda kv: -len(kv[1])) if p]
    for d in data:
        for key, maps in (d.get("spz") or {}).items():
            cur = out["spz"].setdefault(key, {})
            total = sum(len(p) // 2 for p in cur.values())
            for m, pts in maps.items():
                lst = cur.setdefault(str(m), [])
                for j in range(0, len(pts) - 1, 2):
                    if total >= SPAWN_CAP:
                        break
                    if not near_dupe(lst, pts[j], pts[j + 1], NEAR_MAP):
                        lst += [pts[j], pts[j + 1]]
                        total += 1
    # ---------------- detail tables (pass through)
    for t in PASS:
        for d in data:
            for k, v in (d.get(t) or {}).items():
                out[t].setdefault(k, v)
    # ---------------- quest dialog, field by field: Forever sources first (QuestieDB's Forever objective
    # lines), then the rest in priority order (MaNGOS details / progress / completion, pfQuest)
    order = [d for n, d in zip(NAMES, data) if n in FOREVER] + [d for n, d in zip(NAMES, data) if n not in FOREVER]
    for d in order:
        for k, v in (d.get("qtext") or {}).items():
            if isinstance(v, dict):
                e = out["qtext"].setdefault(k, {})
                for f, x in v.items():
                    e.setdefault(f, x)
    # ---------------- translations
    for d in data:
        for loc, tbls in (d.get("loc") or {}).items():
            L = out["loc"].setdefault(loc, {})
            for t, names in tbls.items():
                dst = L.setdefault(t, {})
                for k, v in names.items():
                    if isinstance(v, dict):         # quest dialog: field by field, like qtext
                        e = dst.setdefault(k, {})
                        for f, x in v.items():
                            e.setdefault(f, x)
                    else:
                        dst.setdefault(k, v)

    rep["conflicts"] = dict(sorted(conflicts.items(), key=lambda kv: -kv[1]["count"]))
    rep["merged"] = {t: len(v) for t, v in out.items() if t not in ("loc", "src")}
    rep["order"] = NAMES
    return out, rep


def report_md(rep):
    L = ["# ForeverDB merge report", "", "Sources in priority order: " + ", ".join(rep["order"]) +
         " (Forever sources win any field they have; otherwise the most common value wins).", "",
         "## Entries per source", "", "| Source | " + " | ".join(ENTITY) + " |", "|---" * (len(ENTITY) + 1) + "|"]
    for n in rep["order"]:
        L.append("| %s | %s |" % (n, " | ".join("%d (%d only here)" % (rep["sources"][n].get(t, 0), rep["added_by"][n].get(t, 0)) for t in ENTITY)))
    L += ["", "Merged: " + ", ".join("%s %d" % kv for kv in rep["merged"].items()), "",
          "Forever-only entries (only the Forever source has them): " + ", ".join("%s %d" % kv for kv in rep["forever_only"].items()), "",
          "## Disagreements", "", "| Field | Entries where sources disagree |", "|---|---|"]
    for f, c in rep["conflicts"].items():
        L.append("| %s | %d |" % (f, c["count"]))
    r = rep["rates"]
    L += ["", "Drop rates compared across 2+ sources: %d, differing more than %gx: %d" % (r["compared"], RATE_GAP, r["disagree"]), "",
          "## Examples", ""]
    for f, c in rep["conflicts"].items():
        L.append("**%s**" % f)
        for ex in c["examples"][:8]:
            L.append("- %s: %s -> chose %r" % (ex["id"], json.dumps(ex["values"], ensure_ascii=False), ex.get("chosen")))
        L.append("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    ap.add_argument("sources", nargs="+", help="name=path, highest priority first")
    a = ap.parse_args()
    srcs = []
    for s in a.sources:
        name, _, path = s.partition("=")
        if os.path.exists(path):
            srcs.append((name, load(path)))
        else:
            print("skipping missing source", name, path)
    out, rep = merge(srcs)
    print("merged:", rep["merged"])
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    if a.report:
        os.makedirs(os.path.dirname(a.report) or ".", exist_ok=True)
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=1, ensure_ascii=False, default=str)
        with open(os.path.splitext(a.report)[0] + ".md", "w", encoding="utf-8") as f:
            f.write(report_md(rep))


if __name__ == "__main__":
    main()
