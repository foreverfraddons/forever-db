if GetLocale() ~= "deDE" then
    return
end

local l10n = QuestieLoader:ImportModule("l10n")

l10n.npcNameLookup["deDE"] = loadstring([[return {
[101] = {"Koboldtunnelgräber",nil},
}]])
