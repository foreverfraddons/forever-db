# forever-db

A World of Warcraft: Forever database that rebuilds itself and feeds any number of addons.

**Sources** (a "hive": every source adds what the others are missing, and they are cross-checked)

| Source | What it brings | Licence |
|---|---|---|
| WoW Forever client tables (wago.tools CSV exports, shipped by AllTheThings) | Exact game data: every item (name, quality, item level, required level, class, slot, icon), flight masters, UI maps and their world bounds, zones, achievements and criteria, holidays, recipes/skill spells, item use effects, transmog sets, battle pets | Blizzard Entertainment's game data |
| [AllTheThings](https://github.com/ATTWoWAddon/AllTheThings) (its WoW Forever database, run with `tools/att`) | Hand-curated Forever quests: givers, levels, positions on Forever's maps, rewards, vendors, drops | MIT |
| [QuestieDB](https://github.com/Questie/QuestieDB) (Forever flavor + its Forever corrections) | The only open data with **WoW Forever** content: Forever-only quests, NPCs, items and objects, new zones (Zephras Isle, Riverglades, Mount Hyjal...), Forever map positions, links from player traces, Forever quest XP | GPL-3.0 (see LICENSE-DATA.txt) |
| [VMaNGOS](https://github.com/vmangos/core) nightly dump | Very accurate 1.12 drop rates, vendors, quests, spawns | GPL-2.0-or-later |
| [cMaNGOS classic-db](https://github.com/cmangos/classic-db) | Same kinds of data, independently maintained | GPL-3.0 |
| [pfQuest](https://github.com/shagu/pfQuest) | Drop rates, map positions, names in 9 languages | MIT |
| [LegacyForever](https://github.com/cjber/legacy-forever) | Forever's Legacy challenges, exploration area outlines, where each criterion happens | GPL-3.0-or-later |
| [Shortest Path Forever](https://github.com/cjber/shortest-path-forever) | Travel network: flight paths and times, boats/zeppelins with timetables, portals, teleports, dungeon entrances, trainers, food/drink vendors, town areas | GPL-3.0-or-later |
| [Drop Tables](https://github.com/valcheffnet/DropTables) | Real WoW Forever loot counts (players' shares + Blackthornes Farmer, EG Link, Everloot): drop chances per kill, gold per kill, skinning, kill spots. Counted like our own recordings: after 20 kills the Forever rate replaces the base rate | data CC BY-SA 4.0 |
| Command Center + Questicus recordings (`CommandCenterCollect`, `QuesticusCollect`) | What players actually see in Forever; replaces a drop rate once something was looted 20+ times | - |

Left out on purpose: MaNGOS Zero (CC BY-NC-SA, not compatible with GPL or CurseForge rewards), and every addon or
website that does not allow reuse (all-rights-reserved addons such as Blackthornes Farmer,
ForeverGold and GatherMate2; addons without a licence; data websites such as metaforge.app).
Wowhead is **not** scraped (their terms forbid it). Note: QuestieDB's *generated delta-base*
was built by the Questie team from Wowhead's Forever pages; set the repository variable
`QUESTIE_GENERATED` to `off` to leave that part out (traces and hand-written fixes stay).

**The rule: WoW Forever's own data and what players record in game always win, and are never overwritten.**
- The Forever client tables win every field they have; then the other Forever sources (QuestieDB Forever, AllTheThings); the 1.12 server databases only fill what's missing.
- Recordings (Command Center's Collector, Questicus) replace the sources and Drop Tables for everything they cover, from the first loot: names, levels, drop chances, money, skinning, fishing, quest rewards, givers, map spots. Drop Tables (other players' counts) replaces a base rate after 20 kills.
- Recordings are kept for good in `recorded/` (one JSON per recording file): counts only go up, spots and entries are only added, so a reset SavedVariables or a deleted file never takes recorded data out.
- `fixes.json` (hand-checked in game) corrects the sources, but recorded spots stay next to the corrected ones. The size caps in the slices never cut a recorded drop.

**How sources are combined** (`tools/merge.py`, report in `REPORT.md` and the release):
- Every entry any source has is kept.
- Names, levels, ranks, quality: Forever data wins any field it has; otherwise the value most
  sources agree on (ties: VMaNGOS > cMaNGOS > pfQuest).
- Quest givers/enders, vendors, rewards: union of all sources.
- Drop rates: median of the sources that give one; `0` = known to drop there, rate unknown.
- Map positions: world coordinates from the server databases, Forever map positions from
  QuestieDB/pfQuest (Classic positions moved onto Forever's redrawn maps with QuestieDB's
  conversion factors).
- The report lists, per source, how many entries it has and how many only it has, plus every
  field where sources disagree, with examples.

## Hand-checked corrections

`fixes.json` is applied last and wins over every source and recording: `spm` replaces an npc's or object's
map spots (`"c257001": {"2548": [771, 728]}`, uiMap with 0-1000 coordinates, i.e. map % x 10), `qg` / `qe` add
quest givers / enders, `note` adds a short tip. Add a line there whenever a location is confirmed in game.

## How it updates

1. Twice a day (07:17 and 19:17 UTC), and whenever new recordings arrive, `Build database`:
   - fetches the newest version of **every** source (QuestieDB, VMaNGOS, cMaNGOS, pfQuest);
   - re-imports only the sources that changed (cached by their version);
   - merges and cross-checks them (`dist/report.md`), then adds every recording;
   - and, only when the data's hash changed (or when run by hand with *force*):
     - rebuilds the **ForeverDB** addon in `ForeverDB/`;
     - commits it with `REPORT.md`, tags it `vYYYY.MM.DD.N`;
     - uploads it to CurseForge (project 1807282);
     - refreshes the `latest` GitHub release (full `forever.json.gz` with translations, the report, slices).
2. Your PC's scheduled task pushes new recordings to the addon repo (`collected/`), which pings this repo.
   Other players' Questicus findings (respawn times, new spawn points, zone border crossings, objects that
   appear on a kill) reach it in game: Questicus' relay whispers them to a collector (the author's
   Questicus with its local dev tools), which keeps them in `QuesticusCollect.relay[<sender hash>]`. The
   build reads each sender as a recording of its own (`<file>-relay-<hash>`).
3. Repos listed in `DB_CONSUMERS` get a `db-updated` ping.

The **ForeverDB** CurseForge package holds three LoadOnDemand addon folders:

| Folder | Global | What |
|---|---|---|
| `ForeverDB` | `ForeverDB` | everything addons use: all entities and relations, quest details, the client tables, Legacy and travel data (drop lists capped at the best 40 sources per item) |
| `ForeverDB_Full` | `ForeverDBFull` | uncapped drop/vendor/reward lists, every world and map position, and `src` (which source has each entry) |
| `ForeverDB_Locales` | `ForeverDBLocale` | names in 9 languages: `loc[locale][npc/obj/item/quest][id]` |

The **ForeverDB** addon is published on its own. Addons that use it list it as a required dependency on CurseForge, and the CurseForge app installs it for players. It is LoadOnDemand: an addon calls `C_AddOns.LoadAddOn("ForeverDB")`, then reads the global `ForeverDB`. Command Center does this.

## Layout

```
tools/import_base.py   MaNGOS-family SQL dump (cMaNGOS, VMaNGOS) -> source json
tools/lua/export.lua   loads pfQuest / QuestieDB Lua data (+ QuestieDB's Forever corrections) -> json
tools/import_addons.py pfQuest / QuestieDB json -> source json (Forever map positions)
tools/merge.py         all source jsons -> base.json + cross-check report
tools/build.py         base + recordings -> master forever.json (+ meta.hash)
tools/slice.py         master -> Lua data files for one addon (spec in slices/)
tools/sqldump.py       dump reader (no MySQL needed)
tools/luatable.py      SavedVariables reader
slices/<name>.json     what each addon gets; slices/<name>.toc = its data addon's toc
tests/run_tests.py     end-to-end test on a tiny sample
ForeverDB/             the shared data addon (generated - do not edit; uploaded to CurseForge)
.pkgmeta               CurseForge packaging for ForeverDB/
```

## Using it in another addon

**Easiest:** use the shared **ForeverDB** addon.
1. Add it as a required dependency in your `.pkgmeta` (`required-dependencies`).
2. Load it when you need it: `C_AddOns.LoadAddOn("ForeverDB")`.
3. Read the global `ForeverDB` (tables below). `ForeverDB.meta` has the build date, hash and counts.

**Own slice** (other tables or limits, shipped inside your addon):
1. Add `slices/myaddon.json`, for example:
   ```json
   {"global": "MyAddon_DB", "files": "Data", "target": "MyAddon_Data", "toc": "MyAddon_Data.toc",
    "tables": ["npc", "quest", "qg", "spw", "spm"], "prune": false}
   ```
   Optionally add `slices/myaddon.toc` if the slice should be its own LoadOnDemand addon.
2. Every slice is attached to the `latest` release as `myaddon.zip`.
3. Add your repo to `DB_CONSUMERS` and download that asset on the `db-updated` ping.

Tables:

| Table | Contents |
|---|---|
| `npc` | name, sub, minLv, maxLv, rank |
| `obj` | name |
| `item` | name, quality, reqLevel, itemLevel, class, subclass, inventoryType, icon, allowableClass, requiredSkill, requiredSkillRank, allowableRaces, minFaction, minReputation (reputation needed to buy / use it: faction id + standing 0 Hated ... 7 Exalted) |
| `quest` | title, level, minLevel |
| `qg` / `qe` | quest givers / enders ("c123" creature, "o45" object) |
| `drop` / `odrop` / `idrop` | per item: {source, chance per 10000, ...} (0 = rate unknown) |
| `vend` | per item: vendor ids |
| `vp` | prices seen |
| `rew` | quest rewards |
| `qrw` | quest rewards in detail: [quest] = {money in copper, full XP (before the grey-quest penalty), {choice items}, {fixed items}}. Money and items from the MaNGOS dumps; XP from QuestieDB's Forever quest XP (players' traces), else the classic formula from RewMoneyMaxLevel; recordings replace both |
| `start` | item starts a quest |
| `world` | world drops (minimum level) |
| `taxi` | flight masters: name, continent, x, y, z, flags, Horde/Alliance mount |
| `umap` / `umaa` | UI maps (name, parent, type) / their placement in the world (bounds) |
| `area` | zones: name, continent, parent, exploration level, faction mask, flags |
| `ach` / `ctree` / `crit` / `mtree` | achievements and Legacy challenges, criteria trees, criteria, modifier trees |
| `hol` | holidays: name, looping, region, priority, filter, flags, durations, dates |
| `sla` / `ieff` / `seff` | skill line spells (recipes) / item use effects / spell effects |
| `tset` / `bpet` / `ctun` / `wmo` | transmog sets / battle pet species / content tuning (levels) / map overlays |
| `legacy` / `lcrit` / `explore` | LegacyForever: challenge data, criterion locations, exploration areas |
| `qtext` | `{quest: {d = details (the offer), o = objectives, p = progress ("have you got them?"), c = completion (turn-in text), e = end text, ot = {objective lines}, rec = 1 when recorded in game}}` quest dialog: what players recorded in WoW Forever (Questicus) wins, then QuestieDB's Forever objective lines, then VMaNGOS / cMaNGOS / pfQuest (ForeverDB_Full). Texts keep the game's $N / $C / $R / $B tokens |
| `qgreet` | `{"c<npc>" / "o<object>": greeting}` the text above a quest giver's quest list (recorded in game, then MaNGOS) (ForeverDB_Full) |
| `loc[lang]` | every language the game supports - deDE, esES, esMX, frFR, itIT, koKR, ptBR, ruRU, zhCN, zhTW (English is the base tables). Per language: `npc`, `npcsub` (titles), `obj`, `item`, `quest`, `qtext` and the client's own `itemdesc`, `area`, `map`, `uimap`, `taxi`, `faction`, `ach` / `achdesc` / `achrew`, `ctree`, `class`, `race`, `skill`, `tset`, `holname`, `qsort`, `qinfoname`, `ctypename`, `cfamily`, `spell`. Priority: the WoW Forever client's own texts (wago.tools, per build) > QuestieDB's Forever translations (l10n/Forever + traces) > pfQuest. ForeverDB_Locales only keeps the game's own language in memory (esMX also esES, enGB = English: `meta.locFallback`); `ForeverDBLocaleAll = true` before loading keeps all |
| `loc[lang].qtext` | quest details and objectives in 8 more languages (pfQuest) (ForeverDB_Locales) |
| `zbord` | `{zone areaID: {c = continent mapID, ui = uiMapID, n = map chunks, w = {{x, y, x, y, ...}, ...} world-yard loops (outlines and holes), m = the same loops on the zone's map, 0-1000}}` zone borders from the WoW Forever client's own terrain (every ADT map chunk's area) |
| `abord` | the same for every sub-zone (towns, camps, ...), plus `z` = its zone (ForeverDB_Full) |
| `agrid` | `{continent: {o, c, z = {row: "zoneID*count,..."}}}` which zone each 33-yard map chunk belongs to (world X = o - (row + 0.5) * c, Y = o - (col + 0.5) * c), for point-in-zone lookups (ForeverDB_Full) |
| `zcross` | `{continent: {"zoneA-zoneB": {x, y, ...}}}` world points where players really walked from one zone into the next (Questicus records them; points within 40 yards merged, most walked first, 12 per zone pair): the passes through zone borders, for pathing and travel times |
| (recordings) `nspawn` | Questicus: quest mobs / objects seen standing (out of combat, next to the player) more than 30 yards from every known spawn - merged into `spw` (or `spm` when only map spots are known), 30 yards apart |
| `skin` | `{item: {npc, chance per 10000, npc, chance, ...}}` (flat like drop) what skinning a mob gives (Drop Tables, 3+ skinned corpses) |
| `gold` | `{npc: [average copper per kill, smallest pile, largest pile, kills]}` (Drop Tables) |
| `spf` | Shortest Path Forever travel data (TaxiNodes, TaxiPaths, Docks, Routes, Portals, Teleports, Entrances, trainers, Food, Drink, TownAreas, Zones, Walks) |
| `spw` | spawn world coordinates per map. Convert in game with `C_Map.GetMapPosFromWorldPos` |
| `qe` | quest enders (same keys as `qg`) |
| `qx` | quest details from QuestieDB, per quest: 1 races mask, 2 classes mask, 3 preQuestSingle, 4 preQuestGroup, 5 exclusiveTo, 6 breadcrumbFor, 7 nextInChain, 8 creature objectives, 9 object objectives, 10 item objectives, 11 zoneOrSort, 12 questFlags, 13 specialFlags, 14 requiredSkill {id, value}, 15 reputation rewards {faction, value, ...}, 16 exploration spots {[uiMap] = {x, y, ...}}, 17 parentQuest, 18 sourceItem, 19 requiredMinRep, 20 breadcrumbs, 21 requiredSourceItems, 22 extra objective spots {[uiMap] = {x, y, ...}}, 23 extra objective targets {"c123", "o45"} |
| `nfac` | NPC friendly to: "A", "H" or "AH" |
| `dng` | dungeon entrances (QuestieDB): [areaId] = {name, parentArea, {uiMap, x, y, ...}} (also under alternative area ids) |
| `ind` | npcs / objects that live inside a dungeon: ["c123"] = {areaId, ...} (route to its `dng` entrance) |
| `ptl` | patrol paths of moving mobs, recorded in game with Questicus `/qc patrol` (the longest recording wins): ["c123"] = {[uiMap] = {x, y, ...} in walking order} |
| (recordings) `removed` | spots players Ctrl-clicked away in Questicus ("nothing here"): the matching `spw` / `spm` points of that npc / object are deleted at build time (12 yd / 15 map units); fixes.json still wins |
| `qwk` | how long quests really take (active time while working on them, averaged over everyone's runs, Questicus): [quest] = {seconds, runs} |
| `qsp` | quest objective areas players made progress in (Questicus recordings): [quest] = {[uiMap] = {x, y, ...}} |
| `note` | short hand-written tips for npcs / objects (from `fixes.json`): ["c257001"] = "Stands in a murloc hut..." |
| `qsrc` | what players looted right before a quest objective counted up (Questicus recordings): [quest] = {"o645516", ...} |
| `spm` | map spots (uiMap, 0-1000): Forever positions for things without world coordinates + recordings |

The master `forever.json` (release asset) also has `spz` (all Forever map positions), `loc`
(names in 9 languages) and `src` (which sources have each entry, bit k = k-th source).

## Settings (repository → Settings → Secrets and variables → Actions)

- **Variable `ADDON_REPO`:** `owner/CommandCenter`, the repo holding `collected/`.
- **Variable `DB_CONSUMERS`** (optional): other addon repos to ping.
- **Secret `PIPELINE_TOKEN`:** a fine-grained GitHub token with Contents (read/write) and Actions (read/write) on both repos.
- **Variable `QUESTIE_GENERATED`** (optional): `off` leaves out QuestieDB's Wowhead-derived delta-base.
- **Secret `CF_API_KEY`:** CurseForge API token (https://legacy.curseforge.com/account/api-tokens), used to upload ForeverDB.

## Licence

The merged data is GPL-3.0. Every slice ships `LICENSE-DATA.txt` (sources and their licences),
`LICENSE-GPL.txt` and `LICENSE-pfQuest.txt` (MIT notice).
