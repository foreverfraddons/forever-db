if GetLocale() ~= "deDE" then
    return
end

local l10n = QuestieLoader:ImportModule("l10n")

l10n.itemLookup["deDE"] = loadstring([[return {
[5523] = "Kleine verkrustete Muschel",
}]])
