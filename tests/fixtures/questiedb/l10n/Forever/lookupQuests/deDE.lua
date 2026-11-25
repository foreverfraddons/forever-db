if GetLocale() ~= "deDE" then
    return
end

local l10n = QuestieLoader:ImportModule("l10n")

l10n.questLookup["deDE"] = loadstring([[return {
[50001] = {"Muschelsuche", {"Sammelt 5 Muscheln.", "Kehrt zurück."}},
}]])
