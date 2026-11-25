local l10n = QuestieLoader:ImportModule("l10n")

local itemOverrides = {
    deDE = {
        [5523] = "Kleine seepockenbesetzte Muschel",
    },
}

l10n.itemLookupOverrides = itemOverrides[GetLocale()]
