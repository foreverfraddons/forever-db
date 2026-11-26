"""Turn the JSON written by tools/lua/export.lua (pfQuest, QuestieDB) into the source format
that tools/merge.py reads (same tables as import_base.py, plus spz and loc).

  python tools/import_addons.py pfquest  work/pfquest.json  work/src-pfquest.json  [--zones work/questie-forever.json]
  python tools/import_addons.py questie  work/questie-forever.json  work/src-questie.json

Extra tables:
  spz  {"c123": {uiMap: [x, y, x, y, ...]}}   map positions 0-1000 on Forever's maps
  loc  {locale: {"npc"|"obj"|"item"|"quest": {id: name}}}
Drops known without a rate (QuestieDB) get chance 0 = "drops here, rate unknown".

Map positions: pfQuest stores Classic zone percentages; QuestieDB stores Forever ones.
Zones are AreaTable ids, mapped to uiMap ids with QuestieDB's Forever zone tables, and Classic
positions are moved onto Forever's maps with QuestieDB's per-zone conversion factors (Forever
redrew a few zone maps, e.g. Mulgore).
"""
import json, os, re, sys

SPAWN_CAP = 120


def obj_list(v):
    """{'1': a, '2': b} -> [a, b] (sorted by numeric key); lists pass through."""
    if isinstance(v, list):
        return v
    if not isinstance(v, dict):
        return [] if v is None else [v]
    try:
        return [v[k] for k in sorted(v, key=lambda k: float(k))]
    except ValueError:
        return list(v.values())


def ints(v):
    out = []
    for x in obj_list(v):
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            pass
    return out


def field(rec, keys, name):
    k = keys.get(name)
    return rec.get(str(k)) if k is not None else None


def num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None


# ------------------------------------------------------------------ zones
def zone_tables(qjson_path, conversion_path=None):
    """area id -> uiMap id, and area id -> (scale_x, off_x, scale_y, off_y) Classic->Forever."""
    a2u, coef = {}, {}
    if qjson_path and os.path.exists(qjson_path):
        q = json.load(open(qjson_path, encoding="utf-8"))
        for src in ("classicUiMapToArea", "uiMapToArea"):
            for u, a in (q.get(src) or {}).items():
                if num(a) and num(u):
                    a2u.setdefault(num(a), num(u))
        for src in ("classicAreaToUiMap", "areaToUiMap"):
            for a, u in (q.get(src) or {}).items():
                if num(u):
                    a2u[num(a)] = num(u)
    zone_ids = {}
    if qjson_path and os.path.exists(qjson_path):
        zone_ids = {k: num(v) for k, v in (q.get("zoneIDs") or {}).items() if num(v)}
    if conversion_path and os.path.exists(conversion_path):
        g = json.load(open(conversion_path, encoding="utf-8")).get("geometry", {})
        for t in g.get("transforms", []):
            if t.get("area_id") and t.get("ui_map_id"):
                a2u[int(t["area_id"])] = int(t["ui_map_id"])
        # maps Forever added (Zephras Isle, Riverglades, ...) carry only a name: match it to
        # QuestieDB's zone symbols (ZEPHRAS_ISLE = 16593 ...); the first map of a name wins
        for m in g.get("added_maps", []):
            sym = re.sub(r"[^A-Z0-9]+", "_", (m.get("target_name") or "").upper().replace("'", "")).strip("_")
            area = zone_ids.get(sym)
            if area and m.get("ui_map_id") and area not in a2u:
                a2u[area] = int(m["ui_map_id"])
        for a, c in (g.get("area_coefficients") or {}).items():
            coef[int(a)] = (c["scale_x"], c["offset_x"], c["scale_y"], c["offset_y"])
    a2u = {a: u for a, u in a2u.items() if u}
    return a2u, coef


def add_spots(spz, key, ui, x, y):
    if x is None or y is None or ui is None:
        return
    x, y = int(round(float(x) * 10)), int(round(float(y) * 10))
    if not (0 <= x <= 1000 and 0 <= y <= 1000):
        return
    m = spz.setdefault(key, {})
    pts = m.setdefault(ui, [])
    if sum(len(p) for p in m.values()) // 2 >= SPAWN_CAP:
        return
    for j in range(0, len(pts), 2):
        if abs(pts[j] - x) <= 5 and abs(pts[j + 1] - y) <= 5:
            return
    pts += [x, y]


def empty():
    return {k: {} for k in ["npc", "obj", "item", "quest", "qg", "qe", "drop", "odrop", "idrop",
                            "vend", "rew", "start", "world", "spw", "spz", "loc", "qx", "nfac", "dng", "ind", "qtext"]}


def qtext_entry(d, o):
    """{"d": details, "o": objectives} without empty fields (quest dialog)"""
    e = {}
    if isinstance(d, str) and d.strip():
        e["d"] = d
    if isinstance(o, str) and o.strip():
        e["o"] = o
    return e


def push(d, k, v):
    lst = d.setdefault(k, [])
    if v not in lst:
        lst.append(v)


# ------------------------------------------------------------------ pfQuest
def pfquest(p, a2u, coef):
    out, unmapped = empty(), set()
    names = p.get("names", {})
    en = names.get("enUS", {})
    units, objs = en.get("units") or {}, en.get("objects") or {}
    items, quests = en.get("items") or {}, en.get("quests") or {}

    def lvl(s):
        if s is None:
            return None, None
        parts = str(s).replace(" ", "").split("-")
        a, b = num(parts[0]), num(parts[-1])
        return a, b

    def spots(kind, sid, coords):
        for c in obj_list(coords):
            c = obj_list(c)
            if len(c) < 3:
                continue
            x, y, area = c[0], c[1], num(c[2])
            ui = a2u.get(area)
            if ui is None:
                unmapped.add(area)
                continue
            if area in coef:
                sx, ox, sy, oy = coef[area]
                x, y = float(x) * sx + ox, float(y) * sy + oy
            add_spots(out["spz"], "%s%d" % (kind, sid), ui, x, y)

    for sid, u in p.get("units", {}).items():
        sid = int(sid)
        mn, mx = lvl(u.get("lvl"))
        out["npc"][sid] = [units.get(str(sid)), None, mn, mx, None]
        spots("c", sid, u.get("coords"))
    for sid, o in p.get("objects", {}).items():
        sid = int(sid)
        out["obj"][sid] = [objs.get(str(sid))]
        spots("o", sid, o.get("coords"))
    for iid, nm in items.items():
        out["item"][int(iid)] = [nm, None, None]
    refloot = p.get("refloot", {})
    for iid, it in p.get("items", {}).items():
        iid = int(iid)
        out["item"].setdefault(iid, [items.get(str(iid)), None, None])
        for src, f in (("U", "drop"), ("O", "odrop"), ("I", "idrop")):
            for sid, ch in (it.get(src) or {}).items():
                out[f].setdefault(iid, []).append([int(sid), int(round(float(ch or 0) * 100))])
        for rid, ch in (it.get("R") or {}).items():          # reference loot -> its users
            ref = refloot.get(str(rid)) or {}
            for src, f in (("U", "drop"), ("O", "odrop")):
                for sid, _ in (ref.get(src) or {}).items():
                    out[f].setdefault(iid, []).append([int(sid), int(round(float(ch or 0) * 100))])
        for sid in (it.get("V") or {}):
            push(out["vend"], iid, int(sid))
    for qid, q in p.get("quests", {}).items():
        qid = int(qid)
        out["quest"][qid] = [quests.get(str(qid)), num(q.get("lvl")), num(q.get("min"))]
        for part, dst in (("start", "qg"), ("end", "qe")):
            rel = q.get(part) or {}
            for kind, pre in (("U", "c"), ("O", "o")):
                for sid in ints(rel.get(kind)):
                    push(out[dst], qid, pre + str(sid))
            if part == "start":
                for it in ints(rel.get("I")):
                    out["start"][it] = qid
    for f in ("drop", "odrop", "idrop"):
        for iid, lst in out[f].items():
            best = {}
            for sid, ch in lst:
                best[sid] = max(best.get(sid, 0), ch)
            out[f][iid] = sorted(([s, c] for s, c in best.items()), key=lambda e: -e[1])
    kinds = {"units": "npc", "objects": "obj", "items": "item", "quests": "quest"}
    for loc, tbls in names.items():
        for src, dst in kinds.items():
            t = tbls.get(src) or {}
            if t:
                out["loc"].setdefault(loc, {})[dst] = {int(k): v for k, v in t.items() if isinstance(v, str)}
        # quest dialog (details, objectives): English in qtext, the other languages in loc[lang].qtext
        qt = {}
        for k, v in (tbls.get("qtext") or {}).items():
            e = qtext_entry(v.get("d"), v.get("o")) if isinstance(v, dict) else {}
            if e:
                qt[int(k)] = e
        if qt:
            if loc == "enUS":
                out["qtext"] = qt
            else:
                out["loc"].setdefault(loc, {})["qtext"] = qt
    return out, unmapped


def first_ints(v):
    """[[id, text, ...], ...] -> [id, ...] (QuestieDB objective lists)."""
    out = []
    for e in obj_list(v):
        e = obj_list(e)
        if e:
            if isinstance(e[0], (dict, list)):      # killCredit: {{ids}, baseId, text}
                out += ints(e[0])
                if len(e) > 1 and num(e[1]):
                    out.append(num(e[1]))
            elif num(e[0]) is not None:
                out.append(num(e[0]))
    return sorted(set(out))


def quest_extra(r, qk, a2u):
    """Quest details for questing addons (table qx, one row per quest; Lua index = position + 1):
    1 races mask, 2 classes mask, 3 preQuestSingle, 4 preQuestGroup, 5 exclusiveTo,
    6 breadcrumbFor, 7 nextInChain, 8 kill/creature objectives, 9 object objectives,
    10 item objectives, 11 zoneOrSort, 12 questFlags, 13 specialFlags, 14 requiredSkill [id, value],
    15 reputation rewards [faction, value, ...], 16 exploration spots {uiMap: [x, y, ...]} (0-1000),
    17 parentQuest, 18 sourceItem, 19 requiredMinRep [faction, value], 20 breadcrumbs (quests that lead here),
    21 requiredSourceItems (items you need to make the objective, e.g. bundles you craft into it),
    22 extra objective spots {uiMap: [x, y, ...]}, 23 extra objective targets ["c123", "o45", ...]"""
    o = field(r, qk, "objectives")
    if isinstance(o, dict):         # sparse Lua list: keep the positions (1 creatures, 2 objects, 3 items, ...)
        o = [o.get(str(i)) for i in range(1, 7)]
    o = ((o if isinstance(o, list) else []) + [None] * 6)[:6]
    creatures = first_ints(o[0]) + first_ints(o[4])
    rep = []
    for e in obj_list(field(r, qk, "reputationReward")):
        e = obj_list(e)
        if len(e) >= 2 and num(e[0]) is not None:
            rep += [num(e[0]), num(e[1])]
    trig = {}
    te = obj_list(field(r, qk, "triggerEnd"))
    if len(te) >= 2 and isinstance(te[1], dict):
        for area, pts in te[1].items():
            ui = a2u.get(num(area))
            if ui is None:
                continue
            for pt in obj_list(pts):
                pt = obj_list(pt)
                if len(pt) >= 2:
                    x, y = int(round(float(pt[0]) * 10)), int(round(float(pt[1]) * 10))
                    if 0 <= x <= 1000 and 0 <= y <= 1000:
                        trig.setdefault(str(ui), []).extend([x, y])
    # hidden / special objectives (use the cannon, burn the hut ...): spots + the npcs / objects involved
    extra, refs = {}, []
    for eo in obj_list(field(r, qk, "extraObjectives")):
        if isinstance(eo, dict):     # sparse: keep positions (1 spawnlist, 2 icon, 3 text, 4 index, 5 refs)
            eo = [eo.get(str(i)) for i in range(1, 6)]
        if not isinstance(eo, list) or not eo:
            continue
        spawn = eo[0] if isinstance(eo[0], dict) else {}
        for area, pts in spawn.items():
            ui = a2u.get(num(area))
            if ui is None:
                continue
            for pt in obj_list(pts):
                pt = obj_list(pt)
                if len(pt) >= 2:
                    x, y = int(round(float(pt[0]) * 10)), int(round(float(pt[1]) * 10))
                    if 0 <= x <= 1000 and 0 <= y <= 1000:
                        extra.setdefault(str(ui), []).extend([x, y])
        if len(eo) >= 5:
            for ref in obj_list(eo[4]):
                ref = obj_list(ref)
                if len(ref) >= 2 and num(ref[1]):
                    kind = {"monster": "c", "npc": "c", "object": "o", "item": "i"}.get(str(ref[0]).lower())
                    if kind and kind + str(num(ref[1])) not in refs:
                        refs.append(kind + str(num(ref[1])))
    sk = ints(field(r, qk, "requiredSkill"))
    mr = ints(field(r, qk, "requiredMinRep"))
    row = [num(field(r, qk, "requiredRaces")), num(field(r, qk, "requiredClasses")),
           ints(field(r, qk, "preQuestSingle")) or None, ints(field(r, qk, "preQuestGroup")) or None,
           ints(field(r, qk, "exclusiveTo")) or None, num(field(r, qk, "breadcrumbForQuestId")),
           num(field(r, qk, "nextQuestInChain")), sorted(set(creatures)) or None,
           first_ints(o[1]) or None, first_ints(o[2]) or None, num(field(r, qk, "zoneOrSort")),
           num(field(r, qk, "questFlags")), num(field(r, qk, "specialFlags")), sk[:2] or None,
           rep or None, trig or None, num(field(r, qk, "parentQuest")), num(field(r, qk, "sourceItemId")),
           mr[:2] or None, ints(field(r, qk, "breadcrumbs")) or None,
           ints(field(r, qk, "requiredSourceItems")) or None, extra or None, refs or None]
    while row and row[-1] in (None, 0):
        row.pop()
    return row


# ------------------------------------------------------------------ QuestieDB
def seq(v):
    """a Lua list as the JSON export writes it: a list, or {"1": ..., "2": ...}"""
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return [v[k] for k in sorted(v, key=lambda k: int(k) if str(k).isdigit() else 0)]
    return []


def l10n(src):
    """QuestieDB's Forever translations -> loc[lang]: npc / npcsub / obj / item / quest names, qtext objectives"""
    out = {}
    for loc, kinds in src.items():
        L = out.setdefault(loc, {})
        for k, v in (kinds.get("npc") or {}).items():
            row = seq(v) if not isinstance(v, str) else [v]
            if row and isinstance(row[0], str) and row[0]:
                L.setdefault("npc", {})[int(k)] = row[0]
            if len(row) > 1 and isinstance(row[1], str) and row[1]:
                L.setdefault("npcsub", {})[int(k)] = row[1]
        for kind in ("obj", "item"):
            for k, v in (kinds.get(kind) or {}).items():
                if isinstance(v, str) and v:
                    L.setdefault(kind, {})[int(k)] = v
        for k, v in (kinds.get("quest") or {}).items():
            row = seq(v) if not isinstance(v, str) else [v]
            if row and isinstance(row[0], str) and row[0]:
                L.setdefault("quest", {})[int(k)] = row[0]
            lines = [s for s in seq(row[1]) if isinstance(s, str) and s.strip()] if len(row) > 1 else []
            if lines:
                L.setdefault("qtext", {})[int(k)] = {"o": " ".join(lines)}
    return out


def questie(q, a2u):
    out, unmapped = empty(), set()
    nk, ok, ik, qk = q["npcKeys"], q["objectKeys"], q["itemKeys"], q["questKeys"]

    def spawns(kind, sid, sp):
        for area, pts in (sp or {}).items():
            area = num(area)
            ui = a2u.get(area)
            if ui is None:
                # inside a dungeon / instance (no world map): remember which one (table ind),
                # questing addons route to its entrance (table dng)
                key = "%s%d" % (kind, sid)
                if area and area not in out["ind"].get(key, []):
                    out["ind"].setdefault(key, []).append(area)
                unmapped.add(area)
                continue
            for pt in obj_list(pts):
                pt = obj_list(pt)
                if len(pt) >= 2:
                    add_spots(out["spz"], "%s%d" % (kind, sid), ui, pt[0], pt[1])

    for sid, r in (q.get("npc") or {}).items():
        sid = int(sid)
        out["npc"][sid] = [field(r, nk, "name"), field(r, nk, "subName"), num(field(r, nk, "minLevel")),
                           num(field(r, nk, "maxLevel")), num(field(r, nk, "rank"))]
        spawns("c", sid, field(r, nk, "spawns"))
        fac = field(r, nk, "friendlyToFaction")
        if fac in ("A", "H", "AH"):
            out["nfac"][sid] = fac
        for qid in ints(field(r, nk, "questStarts")):
            push(out["qg"], qid, "c%d" % sid)
        for qid in ints(field(r, nk, "questEnds")):
            push(out["qe"], qid, "c%d" % sid)
    for sid, r in (q.get("obj") or {}).items():
        sid = int(sid)
        out["obj"][sid] = [field(r, ok, "name")]
        spawns("o", sid, field(r, ok, "spawns"))
        for qid in ints(field(r, ok, "questStarts")):
            push(out["qg"], qid, "o%d" % sid)
        for qid in ints(field(r, ok, "questEnds")):
            push(out["qe"], qid, "o%d" % sid)
    for iid, r in (q.get("item") or {}).items():
        iid = int(iid)
        out["item"][iid] = [field(r, ik, "name"), None, num(field(r, ik, "requiredLevel"))]
        for name, f in (("npcDrops", "drop"), ("objectDrops", "odrop"), ("itemDrops", "idrop")):
            for sid in ints(field(r, ik, name)):
                out[f].setdefault(iid, []).append([sid, 0])
        for sid in ints(field(r, ik, "vendors")):
            push(out["vend"], iid, sid)
        for qid in ints(field(r, ik, "questRewards")):
            push(out["rew"], iid, qid)
        sq = num(field(r, ik, "startQuest"))
        if sq:
            out["start"][iid] = sq
    for qid, r in (q.get("quest") or {}).items():
        qid = int(qid)
        out["quest"][qid] = [field(r, qk, "name"), num(field(r, qk, "questLevel")), num(field(r, qk, "requiredLevel"))]
        sb, fb = field(r, qk, "startedBy") or {}, field(r, qk, "finishedBy") or {}
        for idx, pre in (("1", "c"), ("2", "o")):
            for sid in ints(sb.get(idx) if isinstance(sb, dict) else None):
                push(out["qg"], qid, pre + str(sid))
            for sid in ints(fb.get(idx) if isinstance(fb, dict) else None):
                push(out["qe"], qid, pre + str(sid))
        for it in ints(sb.get("3") if isinstance(sb, dict) else None):
            out["start"].setdefault(it, qid)
        out["qx"][qid] = quest_extra(r, qk, a2u)
        ot = field(r, qk, "objectivesText")          # WoW Forever's own objective lines (quest log text)
        lines = [s for s in (ot.values() if isinstance(ot, dict) else ot or []) if isinstance(s, str) and s.strip()] \
            if isinstance(ot, (dict, list)) else ([ot] if isinstance(ot, str) and ot.strip() else [])
        if lines:
            out["qtext"][qid] = {"o": " ".join(lines)}
    return out, unmapped


# ------------------------------------------------------------------ dungeon entrances
def dungeons(path, a2u):
    """QuestieDB support/Forever/Zones/dungeons.lua -> dng: area id -> [name, parentArea, [uiMap, x, y, ...]]
    (x, y 0-1000 on the zone map). Alternative area ids (quests use them) point to the same entry."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    src = open(path, encoding="utf-8").read()
    for m in re.finditer(r'\[(\d+)\]\s*=\s*\{\s*"([^"]+)"\s*,\s*(nil|\{[\d,\s]*\})\s*,\s*(\d+)\s*,\s*\{(.*?)\}\s*\}\s*,', src):
        area, name, alts, parent, locs = int(m.group(1)), m.group(2), m.group(3), int(m.group(4)), m.group(5)
        spots = []
        for z, x, y in re.findall(r'\{\s*(\d+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\}', locs):
            ui = a2u.get(int(z))
            if ui:
                spots += [ui, int(round(float(x) * 10)), int(round(float(y) * 10))]
        row = [name, parent, spots or None]
        out[area] = row
        for a in re.findall(r"\d+", alts if alts != "nil" else ""):
            out.setdefault(int(a), row)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["pfquest", "questie"])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--zones", help="questie export json with the zone tables (for pfquest)")
    ap.add_argument("--conversion", help="QuestieDB data/Forever/conversion.json")
    ap.add_argument("--l10n", help="export.lua l10n output: QuestieDB's Forever translations (9 languages)")
    ap.add_argument("--dungeons", help="QuestieDB support/Forever/Zones/dungeons.lua (dungeon entrances)")
    a = ap.parse_args()
    src = json.load(open(a.src, encoding="utf-8"))
    if a.kind == "pfquest":
        a2u, coef = zone_tables(a.zones, a.conversion)
        out, unmapped = pfquest(src, a2u, coef)
    else:
        a2u, _ = zone_tables(a.src, a.conversion)
        out, unmapped = questie(src, a2u)
        out["dng"] = dungeons(a.dungeons, a2u)
        if a.l10n and os.path.exists(a.l10n):
            out["loc"] = l10n(json.load(open(a.l10n, encoding="utf-8")))
    print(a.kind, {k: len(v) for k, v in out.items()}, "zones without a map:", len(unmapped))
    os.makedirs(os.path.dirname(a.dst) or ".", exist_ok=True)
    with open(a.dst, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
