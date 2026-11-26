"""The WoW Forever client's own translations -> source json for tools/merge.py ({"loc": {lang: {table: {id: text}}}}).

The game ships every text it shows from its own files (DB2 tables) in each language it supports. wago.tools
serves those tables as CSV per build and language; this fetches the text columns of the tables ForeverDB
uses for every client language and keeps a text only where it differs from English (a language the client
doesn't have comes back in English and is left out).

  python tools/import_locales.py <build> <cache dir> <out.json> [--english <csv folder>] [--files DIR]

--files reads <Table>.<lang>.csv from a folder instead of wago.tools (tests). --english is the folder with the
English CSVs (AllTheThings ships them); without it English is fetched too.

Tables written per language (same ids as the English tables):
  item, itemdesc      item names / flavour text (ItemSparse)        area   zones (AreaTable)
  map                 maps (Map)                                    uimap  map names (UiMap)
  taxi                flight paths (TaxiNodes)                      faction factions (Faction)
  ach, achdesc, achrew achievements (Achievement)                   ctree  criteria texts (CriteriaTree)
  class, race         classes / races (ChrClasses, ChrRaces)        skill  skills / professions (SkillLine)
  tset                item sets (ItemSet)                           hol    holidays (HolidayNames by holiday)
  qsort, qinfoname    quest categories / types (QuestSort, QuestInfo)
  ctypename, cfamily  creature types / families (CreatureType, CreatureFamily)
  spell               names of the spells ForeverDB lists (SpellName, only ids in ieff / seff / sla)
  npc, obj            creature / object names where the client has them (Creature, GameObjects)
"""
import argparse, csv, glob, io, json, os, re, sys, time, urllib.request

LOCALES = ["deDE", "esES", "esMX", "frFR", "itIT", "koKR", "ptBR", "ruRU", "zhCN", "zhTW"]

# table: [(text column, loc table), ...]
TABLES = {
    "ItemSparse": [("Display_lang", "item"), ("Description_lang", "itemdesc")],
    "AreaTable": [("AreaName_lang", "area")],
    "Map": [("MapName_lang", "map")],
    "UiMap": [("Name_lang", "uimap")],
    "TaxiNodes": [("Name_lang", "taxi")],
    "Achievement": [("Title_lang", "ach"), ("Description_lang", "achdesc"), ("Reward_lang", "achrew")],
    "CriteriaTree": [("Description_lang", "ctree")],
    "Faction": [("Name_lang", "faction")],
    "ChrClasses": [("Name_lang", "class")],
    "ChrRaces": [("Name_lang", "race")],
    "SkillLine": [("DisplayName_lang", "skill")],
    "ItemSet": [("Name_lang", "tset")],
    "HolidayNames": [("Name_lang", "holname")],
    "QuestSort": [("SortName_lang", "qsort")],
    "QuestInfo": [("InfoName_lang", "qinfoname")],
    "CreatureType": [("Name_lang", "ctypename")],
    "CreatureFamily": [("Name_lang", "cfamily")],
    "SpellName": [("Name_lang", "spell")],
    "Creature": [("Name_lang", "npc")],
    "GameObjects": [("Name_lang", "obj")],
}


class Source:
    def __init__(self, build, cache, files=None, english=None):
        self.build, self.cache, self.files, self.english = build, cache, files, english
        os.makedirs(cache, exist_ok=True)

    def rows(self, table, lang):
        if lang == "enUS" and self.english:
            found = [f for f in glob.glob(os.path.join(self.english, table + ".*.csv")) if re.match(r".*[/\\]" + re.escape(table) + r"\.\d", f)]
            if found:
                with open(sorted(found)[-1], encoding="utf-8-sig", newline="") as f:
                    return list(csv.DictReader(f))
        if self.files:
            p = os.path.join(self.files, "%s.%s.csv" % (table, lang))
            if not os.path.exists(p):
                return None
            with open(p, encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f))
        p = os.path.join(self.cache, "%s.%s.%s.csv" % (table, self.build, lang))
        if not os.path.exists(p):
            url = "https://wago.tools/db2/%s/csv?build=%s&locale=%s" % (table, self.build, lang)
            data = None
            for attempt in range(4):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "forever-db/1 (github.com/foreverfraddons)"})
                    data = urllib.request.urlopen(req, timeout=120).read()
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        return None                       # (a table this client doesn't have)
                    time.sleep(2 + attempt * 3)
                except Exception:
                    time.sleep(2 + attempt * 3)
            if data is None:
                print("locales: %s %s not fetched" % (table, lang), file=sys.stderr)
                return None
            with open(p, "wb") as f:
                f.write(data)
            time.sleep(0.1)
        with open(p, encoding="utf-8-sig", newline="") as f:
            text = f.read()
        if "ID" not in text.split("\n", 1)[0]:
            return None                                   # (not a CSV: an error page)
        return list(csv.DictReader(io.StringIO(text)))


def holiday_ids(src):
    """HolidayNames id -> holiday ids (Holidays.HolidayNameID)"""
    out = {}
    for r in src.rows("Holidays", "enUS") or []:
        try:
            out.setdefault(int(r.get("HolidayNameID") or 0), []).append(int(r["ID"]))
        except (KeyError, ValueError):
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build")
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--english", help="folder with the English CSVs (<Table>.<build>.csv)")
    ap.add_argument("--files", help="folder of <Table>.<lang>.csv instead of wago.tools (tests)")
    ap.add_argument("--spells", help="source json(s) whose ieff / seff / sla spells get names, comma separated")
    a = ap.parse_args()
    src = Source(a.build, a.cache, a.files, a.english)

    spells = set()
    for p in (a.spells or "").split(","):
        if p and os.path.exists(p):
            d = json.load(open(p, encoding="utf-8"))
            for k in (d.get("seff") or {}):
                spells.add(int(k))
            for k in (d.get("sla") or {}):
                spells.add(int(k))
            for rows in (d.get("ieff") or {}).values():
                for e in rows:
                    if e and e[0]:
                        spells.add(int(e[0]))
    hol = holiday_ids(src)

    loc, stats = {}, {}
    for table, cols in TABLES.items():
        en = src.rows(table, "enUS")
        if not en:
            continue
        english = {}
        for r in en:
            try:
                english[int(r["ID"])] = {c: r.get(c) or "" for c, _ in cols}
            except (KeyError, ValueError):
                pass
        for lang in LOCALES:
            rows = src.rows(table, lang)
            if not rows:
                continue
            n = 0
            for r in rows:
                try:
                    rid = int(r["ID"])
                except (KeyError, ValueError):
                    continue
                if table == "SpellName" and spells and rid not in spells:
                    continue
                for col, dst in cols:
                    v = r.get(col) or ""
                    if not v.strip() or v == (english.get(rid) or {}).get(col):
                        continue                          # (empty, or still English: not translated)
                    ids = hol.get(rid, []) if table == "HolidayNames" else [rid]
                    for i in ids:
                        loc.setdefault(lang, {}).setdefault(dst, {})[i] = v
                        n += 1
            stats["%s %s" % (table, lang)] = n
    langs = {l: sum(len(t) for t in v.values()) for l, v in loc.items()}
    print("client translations (build %s):" % a.build, langs)
    print("per table:", {k: v for k, v in stats.items() if v})
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"loc": loc}, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
