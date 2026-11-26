-- Loads addon database files (pfQuest, QuestieDB) outside the game and writes the parts we
-- need as JSON. Works with Lua 5.1 (CI: lua5.1) and Lua 5.3 (texlua).
--
--   lua tools/lua/export.lua pfquest <pfQuest folder> <out.json>
--   lua tools/lua/export.lua questie <QuestieDB folder> <flavor: Forever|Classic> <out.json> [no-generated]
--   (no-generated leaves out QuestieDB's generated delta-base, which its authors built from
--    Wowhead's Forever pages; traces and hand-written Forever fixes are still applied)
--
-- Every table is written as a JSON object with string keys (sparse arrays stay sparse);
-- tools/import_addons.py turns them back into lists where needed.

local load_chunk = loadstring or load
local unpack_ = unpack or table.unpack

local function readfile(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local s = f:read("*a")
  f:close()
  return s
end

-- tables that create sub tables on demand: pfDB["units"]["data"] = ... works on an empty pfDB
local function auto()
  return setmetatable({}, { __index = function(t, k) local v = auto(); rawset(t, k, v); return v end })
end

local function run(path, env)
  local src = readfile(path)
  if not src then return false end
  -- strip a UTF-8 BOM
  if src:sub(1, 3) == "\239\187\191" then src = src:sub(4) end
  local fn, err
  if setfenv then
    fn, err = loadstring(src, "@" .. path)
    if fn then setfenv(fn, env) end
  else
    fn, err = load(src, "@" .. path, "t", env)
  end
  if not fn then error(err) end
  local ok, e = pcall(fn, "QuestieDB", {})
  if not ok then io.stderr:write("warning: " .. path .. ": " .. tostring(e) .. "\n") end
  return ok
end

-- JSON ----------------------------------------------------------------------
local esc = { ['"'] = '\\"', ['\\'] = '\\\\', ['\b'] = '\\b', ['\f'] = '\\f', ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t' }
local function jstr(s)
  return '"' .. s:gsub('[%c"\\]', function(c) return esc[c] or string.format("\\u%04x", c:byte()) end) .. '"'
end

local function encode(v, out, seen)
  local t = type(v)
  if t == "table" then
    if seen[v] then out[#out + 1] = "null"; return end
    seen[v] = true
    out[#out + 1] = "{"
    local first = true
    local keys = {}
    for k in pairs(v) do keys[#keys + 1] = k end
    table.sort(keys, function(a, b)
      local ta, tb = type(a), type(b)
      if ta ~= tb then return ta < tb end
      if ta == "number" or ta == "string" then return a < b end
      return tostring(a) < tostring(b)
    end)
    for _, k in ipairs(keys) do
      local val = v[k]
      local tv = type(val)
      if tv ~= "function" and tv ~= "userdata" and tv ~= "thread" then
        if not first then out[#out + 1] = "," end
        first = false
        local ks
        if type(k) == "number" then
          ks = (k == math.floor(k)) and string.format("%d", k) or string.format("%.14g", k)
        else
          ks = tostring(k)
        end
        out[#out + 1] = jstr(ks)
        out[#out + 1] = ":"
        encode(val, out, seen)
      end
    end
    out[#out + 1] = "}"
    seen[v] = nil
  elseif t == "string" then
    out[#out + 1] = jstr(v)
  elseif t == "number" then
    if v ~= v or v == math.huge or v == -math.huge then out[#out + 1] = "null"
    elseif v == math.floor(v) and math.abs(v) < 2^53 then out[#out + 1] = string.format("%d", v)
    else out[#out + 1] = string.format("%.10g", v) end
  elseif t == "boolean" then
    out[#out + 1] = v and "true" or "false"
  else
    out[#out + 1] = "null"
  end
end

local function write_json(path, v)
  local out = {}
  encode(v, out, {})
  local f = assert(io.open(path, "wb"))
  f:write(table.concat(out))
  f:close()
end

-- pfQuest -------------------------------------------------------------------
local LOCALES = { "enUS", "deDE", "esES", "frFR", "koKR", "ptBR", "ruRU", "zhCN", "zhTW" }

local function pfquest(root, outpath)
  local env = setmetatable({}, { __index = _G })
  env.pfDB = auto()
  env._G = env
  for _, f in ipairs({ "units", "objects", "items", "quests", "refloot", "zones" }) do
    run(root .. "/db/" .. f .. ".lua", env)
  end
  for _, loc in ipairs(LOCALES) do
    for _, f in ipairs({ "units", "objects", "items", "quests" }) do
      run(root .. "/db/" .. loc .. "/" .. f .. ".lua", env)
    end
  end
  local db = env.pfDB
  local res = { units = {}, objects = {}, items = {}, quests = {}, refloot = {}, names = {} }
  for id, u in pairs(rawget(db.units, "data") or {}) do
    res.units[id] = { coords = u.coords, lvl = u.lvl, fac = u.fac }
  end
  for id, o in pairs(rawget(db.objects, "data") or {}) do
    res.objects[id] = { coords = o.coords }
  end
  for id, it in pairs(rawget(db.items, "data") or {}) do
    if next(it) then res.items[id] = it end
  end
  for id, q in pairs(rawget(db.quests, "data") or {}) do
    res.quests[id] = { start = q.start, ["end"] = q["end"], lvl = q.lvl, min = q.min }
  end
  for id, r in pairs(rawget(db.refloot, "data") or {}) do res.refloot[id] = r end
  for _, loc in ipairs(LOCALES) do
    local n = {}
    for _, f in ipairs({ "units", "objects", "items" }) do
      n[f] = rawget(db[f], loc)
    end
    local qs = rawget(db.quests, loc)
    if qs then
      n.quests, n.qtext = {}, {}
      for id, q in pairs(qs) do
        if type(q) == "table" then
          n.quests[id] = q.T
          if q.D or q.O then n.qtext[id] = { d = q.D, o = q.O } end      -- quest dialog: details, objectives
        elseif type(q) == "string" then n.quests[id] = q end
      end
    end
    if next(n) then res.names[loc] = n end
  end
  write_json(outpath, res)
end

-- QuestieDB corrections --------------------------------------------------------
-- QuestieDB keeps WoW Forever's changes (new quests, NPCs, items, zones) as Corrections on top
-- of the raw data. They are applied here in QuestieDB's static order:
--   legacy (inherited Classic fixes) -> generated delta-base -> traces -> authored Forever fixes
-- Field keys: index = replace, index + 1000 = add to a list, index - 1000 = remove from it.
local OFFSET = 1000
local GROUPED = { startedBy = true, finishedBy = true, spawns = true, waypoints = true, objectives = true }

local function deq(a, b)
  if type(a) ~= "table" or type(b) ~= "table" then return a == b end
  for k, v in pairs(a) do if not deq(v, b[k]) then return false end end
  for k in pairs(b) do if a[k] == nil then return false end end
  return true
end

local function list_add(cur, add)
  cur = type(cur) == "table" and cur or {}
  for _, v in ipairs(add) do
    local found = false
    for _, e in ipairs(cur) do if deq(e, v) then found = true; break end end
    if not found then cur[#cur + 1] = v end
  end
  return cur
end

local function list_remove(cur, rem)
  if type(cur) ~= "table" then return cur end
  local out = {}
  for _, e in ipairs(cur) do
    local drop = false
    for _, v in ipairs(rem) do if deq(e, v) then drop = true; break end end
    if not drop then out[#out + 1] = e end
  end
  return out
end

local function enum_table(t)
  -- unknown constants read as 0 so arithmetic on masks/flags never fails
  return setmetatable(t or {}, { __index = function(_, k) return 0 end })
end

function apply_corrections(root, env, modules, QDB, tables, skip_generated)
  local ns = { Enum = {} }
  local Enum = ns.Enum
  local edir = root .. "/src/corrections/enum/"
  for _, f in ipairs({ "expansions", "zones", "quests", "factions", "items", "professions", "phases", "waypoints", "icons" }) do
    local src = readfile(edir .. f .. ".lua")
    if src then
      local fn = assert(load_chunk(src, "@" .. f))
      if setfenv then setfenv(fn, env) end
      local ok, e = pcall(fn, "QuestieDB", ns)
      if not ok then io.stderr:write("warning: enum " .. f .. ": " .. tostring(e) .. "\n") end
    end
  end
  local F = (Enum.byExpansion or {}).Forever or {}
  -- keys with _add / _remove aliases
  local function aliased(k)
    local t = {}
    for name, idx in pairs(k or {}) do
      t[name] = idx; t[name .. "_add"] = idx + OFFSET; t[name .. "_remove"] = idx - OFFSET
    end
    return t
  end
  local Q = modules.QuestieDB or {}
  modules.QuestieDB = Q
  local keysets = { Npc = Q.npcKeys, Object = Q.objectKeys, Item = Q.itemKeys, Quest = Q.questKeys }
  Q.npcKeys, Q.objectKeys, Q.itemKeys, Q.questKeys = aliased(Q.npcKeys), aliased(Q.objectKeys), aliased(Q.itemKeys), aliased(Q.questKeys)
  Q.raceKeys = enum_table(F.raceKeys or F.raceIDs)
  Q.classKeys = enum_table(F.classKeys or F.classIDs)
  Q.npcFlags = enum_table(F.npcFlags)
  for _, k in ipairs({ "sortKeys", "specialFlags", "factionIDs", "waypointPresets", "questFlags", "itemClasses", "dropCorrectionKeys" }) do
    Q[k] = enum_table(Enum[k])
  end
  setmetatable(Q, { __index = function(t, k) local v = enum_table({}); rawset(t, k, v); return v end })
  local Z = modules.ZoneDB or { private = {} }
  modules.ZoneDB = Z
  Z.zoneIDs = enum_table(Enum.zoneIDs)
  local function mod(name, fields)
    local m = modules[name] or { private = {} }
    for k, v in pairs(fields) do m[k] = v end
    modules[name] = m
    return m
  end
  mod("Phasing", { phases = enum_table(Enum.phases) })
  mod("QuestieProfessions", { professionKeys = enum_table(Enum.professionKeys),
    specializationKeys = enum_table(Enum.specializationKeys), rankNames = enum_table(Enum.rankNames) })
  local QC = mod("QuestieCorrections", {})
  setmetatable(QC, { __index = function(t, k) local v = {}; rawset(t, k, v); return v end })
  mod("l10n", {})
  setmetatable(modules.l10n, { __call = function(_, s) return s end })
  env.Questie = setmetatable({}, { __index = function(t, k) local v = enum_table({}); rawset(t, k, v); return v end })
  env.LibQuestieDB = ns
  env.E = setmetatable({}, { __index = function(t, k) local v = setmetatable({}, getmetatable(t)); rawset(t, k, v); return v end })

  local inverse = {}
  for kind, ks in pairs(keysets) do
    inverse[kind] = {}
    for name, idx in pairs(ks or {}) do inverse[kind][idx] = name end
  end

  local function apply(kind, corr, stats)
    local db = tables[kind]
    local inv = inverse[kind]
    for id, fields in pairs(corr) do
      if type(id) == "number" and type(fields) == "table" then
        local row = db[id]
        if row == nil then row = {}; db[id] = row; stats.created = stats.created + 1 end
        stats.rows = stats.rows + 1
        for key, val in pairs(fields) do
          if type(key) == "number" then
            if key > 0 and key < OFFSET then
              if type(val) == "table" and next(val) == nil then row[key] = nil else row[key] = val end
            else
              local field = key >= OFFSET and key - OFFSET or key + OFFSET
              local adding = key >= OFFSET
              local name = inv[field]
              if type(val) == "table" then
                if GROUPED[name] then
                  local cur = type(row[field]) == "table" and row[field] or {}
                  for g, items in pairs(val) do
                    if type(items) == "table" then
                      cur[g] = adding and list_add(cur[g], items) or list_remove(cur[g], items)
                    end
                  end
                  row[field] = cur
                else
                  row[field] = adding and list_add(row[field], val) or list_remove(row[field], val)
                end
              end
            end
          end
        end
      end
    end
  end

  local dir = root .. "/src/corrections/Forever/"
  local order = {
    { "legacy/classicNPCFixes", "Npc" }, { "legacy/classicObjectFixes", "Object" },
    { "legacy/classicItemFixes", "Item" }, { "legacy/classicQuestFixes", "Quest" },
    { "legacy/classicQuestReputationFixes", "Quest" }, { "legacy/itemStartFixes", "Item" },
    { "generated/foreverBaseNpc", "Npc" }, { "generated/foreverBaseObject", "Object" },
    { "generated/foreverBaseItem", "Item" }, { "generated/foreverBaseQuest", "Quest" },
    { "traces/foreverNpcTraces", "Npc" }, { "traces/foreverObjectTraces", "Object" },
    { "traces/foreverItemTraces", "Item" }, { "traces/foreverQuestTraces", "Quest" },
    { "traces/foreverQuestRelationTraces", "Quest" },
    { "foreverNPCFixes", "Npc" }, { "foreverObjectFixes", "Object" },
    { "foreverItemFixes", "Item" }, { "foreverQuestFixes", "Quest" },
  }
  local report = {}
  for _, step in ipairs(order) do
    if skip_generated and step[1]:match("^generated/") then
      report[#report + 1] = { file = step[1], skipped = true }
    else
    local before = {}
    for name in pairs(modules) do before[name] = true end
    local stats = { file = step[1], rows = 0, created = 0, providers = 0 }
    if run(dir .. step[1] .. ".lua", env) then
      for name, m in pairs(modules) do
        if not before[name] and type(m) == "table" then
          -- a provider module: every function returning a correction table
          for fname, fn in pairs(m) do
            if type(fn) == "function" and (fname == "Load" or fname == "LoadAutomaticQuestStarts") then
              local ok, corr = pcall(fn, m, {
                questKeys = Q.questKeys, raceKeys = Q.raceKeys, classKeys = Q.classKeys, sortKeys = Q.sortKeys,
                npcKeys = Q.npcKeys, objectKeys = Q.objectKeys, itemKeys = Q.itemKeys }, Z)
              if ok and type(corr) == "table" then
                stats.providers = stats.providers + 1
                local okA, err = pcall(apply, step[2], corr, stats)
                if not okA then io.stderr:write("warning: applying " .. step[1] .. "." .. fname .. ": " .. tostring(err) .. "\n") end
              elseif not ok then
                io.stderr:write("warning: " .. step[1] .. "." .. fname .. ": " .. tostring(corr) .. "\n")
              end
            end
          end
        end
      end
    end
    report[#report + 1] = stats
    end
  end
  return report
end

-- QuestieDB ------------------------------------------------------------------
local function questie(root, flavor, outpath, skip_generated)
  local modules = {}
  local env = setmetatable({}, { __index = _G })
  env._G = env
  env.QuestieLoader = { ImportModule = function(_, name)
    if not modules[name] then modules[name] = { private = {} } end
    return modules[name]
  end, CreateModule = function(_, name)
    if not modules[name] then modules[name] = { private = {} } end
    return modules[name]
  end }
  env.UnitFactionGroup = function() return "Horde" end
  local low = flavor:lower()
  local base = root .. "/data/" .. flavor .. "/" .. low
  for _, f in ipairs({ "NpcDB", "ObjectDB", "ItemDB", "QuestDB" }) do
    run(base .. f .. ".lua", env)
  end
  local zdir = root .. "/support/" .. (flavor == "Forever" and "Forever/Zones" or "Zones")
  run(root .. "/support/Zones/uiMapIdToAreaId.lua", env)
  run(root .. "/support/Zones/areaIdToUiMapId.lua", env)
  local zbase = modules.ZoneDB and modules.ZoneDB.private or {}
  local classicU2A, classicA2U = zbase.uiMapIdToAreaIdOverride, zbase.areaIdToUiMapIdOverride
  if flavor == "Forever" then
    modules.ZoneDB = nil
    run(zdir .. "/uiMapIdToAreaId.lua", env)
    run(zdir .. "/areaIdToUiMapId.lua", env)
  end
  local z = modules.ZoneDB and modules.ZoneDB.private or {}
  local QDB = modules.QuestieDB or {}
  local function data(s)
    if type(s) == "string" then
      local fn = assert(load_chunk(s))
      return fn()
    end
    return s
  end
  local function keys(k)
    local r = {}
    for name, idx in pairs(k or {}) do r[name] = idx end
    return r
  end
  local npcData, objData, itemData, questData = data(QDB.npcData), data(QDB.objectData), data(QDB.itemData), data(QDB.questData)
  local applied = {}
  if flavor == "Forever" then
    applied = apply_corrections(root, env, modules, QDB, {
      Npc = npcData, Object = objData, Item = itemData, Quest = questData }, skip_generated)
  end
  local zids = {}
  for name, id in pairs((modules.ZoneDB or {}).zoneIDs or {}) do zids[name] = id end
  local res = {
    corrections = applied,
    zoneIDs = zids,
    npcKeys = keys(QDB.npcKeys), objectKeys = keys(QDB.objectKeys),
    itemKeys = keys(QDB.itemKeys), questKeys = keys(QDB.questKeys),
    npc = npcData, obj = objData, item = itemData, quest = questData,
    uiMapToArea = data(z.uiMapIdToAreaIdOverride or z.uiMapIdToAreaId),
    areaToUiMap = data(z.areaIdToUiMapIdOverride or z.areaIdToUiMapId),
    classicUiMapToArea = data(classicU2A), classicAreaToUiMap = data(classicA2U),
  }
  write_json(outpath, res)
end

-- plain addon data files (LegacyForever, Shortest Path Forever ...): each file runs as
-- `local _, ns = ...` and fills ns; the whole ns is written out
local function nsdump(outpath, files)
  local ns = {}
  local env = setmetatable({}, { __index = _G })
  env._G = env
  for _, f in ipairs(files) do
    local src = readfile(f)
    if src then
      local fn, err
      if setfenv then fn, err = loadstring(src, "@" .. f); if fn then setfenv(fn, env) end
      else fn, err = load(src, "@" .. f, "t", env) end
      if fn then
        local ok, e = pcall(fn, "ForeverDBExport", ns)
        if not ok then io.stderr:write("warning: " .. f .. ": " .. tostring(e) .. "\n") end
      else io.stderr:write("warning: " .. f .. ": " .. tostring(err) .. "\n") end
    end
  end
  write_json(outpath, ns)
end

-- ------------------------------------------------------------------ QuestieDB translations
-- l10n/<flavor>/lookup{Quests,Npcs,Items,Objects}/<locale>.lua, then l10n/<flavor>/traces/... on top (per field,
-- trace entries win - QuestieDB's own rule). Out: {locale: {quest = {id: {title, {objective lines}}},
-- npc = {id: {name, subname}}, item = {id: name}, obj = {id: name}}}
local L10N = { Quests = { "questLookup", "quest" }, Npcs = { "npcNameLookup", "npc" },
               Items = { "itemLookup", "item" }, Objects = { "objectLookup", "obj" } }
local LOCALES = { "deDE", "esES", "esMX", "frFR", "itIT", "koKR", "ptBR", "ruRU", "zhCN", "zhTW" }
local function l10n(dir, flavor, outpath)
  local out = {}
  local function lookup(path, loc, field)
    local l10nmod = { [field] = {} }
    local env = {
      GetLocale = function() return loc end,
      QuestieLoader = { ImportModule = function() return l10nmod end },
      loadstring = function(s) if setfenv then return loadstring(s) end return load(s) end,
    }
    local ok, err = pcall(run, path, env)
    if not ok then io.stderr:write("warning: " .. path .. ": " .. tostring(err) .. "\n") end
    local v = l10nmod[field][loc]
    if type(v) == "function" then v = v() end           -- (the files keep them as loadstring(...) to run later)
    return type(v) == "table" and v or nil
  end
  for kind, f in pairs(L10N) do
    for _, loc in ipairs(LOCALES) do
      local base = lookup(dir .. "/l10n/" .. flavor .. "/lookup" .. kind .. "/" .. loc .. ".lua", loc, f[1]) or {}
      local tr = lookup(dir .. "/l10n/" .. flavor .. "/traces/lookup" .. kind .. "/" .. loc .. ".lua", loc, f[1]) or {}
      local merged = {}
      for id, v in pairs(base) do merged[id] = v end
      for id, v in pairs(tr) do
        local b = merged[id]
        if type(v) == "table" and type(b) == "table" then           -- per field
          local m = {}
          for i = 1, math.max(#v, #b, 2) do if v[i] ~= nil then m[i] = v[i] else m[i] = b[i] end end
          merged[id] = m
        else
          merged[id] = v
        end
      end
      if next(merged) then
        out[loc] = out[loc] or {}
        out[loc][f[2]] = merged
      end
    end
  end
  write_json(outpath, out)
end

local mode = arg[1]
if mode == "ns" then
  local files = {}
  for k = 3, #arg do files[#files + 1] = arg[k] end
  nsdump(arg[2], files)
elseif mode == "pfquest" then
  pfquest(arg[2], arg[3])
elseif mode == "l10n" then
  l10n(arg[2], arg[3], arg[4])
elseif mode == "questie" then
  questie(arg[2], arg[3], arg[4], arg[5] == "no-generated")
else
  io.stderr:write("usage: export.lua pfquest <dir> <out> | questie <dir> <flavor> <out>\n")
  os.exit(2)
end
