import MySQLdb as db
import sys
import random

# TODO: Implement lootmodes
# TODO: Implement groups with groupid

# npc_entry, quest1, quest2, ... = argv
npc_entry = 36597  # lich king

with_quest_items = False


### random helpers ###


def RandCount(minCount, maxCount):
    """Random value between minCount and maxCount (inclusive)"""
    if (maxCount <= 0 or maxCount > minCount):
        print "maxCount is %i, invalid." % maxCount

    return random.randrange(minCount, maxCount + 1)


def RandChance(chance):
    """There's a chance% of this returning True"""

    if with_quest_items:
        return random.uniform(0, 100) < abs(chance)
    else:
        return random.uniform(0, 100) < chance


### get names ###


def GetCreatureName(entry, cursor):
    """ Returns the name of a creature"""
    cursor.execute("SELECT `name` FROM `creature_template` WHERE `entry`=%d LIMIT 1" % entry)
    return cursor.fetchone()[0]


def GetItemName(entry, cursor):
    """Returns the name of an item"""
    cursor.execute("SELECT `name` FROM `item_template` WHERE `entry`=%d LIMIT 1" % entry)
    return cursor.fetchone()[0]


### loot processing ###

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
    """Calculates chances if a group has all items with chance = 0"""
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


def ProcessReference(rows, lootMode, groupId):

    groups = SplitIntoGroups(rows)
    CalculateChanceGroups(groups)

    loot = []

    for group in groups:
        for row in groups[group]:
            if RandChance(row[1]):
                for i in range(0, RandCount(row[4], row[5])):
                    loot.append(row[0])

    return loot


def ProcessLoot(rows, references, reflinks):
    """Simulates ONE kill; returns a list of items dropped."""
    loot = []

    for ref in references:
        if RandChance(references[ref][0]):  # ChanceOrQuestChance for references,
                                            # there's a certain chance of not processing references at all
            for i in range(0, references[ref][3]):  # maxcount for references, process reference X times
                newLoot = ProcessReference(rows[ref], references[ref][1], references[ref][2])
                if newLoot:
                    for l in newLoot:
                        loot.append(l)

    return loot


def GetLootTableAux(entry, cursor, rows, references, referencesLinks):
    """Auxiliar method of GetLootTable"""
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
    """Gets the full loot table from DB, including references"""
    rows = dict()
    references = dict()
    refLinks = dict()
    GetLootTableAux(entry, cursor, rows, references, refLinks)

    references[0] = [100.0, 1, 1, 1]

    return rows, references, refLinks


### main ###


try:
    con = db.connect('localhost', 'root', 'root', 'world')
    cur = con.cursor()

    rows, references, refLinks = GetLootTable(npc_entry, cur)

    iterNumber = 10

    print "-- Loot table for %s" % GetCreatureName(npc_entry, cur)
    for key in rows:
        print key
        for row in rows[key]:
            print "\t %s - %s" % (str(row), GetItemName(row[0], cur))

    for i in range(0, iterNumber):
        print "\n%i -- Loot generated for %s" % (i, GetCreatureName(npc_entry, cur))
        for item in ProcessLoot(rows, references, refLinks):
            print "\t%i - %s" % (item, GetItemName(item, cur))

    con.close()

except db.Error, e:
    print "Error %d: %s" % (e.args[0], e.args[1])
    sys.exit(1)
