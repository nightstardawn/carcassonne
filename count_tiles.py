from itertools import product
from typing import get_args
from geom import *
from tileset import TileKind, Tileset


# returns (actual, max possible)
def count(tiles: Tileset, options: list[str | None] = ["city", "road", None]) -> tuple[int, int]:
    possibilities = [
        {U: u, D: d, L: l, R: r}
        for (u, d, l, r) in product(options, repeat=4)
    ]

    n = 0
    for poss in possibilities:
        try:
            next(kind for kind in tiles.kinds if matches(kind, poss))
            n += 1
        except StopIteration:
            pass

    return (n, len(possibilities))

def matches(kind: TileKind, sides: dict[Direction, str | None]) -> bool:
    for angle in get_args(Angle):
        this_matches = True

        for dir, side in sides.items():
            r_dir = dir.rotate(angle)

            if side == "road" and r_dir not in kind.roads:
                this_matches = False
                break

            if side == "city" and all(r_dir not in city for city in kind.cities):
                this_matches = False
                break

            if side == None and (any(r_dir in city for city in kind.cities) or r_dir in kind.roads):
                this_matches = False
                break

        if this_matches:
            return True

    return False

tileset = Tileset(Tileset.BaseTiles)

actual, possible = count(tileset)
print(f"in the base tileset, there are {actual} distinct tile layouts, out of a possible {possible}")
print("(modulo shields, monasteries, and rivers; we only care about roads and cities here. we also don't consider the connectness of cities and roads)")

actual, possible = count(tileset, options=["road", None])
print(f"\nif we only care about roads, then we have {actual} of {possible}")

actual, possible = count(tileset, options=["city", None])
print(f"if we only care about cities, then we have {actual} of {possible}")
