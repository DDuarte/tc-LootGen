import MySQLdb as db
import random
import copy

# TODO: Implement lootmodes
# npc_entry, quest1, quest2, ... = argv


### random helpers ###


def RandCount(minCount, maxCount):
    """Random value between minCount and maxCount (inclusive)"""
    if (maxCount <= 0 or maxCount < minCount):
        print "counts (%i,%i) are invalid." % (minCount, maxCount)

    return random.randrange(minCount, maxCount + 1)


def RandChance(chance):
    """There's a chance% of this returning True"""

    if False:  # if withQuestItems, make this configurable
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
        sumChance = 0
        nonZero = 0
        for row in groups[group]:
            sumChance += row[1]
            if row[1] != 0:
                sameChance = False
                nonZero += 1
                continue

        if sumChance >= 100 and sumChance <= 101:
            sameChance = True

        if sameChance:
            if nonZero != len(groups[group]):
                chance = (100.0 - sumChance) / (len(groups[group]) - nonZero)
                for row in groups[group]:
                    if row[1] == 0:
                        row[1] = chance

        groups[group] = [groups[group], sameChance]

    return groups


def ProcessReference(rows):
    groups = SplitIntoGroups(rows)
    groups = CalculateChanceGroups(groups)

    loot = []

    for group in groups:
        gotItem = False
        forceDrop = groups[group][1]
        groupZero = group == 0

        while True:

            if gotItem and not groupZero:
                break

            if forceDrop and gotItem:
                break

            for row in groups[group][0]:
                    if (not gotItem or groupZero) and RandChance(row[1]):
                        for i in range(0, RandCount(row[4], row[5])):
                            loot.append(row[0])
                            gotItem = True
                            break

            if groupZero:
                break

    return loot


def ProcessLoot(rows, references, reflinks):
    """Simulates ONE kill; returns a list of items dropped."""
    loot = []

    for ref in references:
        if RandChance(references[ref][0]):  # ChanceOrQuestChance for references,
                                            # there's a certain chance of not processing references at all
            for i in range(0, references[ref][3]):  # maxcount for references, process reference X times
                if ref in rows:
                    for l in ProcessReference(rows[ref]):
                        loot.append(l)

    return loot


def GetLootTableAux(entry, cursor, rows, references, referencesLinks):
    """Auxiliar method of GetLootTable"""
    table = ""
    refEntry = 0
    if not rows and not references and not referencesLinks:
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


def GetHtml(n, entry, cursor):
    # process

    rows, references, refLinks = GetLootTable(entry, cursor)

    items = []
    for i in range(0, iterNumber):
        for item in ProcessLoot(rows, references, refLinks):
            items.append(item)

    hist = dict()
    for item in items:
        hist[item] = hist.get(item, 0) + 1

    for i in hist:
        hist[i] = [hist[i], hist[i] * 100.0 / iterNumber]

    name = GetCreatureName(entry, cursor)

    # print

    result = "<html>\n"
    result += "<head>\n"
    result += '\t<script type="text/javascript" src="http://static.wowhead.com/widgets/power.js"></script>\n'
    result += '\t<link href="tablecloth/tablecloth.css" rel="stylesheet" type="text/css" media="screen" />\n'
    result += '\t<script type="text/javascript" src="tablecloth/tablecloth.js"></script>\n'
    result += '\t<script type="text/javascript" src="sorttable.js"></script>\n'
    result += "</head>\n"
    result += "<body>\n"
    result += "\t<h3>Loot generated for %s - %i iterations</h3>\n" % (name, n)
    result += '\t<table border="1" class="sortable">\n'
    result += "\t\t<tr>\n"
    result += "\t\t\t<th>Item</th>\n"
    result += "\t\t\t<th>Count</th>\n"
    result += "\t\t\t<th>Chance</th>\n"
    result += "\t\t</tr>\n"
    for it in hist:
        result += "\t\t<tr>\n"
        result += "\t\t\t<td><a href=\"http://www.wowhead.com/item=%i\">%s</a></td>\n" % (it, GetItemName(it, cursor))
        result += "\t\t\t<td>%d</td>\n" % hist[it][0]
        result += "\t\t\t<td>%f</td>\n" % hist[it][1]
        result += "\t\t</tr>\n"
    result += "\t</table>\n"
    result += "</body>\n"
    result += "</html>\n\n"
    return result

### main ###

if __name__ == "__main__":

    #try:
        con = db.connect('localhost', 'root', 'root', 'world')
        cursor = con.cursor()

        cursor.execute("SELECT `entry` FROM `creature_template` WHERE `lootid`!=0;")
        entries = cursor.fetchall()

        iterNumber = 5000

        for i in entries:
            print i
            fileHtml = open("html\c%d.html" % i[0], 'w+')
            fileHtml.write(GetHtml(iterNumber, i[0], cursor))
            fileHtml.close()

        # print the raw table data from db
        #print "-- Loot table for %s" % GetCreatureName(npc_entry, cur)
        #for key in rows:
        #    print key
        #    for row in rows[key]:
        #        print "\t %s - %s" % (str(row), GetItemName(row[0], cur))

        #for i in range(0, iterNumber):
        #    print "\n%i -- Loot generated for %s" % (i, GetCreatureName(npc_entry, cur))
        #    for item in ProcessLoot(rows, references, refLinks):
        #        print "\t%i - %s" % (item, GetItemName(item, cur))

        con.close()

    #except db.Error, e:
    #    print "Error %d: %s" % (e.args[0], e.args[1])
    #    sys.exit(1)
