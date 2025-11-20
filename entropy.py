from abc import ABC
import random
from tileset import Tileset
from wfc import Cell, Map, Tile, EntropyDefinition
from geom import *

class Deck(EntropyDefinition):
    tiles: Tileset
    hand: dict[int, int] # a dictionary of in our hand, and their amounts

    def __init__(self, tiles: Tileset, amounts: dict[str, int]):
        self.tiles = tiles
        self.hand = {}
        for img_src, amount in amounts.items():
            kind = next(tile for tile in self.tiles.kinds if tile.img_src == img_src)
            self.hand[kind.id] = amount

    def choices(self, map: Map, pos: Pos, cell: Cell) -> list[Tile]:
        return [
            tile for tile in cell.options
            if self.hand.get(tile.kind.id, 0) > 0 ]

    def take(self, map: Map, tile: Tile):
        self.hand[tile.kind.id] -= 1

class RealDeck(Deck):
    top: int | None

    def __init__(self, tiles: Tileset, amounts: dict[str, int]):
        super().__init__(tiles, amounts)
        self.shuffle()

    def shuffle(self):
        ids = [ id for id, amount in self.hand.items() if amount > 0 ]
        if len(ids) > 0:
            self.top = random.choice(ids)
        else:
            self.top = None

    def choices(self, map: Map, pos: Pos, cell: Cell) -> list[Tile]:
        return [ tile for tile in cell.options if tile.kind.id == self.top ]

    def take(self, map: Map, tile: Tile):
        self.hand[tile.kind.id] -= 1
        self.shuffle()

    def new_stage(self, map: Map):
        self.shuffle()

class Extend(EntropyDefinition):
    inner: EntropyDefinition

    def __init__(self, inner: EntropyDefinition) -> None:
        super().__init__()
        self.inner = inner

    def choices(self, map: Map, pos: Pos, cell: Cell) -> list[Tile]:
        return self.inner.choices(map, pos, cell)

    def entropy(self, map: Map, pos: Pos, cell: Cell) -> int:
        return len(self.choices(map, pos, cell))

    def take(self, map: Map, tile: Tile):
        self.inner.take(map, tile)


class CityBuilder(Extend):
    def choices(self, map: Map, pos: Pos, cell: Cell) -> list[Tile]:
        choices = super().choices(map, pos, cell)
        weighted = []

        for tile in choices:
            num_connections = 0
            for dir, other in map.around(pos):
                opp = dir.flip()

                if tile.has_city(dir) and other.has_city(opp):
                    num_connections += 1
                    weighted.append(tile)

        if len(weighted) == 0:
            return choices

        return weighted


def frequencies(numdecks: int) -> dict[str, int]:
    return {
        "m": 4 * numdecks,
        "u": 5 * numdecks,
        "u-d": 3 * numdecks,
        "u-r": 2 * numdecks,
        "lr": 1 * numdecks,
        "lr.s": 2 * numdecks,
        "ur": 3 * numdecks,
        "ur.s": 2 * numdecks,
        "ulr": 3 * numdecks,
        "ulr.s": 1 * numdecks,
        "udlr.s": 1 * numdecks,
        "m.d": 2 * numdecks,
        "ulr.d": 1 * numdecks,
        "ulr.s.d": 2 * numdecks,
        "-.lr": 8 * numdecks,
        "-.ld": 9 * numdecks,
        "u.lr": 4 * numdecks,
        "u.ld": 3 * numdecks,
        "u.rd": 3 * numdecks,
        "ur.ld": 3 * numdecks,
        "ur.s.ld": 3 * numdecks,
        "-.lrd": 4 * numdecks,
        "u.lrd": 3 * numdecks,
        "-.ulrd": 1 * numdecks,
    }
