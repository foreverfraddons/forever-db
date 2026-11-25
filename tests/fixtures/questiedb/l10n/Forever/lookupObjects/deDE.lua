if GetLocale() ~= "deDE" then
    return
end

local l10n = QuestieLoader:ImportModule("l10n")

l10n.objectLookup["deDE"] = loadstring([[return {
}]])
