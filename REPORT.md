# ForeverDB merge report

Sources in priority order: client, questie, att, vmangos, cmangos, pfquest, legacy, spf, terrain (Forever sources win any field they have; otherwise the most common value wins).

## Entries per source

| Source | npc | obj | item | quest |
|---|---|---|---|---|
| client | 0 (0 only here) | 0 (0 only here) | 32011 (5342 only here) | 0 (0 only here) |
| questie | 15565 (5192 only here) | 7480 (752 only here) | 24227 (246 only here) | 6084 (192 only here) |
| att | 1722 (0 only here) | 240 (2 only here) | 14345 (3 only here) | 5166 (66 only here) |
| vmangos | 10381 (0 only here) | 9368 (507 only here) | 17707 (0 only here) | 4433 (0 only here) |
| cmangos | 10384 (0 only here) | 10743 (650 only here) | 17718 (0 only here) | 4245 (0 only here) |
| pfquest | 10385 (4 only here) | 8985 (19 only here) | 17712 (0 only here) | 4433 (0 only here) |
| legacy | 0 (0 only here) | 0 (0 only here) | 0 (0 only here) | 0 (0 only here) |
| spf | 0 (0 only here) | 0 (0 only here) | 0 (0 only here) | 0 (0 only here) |
| terrain | 0 (0 only here) | 0 (0 only here) | 0 (0 only here) | 0 (0 only here) |

Merged: npc 15831, obj 12111, item 32280, quest 6331, qg 5678, qe 6022, vend 3933, rew 3202, drop 11011, odrop 3762, idrop 2750, qx 6084, nfac 7575, dng 232, ind 154, taxi 101, umap 60, umaa 61, area 1404, ach 493, ctree 6797, crit 3407, mtree 2883, hol 23, sla 7390, ieff 9026, seff 3931, tset 9, bpet 122, ctun 103, wmo 1081, legacy 5, lcrit 6, explore 43, spf 29, zbord 58, abord 833, agrid 6, qrw 4132, ptl 0, qwk 0, qgreet 200, start 823, world 3136, spw 15877, spz 16533, qtext 6036

Forever-only entries (only the Forever source has them): npc 5192, obj 754, item 5591, quest 258

## Disagreements

| Field | Entries where sources disagree |
|---|---|
| item.reqLevel | 685 |
| npc.minLv | 642 |
| npc.maxLv | 629 |
| quest.minLevel | 289 |
| item.quality | 248 |
| quest.level | 130 |
| item.name | 85 |
| obj.name | 41 |
| quest.title | 33 |
| npc.rank | 18 |
| npc.name | 12 |
| npc.sub | 11 |
| start | 1 |

Drop rates compared across 2+ sources: 231978, differing more than 3x: 6776

## Examples

**item.reqLevel**
- 872: {"client": 18, "questie": 18, "vmangos": 16, "cmangos": 16} -> chose 18
- 1076: {"questie": 21, "vmangos": 20, "cmangos": 20} -> chose 21
- 1082: {"questie": 5, "vmangos": 10, "cmangos": 10} -> chose 5
- 1187: {"questie": 27, "vmangos": 20, "cmangos": 20} -> chose 27
- 1214: {"client": 14, "questie": 14, "vmangos": 12, "cmangos": 12} -> chose 14
- 1215: {"client": 19, "questie": 19, "vmangos": 17, "cmangos": 17} -> chose 19
- 1314: {"client": 16, "questie": 16, "vmangos": 15, "cmangos": 15} -> chose 16
- 1355: {"client": 12, "questie": 12, "vmangos": 10, "cmangos": 10} -> chose 12

**npc.minLv**
- 1: {"questie": 1, "vmangos": 63, "cmangos": 1, "pfquest": 63} -> chose 1
- 2: {"questie": 1, "vmangos": 63, "cmangos": 1, "pfquest": 63} -> chose 1
- 43: {"questie": 7, "vmangos": 8, "cmangos": 8, "pfquest": 8} -> chose 7
- 72: {"vmangos": 1, "cmangos": 20, "pfquest": 1} -> chose 1
- 89: {"questie": 51, "vmangos": 50, "cmangos": 50, "pfquest": 50} -> chose 51
- 167: {"questie": 15, "vmangos": 13, "cmangos": 13, "pfquest": 13} -> chose 15
- 219: {"questie": 45, "vmangos": 20, "cmangos": 20, "pfquest": 20} -> chose 45
- 226: {"questie": 28, "vmangos": 30, "cmangos": 30, "pfquest": 30} -> chose 28

**npc.maxLv**
- 1: {"questie": 1, "vmangos": 63, "cmangos": 1, "pfquest": 63} -> chose 1
- 2: {"questie": 1, "vmangos": 63, "cmangos": 1, "pfquest": 63} -> chose 1
- 72: {"vmangos": 1, "cmangos": 20, "pfquest": 1} -> chose 1
- 89: {"questie": 50, "vmangos": 50, "cmangos": 60, "pfquest": 50} -> chose 50
- 125: {"questie": 19, "vmangos": 20, "cmangos": 20, "pfquest": 20} -> chose 19
- 129: {"questie": 63, "vmangos": 50, "cmangos": 63, "pfquest": 50} -> chose 63
- 167: {"questie": 15, "vmangos": 13, "cmangos": 13, "pfquest": 13} -> chose 15
- 219: {"questie": 45, "vmangos": 20, "cmangos": 20, "pfquest": 20} -> chose 45

**quest.minLevel**
- 17: {"questie": 38, "att": 38, "vmangos": 38, "cmangos": 36, "pfquest": 38} -> chose 38
- 117: {"questie": 10, "vmangos": 0, "cmangos": 0} -> chose 10
- 172: {"questie": 10, "att": 10, "vmangos": 10, "cmangos": 10, "pfquest": 26} -> chose 10
- 299: {"questie": 22, "att": 22, "vmangos": 25, "cmangos": 25, "pfquest": 25} -> chose 22
- 303: {"questie": 22, "att": 25, "vmangos": 25, "cmangos": 25, "pfquest": 25} -> chose 22
- 377: {"questie": 22, "att": 24, "vmangos": 22, "cmangos": 22, "pfquest": 22} -> chose 22
- 378: {"questie": 22, "att": 25, "vmangos": 22, "cmangos": 22, "pfquest": 22} -> chose 22
- 618: {"questie": 40, "vmangos": 37, "cmangos": 40, "pfquest": 37} -> chose 40

**item.quality**
- 763: {"client": 2, "vmangos": 1, "cmangos": 1} -> chose 2
- 872: {"client": 3, "vmangos": 2, "cmangos": 2} -> chose 3
- 876: {"client": 1, "vmangos": 0, "cmangos": 0} -> chose 1
- 1264: {"client": 3, "vmangos": 2, "cmangos": 2} -> chose 3
- 1604: {"client": 3, "vmangos": 2, "cmangos": 2} -> chose 3
- 1913: {"client": 2, "vmangos": 1, "cmangos": 1} -> chose 2
- 1929: {"client": 3, "vmangos": 2, "cmangos": 2} -> chose 3
- 1934: {"client": 3, "vmangos": 2, "cmangos": 2} -> chose 3

**quest.level**
- 172: {"questie": 60, "vmangos": 60, "cmangos": 60, "pfquest": 29} -> chose 60
- 299: {"questie": 27, "vmangos": 28, "cmangos": 28, "pfquest": 28} -> chose 27
- 349: {"questie": 45, "vmangos": 35, "cmangos": 45, "pfquest": 35} -> chose 45
- 472: {"questie": 30, "vmangos": 25, "cmangos": 25, "pfquest": 25} -> chose 30
- 490: {"questie": 8, "vmangos": 7, "pfquest": 7} -> chose 8
- 544: {"questie": 33, "vmangos": 34, "cmangos": 34, "pfquest": 34} -> chose 33
- 556: {"questie": 33, "vmangos": 32, "cmangos": 32, "pfquest": 32} -> chose 33
- 557: {"questie": 33, "vmangos": 34, "cmangos": 34, "pfquest": 34} -> chose 33

**item.name**
- 1262: {"questie": "Keg of Thunderbrew", "vmangos": "Keg of Thunderbrew Lager", "cmangos": "Keg of Thunderbrew Lager", "pfquest": "Keg of Thunderbrew Lager"} -> chose 'Keg of Thunderbrew'
- 2315: {"client": "Gray Leather Boots", "questie": "Dark Leather Boots", "vmangos": "Dark Leather Boots", "cmangos": "Dark Leather Boots", "pfquest": "Dark Leather Boots"} -> chose 'Gray Leather Boots'
- 2550: {"client": "Monster - Bow, Short", "questie": "Monster - Bow, Brown", "vmangos": "Monster - Bow, Short", "cmangos": "Monster - Bow, Brown", "pfquest": "Monster - Bow, Short"} -> chose 'Monster - Bow, Short'
- 2695: {"client": "Monster - Mace, Spiked Club", "questie": "Monster - Mace, Board with Nail Club", "vmangos": "Monster - Mace, Spiked Club", "cmangos": "Monster - Mace, Board with Nail Club", "pfquest": "Monster - Mace, Spiked Club"} -> chose 'Monster - Mace, Spiked Club'
- 3034: {"questie": "Glyphed Breastplate", "vmangos": "BKP \"Impact\" Shot", "cmangos": "Deprecated BKP \"Impact\" Shot", "pfquest": "BKP \"Impact\" Shot"} -> chose 'Glyphed Breastplate'
- 3148: {"questie": "Work Shirt", "vmangos": "Deprecated Work Shirt", "cmangos": "Work Shirt", "pfquest": "Work Shirt"} -> chose 'Work Shirt'
- 3825: {"questie": "Elixir of Lesser Fortitude", "vmangos": "Elixir of Fortitude", "cmangos": "Elixir of Fortitude", "pfquest": "Elixir of Fortitude"} -> chose 'Elixir of Lesser Fortitude'
- 3830: {"questie": "Recipe: Elixir of Lesser Fortitude", "vmangos": "Recipe: Elixir of Fortitude", "cmangos": "Recipe: Elixir of Fortitude", "pfquest": "Recipe: Elixir of Fortitude"} -> chose 'Recipe: Elixir of Lesser Fortitude'

**obj.name**
- 12653: {"vmangos": "Ghost Saber Trap", "cmangos": "Cat Figurine Trap"} -> chose 'Ghost Saber Trap'
- 19538: {"questie": "World Tree Portal", "vmangos": "Small Wisp", "cmangos": "World Tree Portal", "pfquest": "Small Wisp"} -> chose 'World Tree Portal'
- 19539: {"questie": "Grinding Wheel", "vmangos": "Medium Wisp", "cmangos": "Grinding Wheel", "pfquest": "Medium Wisp"} -> chose 'Grinding Wheel'
- 19540: {"questie": "Orc Manacle", "vmangos": "Large Wisp", "cmangos": "Orc Manacle", "pfquest": "Large Wisp"} -> chose 'Orc Manacle'
- 19550: {"questie": "Starbreeze Village Moonwell", "vmangos": "Starbreeze Moonwell", "cmangos": "Starbreeze Village Moonwell", "pfquest": "Starbreeze Moonwell"} -> chose 'Starbreeze Village Moonwell'
- 20917: {"questie": "Blue aura. short column. scale 3", "vmangos": "Blue aura, short column, scale 3", "cmangos": "Blue aura. short column. scale 3", "pfquest": "Blue aura, short column, scale 3"} -> chose 'Blue aura. short column. scale 3'
- 48404: {"questie": "Campfire", "vmangos": "Dwarven Campfire", "cmangos": "Campfire", "pfquest": "Campfire"} -> chose 'Campfire'
- 152093: {"questie": "Talon Den", "vmangos": "Kadrak Flag Spell Focus (DND)", "cmangos": "Talon Den", "pfquest": "Talon Den"} -> chose 'Talon Den'

**quest.title**
- 117: {"questie": "Thunderbrew", "vmangos": "Thunderbrew", "cmangos": "Thunderbrew Lager", "pfquest": "Thunderbrew"} -> chose 'Thunderbrew'
- 172: {"questie": "Children's Week", "vmangos": "Children's Week", "cmangos": "Children's Week", "pfquest": "Ambushed In The Forest"} -> chose "Children's Week"
- 490: {"questie": "Bounty: Gnarlpine Furbolg", "vmangos": "<UNUSED>", "pfquest": "<UNUSED>"} -> chose 'Bounty: Gnarlpine Furbolg'
- 636: {"questie": "Legends of the Earth", "vmangos": "Legends of the Earth <NYI>", "cmangos": "Legends of the Earth", "pfquest": "Legends of the Earth <NYI>"} -> chose 'Legends of the Earth'
- 684: {"questie": "WANTED: Marez Cowl", "vmangos": "Wanted!  Marez Cowl", "cmangos": "Wanted!  Marez Cowl", "pfquest": "Wanted!  Marez Cowl"} -> chose 'WANTED: Marez Cowl'
- 685: {"questie": "WANTED: Otto and Falconcrest", "vmangos": "Wanted!  Otto and Falconcrest", "cmangos": "Wanted!  Otto and Falconcrest", "pfquest": "Wanted!  Otto and Falconcrest"} -> chose 'WANTED: Otto and Falconcrest'
- 1658: {"questie": "Crashing the Wickerman Festival", "vmangos": "Crashing the Wickerman Festival", "cmangos": "Crashing the Wickerman Festival (PvP)", "pfquest": "Crashing the Wickerman Festival"} -> chose 'Crashing the Wickerman Festival'
- 4002: {"questie": "The Eastern Kingdom", "vmangos": "The Eastern Kingdoms", "cmangos": "The Eastern Kingdom", "pfquest": "The Eastern Kingdoms"} -> chose 'The Eastern Kingdom'

**npc.rank**
- 219: {"questie": 1, "vmangos": 0, "cmangos": 0} -> chose 1
- 471: {"questie": 0, "vmangos": 4, "cmangos": 4} -> chose 0
- 639: {"questie": 0, "vmangos": 2, "cmangos": 2} -> chose 0
- 1748: {"questie": 0, "vmangos": 3, "cmangos": 3} -> chose 0
- 4438: {"questie": 0, "vmangos": 2, "cmangos": 2} -> chose 0
- 7846: {"questie": 0, "vmangos": 3, "cmangos": 3} -> chose 0
- 9024: {"questie": 0, "vmangos": 2, "cmangos": 2} -> chose 0
- 9025: {"questie": 0, "vmangos": 2, "cmangos": 2} -> chose 0

**npc.name**
- 219: {"questie": "Groundskeeper Lomar", "vmangos": "[UNUSED] Logan Mar", "cmangos": "[UNUSED] Logan Mar", "pfquest": "[UNUSED] Logan Mar"} -> chose 'Groundskeeper Lomar'
- 1233: {"vmangos": "Shaethis Darkoak", "cmangos": "[UNUSED] Shaethis Darkoak", "pfquest": "Shaethis Darkoak"} -> chose 'Shaethis Darkoak'
- 2614: {"questie": "Argent Medic", "vmangos": "[UNUSED] Stromgarde Horseman", "cmangos": "[UNUSED] Stromgarde Horseman", "pfquest": "[UNUSED] Stromgarde Horseman"} -> chose 'Argent Medic'
- 2756: {"questie": "Grund Drokda", "vmangos": "UNUSED Grund Drokda", "cmangos": "UNUSED Grund Drokda", "pfquest": "UNUSED Grund Drokda"} -> chose 'Grund Drokda'
- 7383: {"questie": "Black Tabby", "vmangos": "Black Tabby", "cmangos": "Black Tabby", "pfquest": "Maine Coon"} -> chose 'Black Tabby'
- 10776: {"questie": "Pip Quickwit", "vmangos": "Finkle Einhorn", "cmangos": "Finkle Einhorn", "pfquest": "Finkle Einhorn"} -> chose 'Pip Quickwit'
- 11058: {"questie": "Ezra Grimm", "vmangos": "Fras Siabi", "cmangos": "Fras Siabi", "pfquest": "Fras Siabi"} -> chose 'Ezra Grimm'
- 14242: {"questie": "Sulhasa", "vmangos": "[UNUSED] Sulhasa", "cmangos": "[UNUSED] Sulhasa", "pfquest": "Sulhasa"} -> chose 'Sulhasa'

**npc.sub**
- 3690: {"questie": "Kodo Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Kodo Riding Instructor"} -> chose 'Kodo Riding Instructor'
- 4732: {"questie": "Horse Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Horse Riding Instructor"} -> chose 'Horse Riding Instructor'
- 4752: {"questie": "Wolf Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Wolf Riding Instructor"} -> chose 'Wolf Riding Instructor'
- 4753: {"questie": "Nightsaber Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Nightsaber Riding Instructor"} -> chose 'Nightsaber Riding Instructor'
- 4772: {"questie": "Ram Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Ram Riding Instructor"} -> chose 'Ram Riding Instructor'
- 4773: {"questie": "Undead Horse Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Undead Horse Riding Instructor"} -> chose 'Undead Horse Riding Instructor'
- 5492: {"questie": "Church of the Holy Light", "vmangos": "Paladin Trainer", "cmangos": "Paladin Trainer"} -> chose 'Church of the Holy Light'
- 6777: {"questie": "Specialty Engineer", "vmangos": "Speciality Engineer", "cmangos": "Speciality Engineer"} -> chose 'Specialty Engineer'

**start**
- 11463: {"questie": 4281, "att": 4135, "vmangos": 4281, "cmangos": 4281, "pfquest": 4281} -> chose None

