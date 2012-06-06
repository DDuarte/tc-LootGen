import MySQLdb as db
import sys
import random

# TODO: Implement lootmodes
# TODO: Implement groups with groupid

# npc_entry, quest1, quest2, ... = argv
npc_entry = 36538  # 1009  # 20324  # lich king

# get names


def GetCreatureName(entry, cursor):
    cursor.execute("SELECT `name` FROM `creature_template` WHERE `entry`=%d LIMIT 1" % entry)
    return cursor.fetchone()[0]


def GetItemName(entry, cursor):
    cursor.execute("SELECT `name` FROM `item_template` WHERE `entry`=%d LIMIT 1" % entry)
    return cursor.fetchone()[0]


# table queries

def GetLootTableAux(entry, cursor, rows, references, referencesLinks):
    table = ""
    refEntry = 0
    if not rows:
        table = "creature_loot_template"
    else:
        table = "reference_loot_template"
        refEntry = entry

    query = "SELECT `item`,`ChanceOrQuestChance`,`lootmode`,`groupid`,`mincountOrRef`,`maxcount` FROM `%s` WHERE `entry`=%d;" % (table, entry)
    cursor.execute(query)
    rawData = cursor.fetchall()

    referencesEntries = []

    for row in rawData:
        row = list(row)
        if row[4] < 0:
            referencesEntries.append(abs(row[4]))
            references[abs(row[4])] = [row[1], row[2], row[3], row[5]]

            if refEntry in referencesLinks:
                referencesLinks[refEntry].append(abs(row[4]))
            else:
                referencesLinks[refEntry] = [abs(row[4])]

        else:
            if refEntry in rows:
                rows[refEntry].append(row)
            else:
                rows[refEntry] = [row]

    if not referencesEntries:
        return
    else:
        for ref in referencesEntries:
            GetLootTableAux(ref, cursor, rows, references, referencesLinks)


def GetLootTable(entry, cursor):
    rows = dict()
    references = dict()
    refLinks = dict()
    GetLootTableAux(entry, cursor, rows, references, refLinks)

    references[0] = [100.0, 1, 1, 1]

    for i in range(0, 2):
        ProcessLoot(rows, references, refLinks)
    #print references
    #print refLinks
    #print rows
    return rows

# randomness


def RandCount(minCount, maxCount):
    if (maxCount <= 0):
        print "maxCount is %i, invalid." % maxCount

    return random.randrange(minCount, maxCount + 1)


def RandChance(chance):
    return random.uniform(0, 100) < chance


def ProcessLoot(rows, references, reflinks):
    """Simulates ONE kill; returns a list of items dropped."""
    loot = []

    for ref in references:
        loot.append(ProcessReference(rows[ref], references[ref][0], references[ref][1], references[ref][2]))

    return loot


def SplitIntoGroups(rows):
    """Splits rows of a certain entry into a dictionary, key is groupid"""

    groups = {}

    for row in rows:
        if row[3] in groups:
            groups[row[3]].append(row)
        else:
            groups[row[3]] = [row]

    return groups


def CalculateChanceGroups(groups):
    for group in groups:
        sameChance = True
        for row in groups[group]:
            # assumes that a group will have all chances with 0 or no 0s at all
            if row[1] != 0:
                sameChance = False
                break

        if sameChance:
            chance = 100.0 / len(groups[group])
            for row in groups[group]:
                row[1] = chance

    return groups


def ProcessReference(rows, chance, lootMode, groupId):

    groups = SplitIntoGroups(rows)
    CalculateChanceGroups(groups)

    lootRows = []
    lootRows.append(random.sample(rows, 1))

    loot = []
    for row in lootRows[0]:
        loot.append(row[0])

    return loot

try:
    con = db.connect('localhost', 'root', '', 'world')
    cur = con.cursor()

    rows = GetLootTable(npc_entry, cur)

    print "-- Loot table for %s" % GetCreatureName(npc_entry, cur)
    for key in rows:
        print key
        for row in rows[key]:
            print "\t %s - %s" % (str(row), GetItemName(row[0], cur))

    con.close()

except db.Error, e:
    print "Error %d: %s" % (e.args[0], e.args[1])
    sys.exit(1)
