"""End-to-end check of the pipeline on the tiny sample dump + sample recording."""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run(*a):
    subprocess.run([sys.executable, *a], check=True, cwd=ROOT)


def main():
    tmp = tempfile.mkdtemp()
    dump, col, out = os.path.join(tmp, "dump"), os.path.join(tmp, "collected"), os.path.join(tmp, "addon")
    os.makedirs(dump); os.makedirs(col); os.makedirs(out)
    shutil.copy(os.path.join(HERE, "mini.sql"), dump)
    shutil.copy(os.path.join(HERE, "rec1.lua"), col)
    shutil.copy(os.path.join(HERE, "rec2.lua"), col)
    with open(os.path.join(out, "Test_DB.toc"), "w") as f:
        f.write("## Interface: 16001\n## Version: 0\n\nold.lua\n")
    run("tools/import_base.py", dump, os.path.join(tmp, "base.json"))
    run("tools/build.py", "--base", os.path.join(tmp, "base.json"), "--collected", col, "--out", os.path.join(tmp, "forever.json"),
        "--droptables", os.path.join(HERE, "fixtures", "droptables.json"))
    spec = json.load(open(os.path.join(ROOT, "slices", "forever.json")))
    spec["toc"] = "Test_DB.toc"
    sp = os.path.join(tmp, "spec.json"); json.dump(spec, open(sp, "w"))
    run("tools/slice.py", sp, os.path.join(tmp, "forever.json"), out)
    db = json.load(open(os.path.join(tmp, "forever.json")))
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + name)
        ok = ok and cond
    check("forever rate replaces base after 20 loots", [100, 2000] in db["drop"]["5523"])
    check("forever-only creature drop added", [777, 7500] in db["drop"]["5523"])
    check("group equal share", db["drop"]["7000"] == [[101, 2500]])
    check("reference chance multiplied", db["drop"]["8001"] == [[101, 500]])
    check("vendor template", 200 in db["vend"]["5523"])
    check("recorded quest reward", 50001 in db["rew"]["5523"])
    # Questicus' Record.lua tables
    check("recorded money per kill", db["gold"]["5523"][3] >= 4)
    check("recorded skinning", any(p[0] == 5523 for p in db["skin"].get("4232", [])))
    check("fishing by zone", db["fish"]["1429"] == [[6303, 10000]])
    check("flight costs", db["fcost"]["352"]["nodes"]["Sentinel Hill"][0] == 80)
    check("quest details + offered-by giver", db["qinfo"]["50001"]["xb"] == 420 and "c888" in db["qg"]["50001"])
    check("game rewards replace the base ones", db["qrw"]["50001"][0] == 0 and db["qrw"]["50001"][1] == 420
          and db["qrw"]["50001"][3] == [2318] and db["quest"]["50001"][1] == 4)
    check("class training costs per ability", db["train"]["HUNTER"]["Serpent Sting (Rank 2)"] == [200, 10]
          and db["train"]["HUNTER"]["Arcane Shot"] == [100, 6])
    check("vendors: prices, limits, costs, requirements", db["vendx"]["5523"]["200"]["p"] == 450
          and db["vendx"]["5523"]["200"]["r"] == ["Requires Level 5"] and db["vendx"]["5523"]["9999"]["c"] == [[20558, 20]]
          and 5523 in db["vend"]["9999"])
    check("objects that appear on a kill have no respawn time", db["osummon"].get("o4444") == 1)
    check("respawn between 'not back after' and 'back by'", db["resp"].get("c5555") == 150)
    sp6 = [g for g in db["spw"].get("c6", []) if g[0] == 0]
    check("new spawn points merged, near ones once", sp6 and sum(1 for g in sp6 for k in range(1, len(g) - 1, 2) if abs(g[k] - 10000) < 30) == 1)
    check("hand-set route paths kept", db["fpath"].get("complete:5", {}).get("n") == [1, 2, 3, 4, 5, 6])
    check("findings relayed in game from another player count as their own recording", db["resp"].get("c7777") == 300)
    check("zone border crossings: near points merged, removed ones gone", db["zcross"]["1"]["14-17"] == [305, -3768])
    check("walls drawn by hand kept, removed ones gone", db["walls"].get("1", {}).get("wa", {}).get("n") == [0, 0, 50, 50] and "wb" not in db["walls"].get("1", {}))
    check("zone outline redrawn by hand", db["zbord"].get("9001", {}).get("w") == [[0, 0, 100, 0, 100, 100]] and db["zbordEd"].get("1"))
    check("respawn times measured in game", db["resp"]["c5523"] == 300 and db["resp"]["o1731"] == 250)
    check("game XP at a grey-ish level worked back to full", db["qrw"]["50002"][1] == 500)
    check("rares, subzones, skills, types", db["rare"]["99"]["gap"] == 8000 and "Northshire Abbey" in db["zsub"]["1429"]
          and db["oskill"]["1731"] == ["Mining", 1] and db["ctype"]["5523"] == ["Beast", "Wolf"])
    check("renamed npc", db["npc"]["100"][0] == "Murloc Raider (Forever)")
    check("map spots", db["spm"]["c777"]["1429"] == [500, 600])
    # Drop Tables: 40 kills, 36 lootable / 36 opened, 12 drops -> 12 / 40 = 30% (replaces the base rate: 20+ kills)
    check("drop tables: chance per kill", [4444, 3000] in db["drop"]["5523"])
    check("drop tables: new npc from its name and levels", db["npc"]["4444"][0] == "Forever Crab" and db["npc"]["4444"][2:4] == [5, 6])
    check("drop tables: gold per kill, smallest / largest, kills", db["gold"]["4444"] == [7, 5, 15, 40])
    check("drop tables: skinning chance", db["skin"]["2318"] == [[4444, 8000]])
    check("drop tables: kill spots on the map (50 x 50 grid cell centres)", db["spm"]["c4444"]["1429"][:2] == [510, 510])
    check("Questicus objective spots (near ones merged)", db["qsp"]["50001"]["1429"] == [400, 500, 700, 700])
    check("Questicus objective sources (every one recorded, most seen first)", db["qsrc"]["50001"][0] == "o645516")
    check("Questicus patrol path kept in walking order", db["ptl"]["c263380"]["2548"] == [100, 100, 120, 110, 140, 130, 160, 150])
    check("Questicus real quest time (active seconds, runs)", db["qwk"]["50001"] == [300, 2])
    check("spot a player removed in game is gone, the other stays", db["spm"]["c888"]["1429"] == [300, 300])
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import build as _b
    t = {"qx": {1: [0, 0, None, None, None, None, 3], 2: [0, 0, None, None, None, None, 3], 3: [0], 4: [0, 0, [9], None, None, None, 5], 5: [0, 0, [7]]}}
    check("chain prerequisites from 'next' links (only where none exist)",
          _b.chain_prereqs(t) == 1 and t["qx"][3][2] == [1, 2] and t["qx"][5][2] == [7])
    check("quest rewards: money, XP from RewMoneyMaxLevel (/0.6 up to level 60), choice items",
          db["qrw"]["400"][:3] == [350, 2400, [5523]] and "401" not in db["qrw"])
    check("fixes.json applied (Old Rot-Chum spot + note, extra quest giver)",
          db["spm"]["c257001"]["2548"] == [771, 728] and "murloc hut" in db["note"]["c257001"]
          and "c259961" in db["qg"]["95120"])
    toc = open(os.path.join(out, "Test_DB.toc")).read()
    check("toc lists data file", "ForeverDB.lua" in toc and "old.lua" not in toc)
    lua = open(os.path.join(out, "ForeverDB.lua")).read()
    check("lua written", "ForeverDB = ForeverDB or {}" in lua and ";(function()" in lua)
    exe = shutil.which("lua5.1") or shutil.which("lua") or shutil.which("texlua")
    if exe:
        chk = os.path.join(tmp, "check.lua")
        with open(chk, "w") as f:
            f.write('dofile([[%s]]) assert(ForeverDB.drop[5523][1]) print("lua loads")' % os.path.join(out, "ForeverDB.lua"))
        r = subprocess.run([exe, chk], capture_output=True, text=True)
        if r.returncode:
            print(r.stdout, r.stderr)
        check("lua file loads", r.returncode == 0)

    # ---- RULE: client data and recordings are what the release uses, never overwritten
    kt = os.path.join(tmp, "keeptest"); kcol = os.path.join(kt, "collected"); keep = os.path.join(kt, "recorded")
    os.makedirs(kcol)
    rec = os.path.join(kcol, "rec-pc.lua")
    with open(rec, "w", encoding="utf-8-sig") as f:      # byte-order mark, like the PC's sync script writes
        f.write('CommandCenterCollect = { ["loot"] = { ["c:101"] = { ["n"] = 2, ["i"] = { [7000] = 1, [7002] = 2 } } },'
                ' ["sp"] = { ["c:257001"] = { [2548] = { 100, 900 } } } }\n')
    kfx = os.path.join(kt, "fixes.json")
    json.dump({"spm": {"c257001": {"2548": [771, 728]}}}, open(kfx, "w"))
    def kbuild(name):
        run("tools/build.py", "--base", os.path.join(tmp, "base.json"), "--collected", kcol, "--keep", keep,
            "--fixes", kfx, "--droptables", os.path.join(HERE, "fixtures", "droptables.json"),
            "--out", os.path.join(kt, name))
        return json.load(open(os.path.join(kt, name)))
    k1 = kbuild("k1.json")
    check("recordings with a byte-order mark are read", k1["meta"]["recordings"] == 1)
    check("a recorded chance replaces the base one from the first loot (2 kills)",
          [101, 5000] in k1["drop"]["7000"] and [101, 10000] in k1["drop"]["7002"])
    check("fixes.json corrects the spot but the recorded spot stays",
          k1["spm"]["c257001"]["2548"] == [771, 728, 100, 900])
    # the PC's SavedVariables were reset: the new snapshot has fewer loots and no spots
    with open(rec, "w", encoding="utf-8-sig") as f:
        f.write('CommandCenterCollect = { ["loot"] = { ["c:101"] = { ["n"] = 1, ["i"] = { [7000] = 1 } } } }\n')
    k2 = kbuild("k2.json")
    check("kept recordings: counts never go down after a reset", [101, 5000] in k2["drop"]["7000"] and [101, 10000] in k2["drop"]["7002"])
    check("kept recordings: recorded spots survive a reset", k2["spm"]["c257001"]["2548"] == [771, 728, 100, 900])
    os.remove(rec)
    k3 = kbuild("k3.json")
    check("kept recordings: a deleted recording file still counts", [101, 5000] in k3["drop"]["7000"] and k3["meta"]["recordings"] == 1)
    import slice as _s
    capdb = {"seen": {"c9": {"7000": [1, 1]}}, "drop": {"7000": [[1, 9000], [2, 8000], [9, 100]]}}
    check("slice caps never cut a recorded drop row", _s.capped(capdb, "drop", "7000", capdb["drop"]["7000"], 2) == [[1, 9000], [2, 8000], [9, 100]]
          and _s.capped({"seen": {}}, "drop", "7000", capdb["drop"]["7000"], 2) == [[1, 9000], [2, 8000]])

    # ---- quest dialog: Forever sources first field by field, recordings win
    import merge as _m
    mq, _ = _m.merge([("questie", {"qtext": {"1": {"o": "Forever objectives"}}}),
                      ("vmangos", {"qtext": {"1": {"o": "1.12 objectives", "d": "1.12 details", "c": "done"}}})])
    check("quest dialog: Forever objective text wins, the rest filled from MaNGOS",
          mq["qtext"]["1"] == {"o": "Forever objectives", "d": "1.12 details", "c": "done"})
    ml, _ = _m.merge([("questie", {"loc": {"deDE": {"qtext": {"1": {"o": "Forever-Ziele"}}, "npc": {"5": "Forever-Name"}}}}),
                      ("pfquest", {"loc": {"deDE": {"qtext": {"1": {"o": "1.12-Ziele", "d": "1.12-Details"}}, "npc": {"5": "1.12-Name"}}}})])
    check("translated quest dialog: Forever objective text wins, the details filled from pfQuest",
          ml["loc"]["deDE"]["qtext"]["1"] == {"o": "Forever-Ziele", "d": "1.12-Details"} and ml["loc"]["deDE"]["npc"]["5"] == "Forever-Name")
    qcol = os.path.join(tmp, "qtextcol"); os.makedirs(qcol)
    with open(os.path.join(qcol, "qrec-pc.lua"), "w", encoding="utf-8-sig") as f:
        f.write('QuesticusCollect = { ["qtext"] = { [5001] = { ["d"] = "Forever words, $N.", ["p"] = "Got them?", ["t"] = 5 } },'
                ' ["qgreet"] = { ["c777"] = { ["x"] = "Hello $C.", ["t"] = 5 } } }\n')
    base_q = json.load(open(os.path.join(tmp, "base.json")))
    base_q["qtext"] = {"5001": {"d": "old words", "o": "kill things", "c": "thanks"}}
    json.dump(base_q, open(os.path.join(tmp, "base_q.json"), "w"))
    run("tools/build.py", "--base", os.path.join(tmp, "base_q.json"), "--collected", qcol, "--out", os.path.join(tmp, "q.json"))
    qdb = json.load(open(os.path.join(tmp, "q.json")))
    check("quest dialog: recorded text replaces the sources', the rest stays",
          qdb["qtext"]["5001"] == {"d": "Forever words, $N.", "o": "kill things", "p": "Got them?", "c": "thanks", "rec": 1})
    check("quest dialog: recorded greeting", qdb["qgreet"]["c777"] == "Hello $C.")

    # ---- zone borders from the terrain (tools/import_terrain.py)
    tdir = os.path.join(tmp, "terrain"); os.makedirs(tdir)
    run("tests/fixtures/terrain/make.py", tdir)
    run("tools/import_terrain.py", os.path.join(tdir, "csv"), os.path.join(tdir, "cache"), os.path.join(tdir, "t.json"),
        "--files", os.path.join(tdir, "files"))
    tj = json.load(open(os.path.join(tdir, "t.json")))
    z, s = tj["zbord"].get("1", {}), tj["abord"].get("2", {})
    check("terrain: zone border (world yards) and on its map (0..1000)",
          z.get("ui") == 1429 and z.get("n") == 512 and z.get("w") == [[16533, 16000, 17067, 16000, 17067, 17067, 16533, 17067]]
          and z.get("m") == [[1000, 500, 1000, 0, 0, 0, 0, 500]])
    check("terrain: sub-zone border, with its zone", s.get("z") == 1 and s.get("n") == 16
          and s.get("w") == [[16933, 16933, 16800, 16933, 16800, 16800, 16933, 16800]])
    check("terrain: zone grid for point lookups (sub-zone rolled up to its zone)", tj["agrid"]["0"]["z"]["5"] == "1*32,0*992")
    check("terrain: instances left out", "33" not in tj["agrid"])

    # ---- VMaNGOS: final-patch rows only, several creatures per spawn point
    vdump = os.path.join(tmp, "vdump"); os.makedirs(vdump)
    shutil.copy(os.path.join(HERE, "vm_mini.sql"), vdump)
    run("tools/import_base.py", vdump, os.path.join(tmp, "src-vmangos.json"))
    vm = json.load(open(os.path.join(tmp, "src-vmangos.json")))
    check("vmangos newest patch row", vm["npc"]["300"][0] == "New Name" and vm["npc"]["300"][2] == 3)
    check("vmangos drop valid in 1.12 kept", [300, 5000] in vm["drop"].get("9000", []))
    check("vmangos drop removed before 1.12 skipped", "9001" not in vm["drop"])
    check("vmangos spawn shared by id2", "c301" in vm["spw"] and "c300" in vm["spw"])
    check("vmangos spawn ended before 1.12 skipped", vm["spw"]["c301"] == [[0, 100, 201]])

    if exe:
        fx = os.path.join(HERE, "fixtures")
        conv = os.path.join(fx, "questiedb", "data", "Forever", "conversion.json")
        qj, pj = os.path.join(tmp, "questie.json"), os.path.join(tmp, "pfquest.json")
        subprocess.run([exe, "tools/lua/export.lua", "questie", os.path.join(fx, "questiedb"), "Forever", qj], check=True, cwd=ROOT)
        subprocess.run([exe, "tools/lua/export.lua", "pfquest", os.path.join(fx, "pfquest"), pj], check=True, cwd=ROOT)
        dng = os.path.join(fx, "questiedb", "support", "Forever", "Zones", "dungeons.lua")
        run("tools/import_addons.py", "questie", qj, os.path.join(tmp, "src-questie.json"), "--conversion", conv, "--dungeons", dng)
        run("tools/import_addons.py", "pfquest", pj, os.path.join(tmp, "src-pfquest.json"), "--zones", qj, "--conversion", conv)
        qs = json.load(open(os.path.join(tmp, "src-questie.json")))
        pf = json.load(open(os.path.join(tmp, "src-pfquest.json")))
        check("questie correction adds a Forever-only npc", qs["npc"].get("99999", [None])[0] == "Skyborne Scout")
        check("questie _add operation", "c100" in qs["qg"].get("50002", []))
        check("questie replacement", qs["npc"]["100"][2] == 12)
        check("questie quest details (qx) for every quest", set(qs["qx"]) == set(qs["quest"]))
        check("dungeon entrances (dng) incl. alternative area ids",
              qs["dng"].get("1581", [None])[0] == "The Deadmines" and qs["dng"].get("10029", [None])[0] == "The Deadmines"
              and qs["dng"]["717"][2][1:] == [524, 700])
        check("questie authored fix", qs["npc"]["101"][0] == "Kobold Tunneler")
        check("questie dynamic (per character) fixes skipped", qs["npc"]["101"][0] != "SHOULD NOT APPLY")
        check("questie spawn on Forever map", qs["spz"]["c99999"] == {"1429": [255, 402]})
        check("questie drop without rate", qs["drop"]["5523"] == [[100, 0]])
        qde = qs.get("loc", {}).get("deDE", {})
        check("questie translations: npc, quest and item names", qde.get("npc", {}).get("99999") == "Himmelsgeborener Späher"
              and qde.get("quest", {}).get("50001") == "Muschelsuche")
        check("questie translations: a trace wins over the base file", qde.get("npc", {}).get("101") == "Koboldtunnelgräber")
        check("questie translations: an override replaces the item name",
              qde.get("item", {}).get("5523") == "Kleine seepockenbesetzte Muschel")
        check("questie translations: quest objective lines", qde.get("qtext", {}).get("50001") == {"o": "Sammelt 5 Muscheln. Kehrt zurück."})
        check("questie translations: only locales with files", set(qs.get("loc", {})) == {"deDE"})
        check("pfquest rate per 10000", [100, 3000] in pf["drop"]["5523"])
        check("pfquest Classic map moved onto Forever map", pf["spz"]["c100"] == {"1412": [300, 400]})
        check("pfquest translations", pf["loc"]["deDE"]["npc"]["100"] == "Murlocräuber")
        # ---- merge: Forever source wins, vote for the rest, union of relations, median rates
        base_src = os.path.join(tmp, "base.json")
        run("tools/merge.py", "--out", os.path.join(tmp, "merged.json"), "--report", os.path.join(tmp, "report.json"),
            "questie=" + os.path.join(tmp, "src-questie.json"), "vmangos=" + os.path.join(tmp, "src-vmangos.json"),
            "cmangos=" + base_src, "pfquest=" + os.path.join(tmp, "src-pfquest.json"))
        m = json.load(open(os.path.join(tmp, "merged.json")))
        rep = json.load(open(os.path.join(tmp, "report.json")))
        check("merge keeps entries every source has", all(k in m["npc"] for k in ("100", "300", "99999", "777") if k != "777" or "777" in json.load(open(base_src))["npc"]))
        check("merge: Forever level wins", m["npc"]["100"][2] == 12)
        check("merge: Forever-only npc kept", m["npc"]["99999"][0] == "Skyborne Scout")
        check("merge: drop rate from sources with a rate", next(c for s, c in m["drop"]["5523"] if s == 100) > 0)
        check("merge: drop only pfQuest knows", any(s == 101 for s, _ in m["drop"]["5523"]))
        check("merge: source mask", m["src"]["npc"]["100"] & 1 == 1)
        check("merge: the Forever translation wins over pfQuest's", m["loc"]["deDE"]["npc"]["100"] == "Murlocplünderer")
        check("merge report", rep["forever_only"]["npc"] >= 1 and "npc.minLv" in rep["conflicts"])
        check("report markdown", os.path.exists(os.path.join(tmp, "report.md")))
    # ---- AllTheThings preprocessor (Forever build: classic tags on, later expansions off)
    sys.path.insert(0, os.path.join(ROOT, "tools", "att"))
    from preprocess import preprocess, evaluate
    check("att: #if FOREVER on, AFTER TBC off", evaluate("FOREVER") and not evaluate("AFTER TBC") and evaluate("BEFORE 7.3.0"))
    check("att: NOT ANYCLASSIC off", not evaluate("NOT ANYCLASSIC"))
    pp = preprocess("a\n-- #if AFTER WRATH\nb\n-- #else\nc\n-- #endif\nd").split("\n")
    check("att: preprocess keeps the active branch and line numbers", pp == ["a", "", "", "", "c", "", "d"])
    run("tools/import_att.py", os.path.join(HERE, "fixtures", "att.json"), os.path.join(tmp, "src-att.json"))
    at = json.load(open(os.path.join(tmp, "src-att.json")))
    check("att: quest giver + level + reward + drop", at["qg"]["794"] == ["c3145"] and at["quest"]["794"][2] == 5
          and at["rew"]["4921"] == [794] and at["drop"]["4859"] == [[3183, 0]] and at["spz"]["c3145"] == {"1411": [428, 690]})
    # ---- Forever client tables
    run("tools/import_client.py", os.path.join(HERE, "fixtures", "client"), os.path.join(tmp, "src-client.json"))
    cl = json.load(open(os.path.join(tmp, "src-client.json")))
    check("client: item row (name, quality, reqLevel, ilvl, class)", cl["item"]["5523"][:5] == ["Small Barnacled Clam", 1, 7, 10, 0])
    check("client: item without a search name keeps class/icon", cl["item"]["9000"][4] == 7 and cl["item"]["9000"][7] == 134000)
    check("client: reputation needed for an item (faction, standing)", cl["item"]["99001"][12:14] == [609, 5])
    check("client: flight master", cl["taxi"]["1"][0] == "Northshire Abbey" and cl["taxi"]["1"][1] == 0)
    if exe:
        lj, sj = os.path.join(tmp, "legacy.json"), os.path.join(tmp, "spf.json")
        subprocess.run([exe, "tools/lua/export.lua", "ns", lj, os.path.join(HERE, "fixtures", "extra", "legacy.lua")], check=True, cwd=ROOT)
        subprocess.run([exe, "tools/lua/export.lua", "ns", sj, os.path.join(HERE, "fixtures", "extra", "spf.lua")], check=True, cwd=ROOT)
        run("tools/import_extra.py", "legacy", lj, os.path.join(tmp, "src-legacy.json"))
        run("tools/import_extra.py", "spf", sj, os.path.join(tmp, "src-spf.json"))
        lg = json.load(open(os.path.join(tmp, "src-legacy.json")))
        sp = json.load(open(os.path.join(tmp, "src-spf.json")))
        check("legacy: rewards + exploration outlines", lg["legacy"]["rewards"]["684"] is True and "1411" in lg["explore"])
        check("spf: travel tables", sp["spf"]["TaxiNodes"]["2"]["name"] == "Stormwind" and "Portals" in sp["spf"])
        # client item fields win the vote (Forever source first)
        run("tools/merge.py", "--out", os.path.join(tmp, "m2.json"), "client=" + os.path.join(tmp, "src-client.json"),
            "questie=" + os.path.join(tmp, "src-questie.json"), "att=" + os.path.join(tmp, "src-att.json"),
            "legacy=" + os.path.join(tmp, "src-legacy.json"), "spf=" + os.path.join(tmp, "src-spf.json"))
        m2 = json.load(open(os.path.join(tmp, "m2.json")))
        check("merge: client item row wins and is 14 columns", m2["item"]["5523"][2] == 7 and len(m2["item"]["5523"]) == 14)
        check("merge: pass-through tables", "1" in m2["taxi"] and "rewards" in m2["legacy"] and "TaxiNodes" in m2["spf"])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
