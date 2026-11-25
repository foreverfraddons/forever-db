if GetLocale() ~= "deDE" then
    return
end

local l10n = QuestieLoader:ImportModule("l10n")

l10n.npcNameLookup["deDE"] = loadstring([[return {
[100] = {"Murlocplünderer",nil},
[101] = {"Kobold",nil},
[99999] = {"Himmelsgeborener Späher","Kundschafter"},
}]])
