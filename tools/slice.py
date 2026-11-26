"""Cut a slice of the master database for one addon and write it as Lua.

  python tools/slice.py slices/commandcenter.json dist/forever.json <addon folder>

Spec (slices/<name>.json):
  {
    "global": "ForeverDB",               Lua global the data lands in
    "files": "ForeverDB",                file name prefix (ForeverDB.lua, ForeverDB_2.lua, ...)
    "toc": "ForeverDB.toc",             optional: rewrite the file list + version in this toc
    "tables": ["npc", "drop", ...],      which master tables to include
    "prune": true,                       keep only npcs/objects/quests/items referenced by the other tables
    "fields": {"npc": [0, 1, 2, 3, 4]}   optional: which columns of a row to keep
    "max_rows": {"drop": 40}             optional: keep only the best N sources per item
  }
Flattening done for Lua: drop/odrop/idrop rows [[src, chance], ...] -> {src, chance, src, chance, ...}.
Big tables are written in chunks wrapped in functions (Lua's per-function constant limit),
and split over several files (MAX_FILE bytes each).
"""
import json, os, re, sys

CHUNK = 3000
CHUNK_BYTES = 400_000
MAX_FILE = 3_500_000


def lua_str(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
    return '"' + s + '"'


def lua(v):
    if v is None:
        return "nil"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int,)):
        return str(v)
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(round(v, 4))
    if isinstance(v, str):
        return lua_str(v)
    if isinstance(v, list):
        # trailing nils trimmed; inner nils kept positional
        while v and v[-1] is None:
            v = v[:-1]
        return "{" + ",".join(lua(x) for x in v) + "}"
    if isinstance(v, dict):
        parts = []
        for k in sorted(v, key=lambda k: (0, int(k)) if str(k).lstrip("-").isdigit() else (1, str(k))):
            ks = str(k)
            if ks.lstrip("-").isdigit():
                parts.append("[%s]=%s" % (ks, lua(v[k])))
            elif re.match(r"^[A-Za-z_]\w*$", ks):
                parts.append("%s=%s" % (ks, lua(v[k])))
            else:
                parts.append("[%s]=%s" % (lua_str(ks), lua(v[k])))
        return "{" + ",".join(parts) + "}"
    raise TypeError(type(v))


def referenced(db, tables):
    npcs, objs, quests, items = set(), set(), set(), set()
    for f in ("drop", "odrop", "idrop", "vend", "rew", "start", "world"):
        if f in tables:
            items.update(int(k) for k in db.get(f, {}))
    for f, bucket in (("drop", npcs), ("odrop", objs), ("idrop", items)):
        if f in tables:
            for rows in db.get(f, {}).values():
                bucket.update(r[0] for r in rows)
    if "vend" in tables:
        for rows in db.get("vend", {}).values():
            npcs.update(rows)
    for f in ("rew",):
        if f in tables:
            for rows in db.get(f, {}).values():
                quests.update(rows)
    if "start" in tables:
        quests.update(db.get("start", {}).values())
    if "qx" in tables:
        # questing data: every quest, the creatures / objects / items its objectives need
        quests.update(int(k) for k in db.get("qx", {}))
        quests.update(int(k) for k in db.get("qg", {}))
        for row in db.get("qx", {}).values():
            for col, bucket in ((7, npcs), (8, objs), (9, items), (20, items)):
                if len(row) > col and row[col]:
                    bucket.update(row[col])
            for ref in (row[22] if len(row) > 22 and row[22] else []):
                {"c": npcs, "o": objs, "i": items}.get(ref[0], set()).add(int(ref[1:]))
        for srcs in db.get("qsrc", {}).values():
            for ref in srcs:
                {"c": npcs, "o": objs}.get(ref[0], set()).add(int(ref[1:]))
    for f in ("qg", "qe"):
        if f in tables:
            for q, ws in db.get(f, {}).items():
                if int(q) in quests:
                    for w in ws:
                        (npcs if w[0] == "c" else objs).add(int(w[1:]))
    return npcs, objs, quests, items


KIND = {"drop": "c", "odrop": "o", "idrop": "i", "skin": "c"}


def capped(db, t, k, rows, n):
    """The best n rows, plus every row recorded in WoW Forever (db.seen): recorded data is never cut."""
    if len(rows) <= n or t not in KIND:
        return rows[:n]
    seen = db.get("seen") or {}
    def recorded(r):
        s = seen.get(KIND[t] + str(r[0])) if isinstance(r, list) and r else None
        return bool(s) and (str(k) in s or k in s)
    return rows[:n] + [r for r in rows[n:] if recorded(r)]


def make_slice(db, spec):
    tables = spec["tables"]
    out = {}
    keep = None
    caps = spec.get("max_rows", {})
    if caps:
        db = dict(db)
        for t, n in caps.items():
            if t in db:
                db[t] = {k: capped(db, t, k, v, n) for k, v in db[t].items()}
    if spec.get("prune"):
        npcs, objs, quests, items = referenced(db, tables)
        keep = {"npc": npcs, "obj": objs, "quest": quests, "qg": quests, "qe": quests, "item": items,
                "vp": npcs, "qx": quests, "nfac": npcs, "qsp": quests, "qsrc": quests, "qwk": quests}
    for t in tables:
        src = db.get(t, {})
        res = {}
        for k, v in src.items():
            ik = int(k) if str(k).lstrip("-").isdigit() else k
            if keep and t in keep and ik not in keep[t]:
                continue
            if keep and t in ("spw", "spm", "seen", "ind", "note", "ptl"):
                kind, num = str(k)[0], int(str(k)[1:])
                if (kind == "c" and num not in keep["npc"]) or (kind == "o" and num not in keep["obj"]):
                    continue
            if t in ("drop", "odrop", "idrop", "skin"):
                v = [x for pair in v for x in pair]      # already capped above (recorded rows kept)
            elif t in ("vend", "rew") and spec.get("max_rows", {}).get(t):
                v = v[:spec["max_rows"][t]]
            cols = spec.get("fields", {}).get(t)
            if cols and isinstance(v, list):
                v = [v[c] if c < len(v) else None for c in cols]
            res[ik] = v
        out[t] = res
    out["meta"] = dict(db.get("meta", {}))
    if spec.get("per_locale") and isinstance(out.get("loc"), dict):
        out["meta"]["languages"] = sorted(out["loc"])
        out["meta"]["locFallback"] = dict(LOC_FALLBACK)
    return out


# a language the game may run in -> the one ForeverDB falls back to for texts it doesn't have
LOC_FALLBACK = {"enGB": "enUS", "esMX": "esES", "ptPT": "ptBR"}


def write_lua(sl, spec, folder):
    g = spec["global"]
    prefix = spec.get("files", "Data")
    files, cur, size = [], [], 0

    def flush():
        nonlocal cur, size
        if cur:
            files.append(cur)
        cur, size = [], 0

    head = ["-- generated by forever-db (tools/slice.py) - do not edit",
            "%s = %s or {}" % (g, g), "local D = %s" % g]
    per_locale = spec.get("per_locale")
    if per_locale:
        # only the game's language (and the one it falls back to) is kept in memory; set ForeverDBLocaleAll = true
        # before loading to keep every language (tools)
        head += ["local L = GetLocale and GetLocale()",
                 "local W = { [L or \"\"] = true, [(%s)[L or \"\"] or \"\"] = true }" % lua(LOC_FALLBACK),
                 "if not L or ForeverDBLocaleAll then W = setmetatable({}, { __index = function() return true end }) end"]
    meta = sl.pop("meta", {})
    cur.append("D.meta = %s" % lua(meta)); size += 200
    items = []
    for t, rows in sl.items():
        if per_locale and t == "loc":
            # D.loc[lang][table] = rows, each language's chunks behind W[lang]
            for lang in sorted(rows):
                for sub in sorted(rows[lang]):
                    items.append(("loc[%s][%s]" % (lua_str(lang), lua_str(sub)), rows[lang][sub], lang))
        else:
            items.append((t, rows, None))
    for t, rows, lang in items:
        keys = sorted(rows, key=lambda k: (0, k) if isinstance(k, int) else (1, str(k)))
        def ensure():
            if lang is None:
                return ["D.%s = D.%s or {}" % (t, t)]
            ls = lua_str(lang)
            return ["D.loc = D.loc or {}",
                    "if W[%s] then D.loc[%s] = D.loc[%s] or {}; D.%s = D.%s or {} end" % (ls, ls, ls, t, t)]
        cur.extend(ensure())
        # one function per CHUNK rows or ~CHUNK_BYTES of text, whichever comes first: Lua 5.1 (the
        # game) allows about 262k constants per function, and big nested rows (map outlines) add up
        parts, part, psize = [], [], 0
        for k in keys:
            ks = "[%d]" % k if isinstance(k, int) else ("[%s]" % k if str(k).lstrip("-").isdigit() else "[%s]" % lua_str(k))
            line = "t%s=%s" % (ks, lua(rows[k]))
            if part and (len(part) >= CHUNK or psize + len(line) > CHUNK_BYTES):
                parts.append(part); part, psize = [], 0
            part.append(line); psize += len(line)
        if part:
            parts.append(part)
        for part in parts:
            guard = "" if lang is None else " if not W[%s] then return end" % lua_str(lang)
            text = "\n".join([";(function()%s local t = D.%s" % (guard, t)] + part + ["end)()"])
            if size + len(text) > MAX_FILE and size > 0:
                flush()
                cur.extend(ensure())
            cur.append(text); size += len(text)
    flush()
    names = []
    os.makedirs(folder, exist_ok=True)
    for i, chunk in enumerate(files):
        name = "%s.lua" % prefix if i == 0 else "%s_%d.lua" % (prefix, i + 1)
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(head + chunk) + "\n")
        names.append(name)
    # remove stale extra files
    for fn in os.listdir(folder):
        if re.match(re.escape(prefix) + r"_\d+\.lua$", fn) and fn not in names:
            os.remove(os.path.join(folder, fn))
    if spec.get("toc"):
        p = os.path.join(folder, spec["toc"])
        with open(p, encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.startswith("##") or not l.strip()]
        lines = [l for l in lines if l.strip()]
        lines = [("## Version: %s" % meta.get("build", "0")) if l.startswith("## Version:") else l for l in lines]
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n\n" + "\n".join(names) + "\n")
    return names


def main():
    spec_path, master, folder = sys.argv[1:4]
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    with open(master, encoding="utf-8") as f:
        db = json.load(f)
    sl = make_slice(db, spec)
    counts = {k: len(v) for k, v in sl.items() if isinstance(v, dict) and k != "meta"}
    names = write_lua(sl, spec, folder)
    total = sum(os.path.getsize(os.path.join(folder, n)) for n in names)
    print("slice", spec_path, "->", folder, names, "%.1f MB" % (total / 1e6), counts)


if __name__ == "__main__":
    main()
