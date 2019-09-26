#!/usr/bin/python3.6
import argparse
from typing import *
import random as rd
import sys

# https://pypi.org/project/recordclass/
from recordclass import recordclass, RecordClass # type: ignore

seed = rd.randrange(sys.maxsize)
seed = 4209056135191916808
rng = rd.Random(seed)
print("Seed:", seed)

nDays = 2 # number of available days

Name = str
Score = float
DaysOk = List[bool]
PlayerInfo = Tuple[Score, DaysOk]
ParseInfo = Dict[Name, PlayerInfo]

def parse_file (f) -> ParseInfo:
    parseInfo: ParseInfo = {}
    for line in f:
        words = line.split(' ')
        name = ''.join(words[0:-3]).replace('{', '').replace('}', '').replace('|', '')
        score = float(words[-3])
        daysOk = [bool(words[-2]), bool(words[-1])]
        if not any(daysOk):
            continue

        assert(name not in parseInfo)
        parseInfo[name] = (score, daysOk)
    return parseInfo

Rank = int
def score_to_rank(s: Score) -> Rank:
    assert (s >= 0.0)
    if (s < 10.0):
        return 0
    elif (s < 20.0):
        return 1
    elif (s < 35.0):
        return 2
    elif (s < 50.0):
        return 3
    else:
        return 4


Day = int
Table = int
class PlayerAssign(RecordClass):
    day: Day
    table: Table
PA = PlayerAssign
Solution = Dict[Name, PlayerAssign]


def _check_solution(parseInfo: ParseInfo, solution: Solution, rankDiff: Optional[int] = None) -> int:
    # 1) All players that are available for a day, should have an assignment
    for player in parseInfo:
        _, daysOk = parseInfo[player]
        if player not in solution:
            return -1

    # 2) Each player should be available during their assigned day
    for player in solution:
        _, daysOk = parseInfo[player]
        day, _ = solution[player]
        if not daysOk[day]:
            return -2

    # 3) Each table should have 4 to 6 players
    tableSize: Dict[Table, int] = {}
    for player in solution:
        table, _ = solution[player]
        if table not in tableSize:
            tableSize[table] = 0
        tableSize[table] += 1
    for table in tableSize:
        if not (4 <= tableSize[table] <= 6):
            return -3

    # 4) Check that the rank difference of a table does not exceed RankDiff
    if rankDiff is not None:
        tableRankRange: Dict[Table, Tuple[int, int]] = {}
        for player in solution:
            table, _ = solution[player]
            score, _ = parseInfo[player]
            rank = score_to_rank(score)
            if table not in tableRankRange:
                tableRankRange[table] = (rank, rank)

            rankRange = tableRankRange[table]
            if rank < rankRange[0]:
                rankRange = (rank, rankRange[1])
            elif rank > rankRange[1]:
                rankRange = (rankRange[0], rank)
            tableRankRange[table] = rankRange

        for table in tableRankRange:
            rankRange = tableRankRange[table]
            tableDiff = rankRange[1] - rankRange[0]
            if tableDiff > rankDiff:
                return -4

    # 5) Each player should not be allocated to more than one table
    # --> already guaranteed by the dictionary structure

    return 0


def check_solution(parseInfo: ParseInfo, solution: Solution, rankDiff: Optional[int] = None) -> bool:
    return (_check_solution(parseInfo, solution, rankDiff) == 0)


def test_check_solution() -> None:
    parseInfo = {"toto": (0., [False, True]), "titi": (0., [False, True]), "tata": (0., [False, True]), "lolo": (0., [True, True])}

    solution = {"toto": PA(1, 0), "titi": PA(1, 0), "tata": PA(1, 0), "lolo": PA(1, 0)}
    assert(_check_solution(parseInfo, solution, 0) == 0) # success

    solution = {"toto": PA(1, 0), "tata": PA(1, 0), "lolo": PA(1, 0)}
    assert(_check_solution(parseInfo, solution, 0) == -1) # fail 1)

    solution = {"toto": PA(0, 0), "titi": PA(0, 0), "tata": PA(0, 0), "lolo": PA(0, 0)}
    assert(_check_solution(parseInfo, solution, 0) == -2) # fail 2)

    parseInfo = {"toto": (0., [False, True]), "titi": (0., [False, True]), "tata": (0., [False, True])}
    solution = {"toto": PA(1, 0), "titi": PA(1, 0), "tata": PA(1, 0)}
    assert(_check_solution(parseInfo, solution, 0) == -3) # fail 3)

    parseInfo = {"toto": (10., [False, True]), "titi": (0., [False, True]), "tata": (0., [False, True]), "lolo": (0., [True, True])}
    solution = {"toto": PA(1, 0), "titi": PA(1, 0), "tata": PA(1, 0), "lolo": PA(1, 0)}
    assert(_check_solution(parseInfo, solution, 0) == -4) # fail 4)

    print("All good!")


def print_solution(solution: Solution) -> None:
    print(20*"#" + " solution " + 20*"#")
    tables : Dict[int, Tuple[Day, List[Name]]] = {}
    for player in solution:
        day, table = solution[player]
        if table not in tables:
            tables[table] = (day, [])
        tables[table][1].append(player)

    for table in tables:
        print("Table", table, "of day", tables[table][0])
        for player in tables[table][1]:
            print("\t", player)

## Heuristic to compute the solution.
#
# The principle is to follow a partial ordering of the players, and then try
# to form contiguous groups out of that ordering.
#
# This ordering is such that two properties are ensured:
# 1) Players of same rank are contiguous
# 2) Within each even rank, the Day 1 only players are at the top while the
#    Day 2 only players are at the bottom. For each odd rank, it's the opposite:
#    Day 1 players at the bottom, Day 2 players at the top.
#    These two days are selected at random so that no particular day is biased.
#
# Since we represent this partial ordering with a totally ordered list, we also
# insert randomness into each equivalence class.
#
# This alternation is to ease the group making of people of different ranks,
# when the numbers are not ideal to work with. It introduces a potential bias
# though: the players who select both days will have more probability to be
# found in a table of the same rank as them, than those who only select one day.
#
# Those who only select one day will sometimes find themselves in a table of higher
# rank, sometimes in lower rank, but since we select Day 1 and Day 2 randomly,
# normally this shouldn't introduce any significant bias.
#
# Also, this particular algorithm becomes irrelevant if more than 2 days are
# available.. While I think it could be generalized, right now it's not worth
# the trouble.
##

def order_players(parseInfo: ParseInfo, day1: int) -> List[Name]:
    return []


def cut_by_four(n: int) -> List[int]:
    return []


def contiguous_gather(parseInfo: ParseInfo, sizes: List[int]) -> Solution:
    return {}


def compute_solution(parseInfo: ParseInfo) -> Solution:
    day1 = rng.randint(0, 1)
    ordered = order_players(parseInfo, day1)
    group_sizes = cut_by_four(len(ordered))
    solution = contiguous_gather(parseInfo, group_sizes)
    return solution


parser = argparse.ArgumentParser()
parser.add_argument("file")
args = parser.parse_args()

if args.file == "test":
    test_check_solution()
    sys.exit(0)

with open(args.file, 'r') as f:
    parseInfo = parse_file(f)

print(parseInfo)

solution = compute_solution(parseInfo)
print_solution(solution)

if not check_solution(parseInfo, solution):
    print("/!\\ The solution is not valid /!\\")

## OLD RANDOM VERSION
#def selectBestDivider(n: int, li: List[int]) -> int:
#    bestResult = None
#    for divider in li:
#        result = n % divider
#        if bestResult is None or result < bestResult:
#            bestResult = result
#            bestDivider = divider
#    return bestDivider
#
#
#def group_and_assign(partial: Solution, group: List[Name], tableCount: int) -> int:
#    bestDivider = selectBestDivider(len(group), list(range(4, 6+1)))
#    while len(group) >= bestDivider:
#        for i in range(bestDivider):
#            chosen = rng.choice(group)
#            group.remove(chosen)
#            partial[chosen][1] = tableCount
#        tableCount += 1
#    return tableCount
#
#
#def update_solution_fixed_day(parseInfo: ParseInfo, partial: Solution, day: Day,
#                              tableCount: int) -> int:
#    byRank : Dict[int, List[Name]] = {}
#    for player in parseInfo:
#        if partial[player].day != day:
#            continue
#        score, _ = parseInfo[player]
#        rank = score_to_rank(score)
#        if rank not in byRank:
#            byRank[rank] = []
#        byRank[rank].append(player)
#
#    for rank in byRank:
#        tableCount = group_and_assign(partial, byRank[rank], tableCount)
#
#    remaining: List[Name] = []
#    for rank in byRank:
#        remaining += byRank[rank]
#
#    tableCount = group_and_assign(partial, remaining, tableCount)
#    return tableCount
#
#
#def update_solution_fixed_days(parseInfo: ParseInfo, partial: Solution) -> None:
#    tableCount = 0
#    for day in range(nDays):
#        tableCount = update_solution_fixed_day(parseInfo, partial, day, tableCount)
#
#
#def choose_random_solution(parseInfo: ParseInfo) -> Solution:
#    solution = {}
#
#    for player in parseInfo:
#        score, daysOk = parseInfo[player]
#        availableDays: List[Day] = [day for day, ok in enumerate(daysOk) if ok]
#        day = rng.choice(availableDays)
#        solution[player] = PA(day, -1)
#    update_solution_fixed_days(parseInfo, solution)
#    return solution

#count=0
#while True: # do-while
#    solution = choose_random_solution(parseInfo)
#    if count <= 10000:
#        if check_solution(parseInfo, solution, 0):
#            break
#    elif count <= 20000:
#        if check_solution(parseInfo, solution, 1):
#            break
#    elif count <= 30000:
#        if check_solution(parseInfo, solution, 2):
#            break
#    elif count <= 40000:
#        if check_solution(parseInfo, solution, 3):
#            break
#    else:
#        print("Could not find a solution :-(")
#        break
#    count += 1

