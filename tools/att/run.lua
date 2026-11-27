-- Runs AllTheThings' own Lua database sources (the WoW Forever build) outside the game,
-- the way ATT's parser does: shared/.main.lua, the rest of shared/, then the Forever
-- files, each already preprocessed (tools/att/preprocess.py). Then walks the categories
-- it built and writes the facts ForeverDB uses as JSON.
--
--   lua tools/att/run.lua <file list> <out.json>
-- The file list has one preprocessed .lua path per line, in load order.

local list, outpath = arg[1], arg[2]
local load_chunk = loadstring or load

-- what the C# parser normally provides
CurrentSubFileName = nil
STUB_GLOBALS = {}
local errors, loaded = {}, 0
local function readfile(p)
  local f = io.open(p, "rb"); if not f then return nil end
  local s = f:read("*a"); f:close(); return s
end

for path in io.lines(list) do
  local src = readfile(path)
  if src then
    if src:sub(1, 3) == "\239\187\191" then src = src:sub(4) end
    STUB_GLOBALS.CurrentFileName = path:match("([^/]+)%.lua$")
    STUB_GLOBALS.CurrentSubFileName = STUB_GLOBALS.CurrentFileName
    local fn, err = load_chunk(src, "@" .. path)
    if not fn then
      errors[#errors + 1] = tostring(err)
    else
      local ok, e = pcall(fn)
      if ok then loaded = loaded + 1 else errors[#errors + 1] = path .. ": " .. tostring(e) end
      -- ATT's strict-global check, but naming the missing global
      setmetatable(_G, { __index = function(_, k)
        if k == "CurrentSubFileName" or STUB_GLOBALS[k] ~= nil then return STUB_GLOBALS[k] end
        error("NON-EXISTENT-GLOBAL: " .. tostring(k), 2)
      end })
    end
  end
end
io.stderr:write(("att: %d files ran, %d errors\n"):format(loaded, #errors))
for k = 1, math.min(#errors, 15) do io.stderr:write("  " .. errors[k]:sub(1, 300) .. "\n") end

-- walk -------------------------------------------------------------------------
local raw_G = getmetatable(_G) and setmetatable(_G, nil) or _G
local ATT = rawget(_G, "AllTheThings") or {}

local out = { npc = {}, obj = {}, quest = {}, item = {}, qg = {}, qe = {}, spz = {}, drop = {}, odrop = {},
              vend = {}, rew = {}, start = {}, cat = {}, files = loaded, errors = #errors }

local function num(v) return type(v) == "number" and v or tonumber(v) end
local function addset(t, k, v)
  local l = t[k]; if not l then l = {}; t[k] = l end
  for _, x in ipairs(l) do if x == v then return end end
  l[#l + 1] = v
end
local function coords(o)
  local res = {}
  local function one(c)
    if type(c) == "table" and num(c[1]) and num(c[2]) and num(c[3]) then res[#res + 1] = { c[1], c[2], c[3] } end
  end
  one(o.coord)
  if type(o.coords) == "table" then for _, c in ipairs(o.coords) do one(c) end end
  return res
end
local function spots(key, o)
  for _, c in ipairs(coords(o)) do
    local m = out.spz[key]; if not m then m = {}; out.spz[key] = m end
    local ui = tostring(math.floor(c[3]))
    local pts = m[ui]; if not pts then pts = {}; m[ui] = pts end
    local x, y = math.floor(c[1] * 10 + 0.5), math.floor(c[2] * 10 + 0.5)
    local dup = false
    for j = 1, #pts, 2 do if math.abs(pts[j] - x) <= 5 and math.abs(pts[j + 1] - y) <= 5 then dup = true; break end end
    if not dup and x >= 0 and x <= 1000 and y >= 0 and y <= 1000 and #pts < 240 then pts[#pts + 1] = x; pts[#pts + 1] = y end
  end
end
local function list(v)
  if type(v) == "number" then return { v } end
  if type(v) == "table" then return v end
  return {}
end

local seen = {}
local function walk(o, ctx)
  if type(o) ~= "table" or seen[o] then return end
  seen[o] = true
  local here = ctx
  local npcID, questID, itemID, objectID = num(rawget(o, "npcID") or rawget(o, "creatureID")), num(rawget(o, "questID")),
    num(rawget(o, "itemID")), num(rawget(o, "objectID"))
  if npcID and npcID > 0 then
    out.npc[npcID] = out.npc[npcID] or { rawget(o, "name") }
    spots("c" .. npcID, o)
    here = { kind = "npc", id = npcID, map = ctx and ctx.map }
  elseif objectID and objectID > 0 then
    out.obj[objectID] = out.obj[objectID] or { rawget(o, "name") }
    spots("o" .. objectID, o)
    here = { kind = "obj", id = objectID, map = ctx and ctx.map }
  elseif questID and questID > 0 and not rawget(o, "itemID") then
    local lvl = num(rawget(o, "lvl"))
    if type(rawget(o, "lvl")) == "table" then lvl = num(o.lvl[1]) end
    out.quest[questID] = out.quest[questID] or { rawget(o, "name"), nil, lvl }
    local cs = coords(o)
    for _, g in ipairs(list(rawget(o, "qgs") or rawget(o, "qg"))) do
      if num(g) and num(g) > 0 then
        addset(out.qg, questID, "c" .. g)
        if #cs > 0 then spots("c" .. g, o) end
      end
    end
    for _, p in ipairs(list(rawget(o, "providers") or (rawget(o, "provider") and { o.provider }))) do
      if type(p) == "table" and p[1] == "o" and num(p[2]) then addset(out.qg, questID, "o" .. p[2]) end
      if type(p) == "table" and p[1] == "i" and num(p[2]) then out.start[p[2]] = out.start[p[2]] or questID end
    end
    for _, g in ipairs(list(rawget(o, "qi"))) do if num(g) then out.start[g] = out.start[g] or nil end end
    here = { kind = "quest", id = questID, map = ctx and ctx.map }
  elseif itemID and itemID > 0 then
    out.item[itemID] = out.item[itemID] or { rawget(o, "name") }
    if ctx then
      if ctx.kind == "npc" then
        if rawget(o, "cost") then addset(out.vend, itemID, ctx.id) else addset(out.drop, itemID, ctx.id) end
      elseif ctx.kind == "obj" then addset(out.odrop, itemID, ctx.id)
      elseif ctx.kind == "quest" then addset(out.rew, itemID, ctx.id) end
    end
    for _, cr in ipairs(list(rawget(o, "crs") or rawget(o, "cr"))) do if num(cr) then addset(out.drop, itemID, num(cr)) end end
    here = ctx   -- an item's children still belong to the container
  else
    local mapID = num(rawget(o, "mapID"))
    if mapID then here = { kind = ctx and ctx.kind, id = ctx and ctx.id, map = mapID } end
    -- headers holding a creature list: items below drop from those creatures
    if not npcID and rawget(o, "crs") then
      for _, cr in ipairs(list(o.crs)) do if num(cr) then here = { kind = "npc", id = num(cr), map = ctx and ctx.map } break end end
    end
  end
  local kids = rawget(o, "groups") or rawget(o, "g")
  if type(kids) == "table" then for _, k in ipairs(kids) do walk(k, here) end end
end

-- never-implemented content and hidden tracking quests are not things players can get or do
local SKIP = { NeverImplemented = true, HiddenQuestTriggers = true, HiddenAchievementTriggers = true,
               HiddenCurrencyTriggers = true, Uncollectible = true, _petDB = true }
for name, cat in pairs(ATT) do
  if type(cat) == "table" and not SKIP[name] then
    local before = 0
    for _ in pairs(out.quest) do before = before + 1 end
    walk(cat, nil)
    for _, k in ipairs(cat) do walk(k, nil) end
    out.cat[#out.cat + 1] = tostring(name)
  end
end

-- items and quests ATT lists as never implemented (e.g. WoW Forever's "Beta Event": epic items low-level
-- creatures dropped on the beta's last day, in the client's Item table but not obtainable in the live game).
-- Anything also found in a live category above is left out of this list.
out.nyi = { item = {}, quest = {} }
local nseen = {}
local function nyiwalk(o)
  if type(o) ~= "table" or nseen[o] then return end
  nseen[o] = true
  local it, q = num(rawget(o, "itemID")), num(rawget(o, "questID"))
  if it and it > 0 and not out.item[it] then out.nyi.item[it] = 1 end
  if q and q > 0 and not rawget(o, "itemID") and not out.quest[q] then out.nyi.quest[q] = 1 end
  local kids = rawget(o, "groups") or rawget(o, "g")
  if type(kids) == "table" then for _, k in ipairs(kids) do nyiwalk(k) end end
end
if type(ATT.NeverImplemented) == "table" then
  nyiwalk(ATT.NeverImplemented)
  for _, k in ipairs(ATT.NeverImplemented) do nyiwalk(k) end
end

-- JSON (same encoder idea as tools/lua/export.lua)
local esc = { ['"'] = '\\"', ['\\'] = '\\\\', ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t' }
local function enc(v, buf)
  local t = type(v)
  if t == "table" then
    buf[#buf + 1] = "{"
    local first = true
    for k, x in pairs(v) do
      local tx = type(x)
      if tx == "table" or tx == "string" or tx == "number" or tx == "boolean" then
        if not first then buf[#buf + 1] = "," end
        first = false
        buf[#buf + 1] = '"' .. tostring(k) .. '":'
        enc(x, buf)
      end
    end
    buf[#buf + 1] = "}"
  elseif t == "string" then
    buf[#buf + 1] = '"' .. v:gsub('[%c"\\]', function(c) return esc[c] or string.format("\\u%04x", c:byte()) end) .. '"'
  elseif t == "number" then
    if v ~= v or v == math.huge or v == -math.huge then buf[#buf + 1] = "null"
    elseif v == math.floor(v) then buf[#buf + 1] = string.format("%d", v)
    else buf[#buf + 1] = string.format("%.6g", v) end
  elseif t == "boolean" then buf[#buf + 1] = tostring(v)
  else buf[#buf + 1] = "null" end
end
local buf = {}
enc(out, buf)
local f = assert(io.open(outpath, "wb")); f:write(table.concat(buf)); f:close()
