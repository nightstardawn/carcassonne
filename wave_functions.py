from abc import ABC
import random
from typing import ClassVar, Type
import typing
from tileset import Tileset
from wfc import Cell, Map, Tile, WF
from geom import *


class Extend[T: WF](WF):
    inner: T

    def __init__(self, inner: T) -> None:
        super().__init__()
        self.inner = inner

    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        return self.inner.wave_function(map, pos, cell)

    def entropy(self, map: Map, pos: Pos, cell: Cell) -> int:
        return len(self.wave_function(map, pos, cell))

    def take(self, map: Map, tile: Tile):
        self.inner.take(map, tile)

    def new_stage(self, map: Map):
        return super().new_stage(map)


class Deck(Extend[WF]):
    tiles: Tileset
    weight: bool
    hand: dict[int, int] # a dictionary of in our hand, and their amounts

    TileFrequencies = {
        "m": 4, "u": 5, "u-d": 3, "u-r": 2, "lr": 1, "lr.s": 2, "ur": 3,
        "ur.s": 2, "ulr": 3, "ulr.s": 1, "udlr.s": 1, "m.d": 2, "ulr.d": 1,
        "ulr.s.d": 2, "-.lr": 8, "-.ld": 9, "u.lr": 4, "u.ld": 3, "u.rd": 3,
        "ur.ld": 3, "ur.s.ld": 3, "-.lrd": 4, "u.lrd": 3, "-.ulrd": 1,
    }

    def __init__(self, inner: WF, tiles: Tileset, weight: bool = False, decks: int = 1):
        super().__init__(inner)
        self.tiles = tiles
        self.weight = weight
        self.hand = {}

        for img_src, amount in Deck.TileFrequencies.items():
            kind = next(tile for tile in self.tiles.kinds if tile.img_src == img_src)
            self.hand[kind.id] = amount * decks

    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)

        if self.weight:
            return {
                (tile, n) for (tile, n) in wf
                if self.hand.get(tile.kind.id, 0) > 0
            }
        else:
            return {
                (tile, self.hand[tile.kind.id] * n) for (tile, n) in wf
            }

    def take(self, map: Map, tile: Tile):
        super().take(map, tile)
        self.hand[tile.kind.id] -= 1

class RealDeck(Extend[Deck]):
    top: int | None

    def shuffle(self):
        ids = [ id for id, amount in self.inner.hand.items() if amount > 0 ]
        if len(ids) > 0:
            self.top = random.choice(ids)
        else:
            self.top = None

    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)

        return {
            (tile, n) for tile, n in wf
            if tile.kind.id == self.top
        }

    def take(self, map: Map, tile: Tile):
        super().take(map, tile)
        self.inner.hand[tile.kind.id] -= 1
        self.shuffle()

    def new_stage(self, map: Map):
        super().new_stage(map)
        self.shuffle()


# A definition of a wave function in which, if it's possible for the chosen tile
# to connect to an existing city, we won't even consider placing roads.
class CityBuilder(Extend[WF]):
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)

        weighted: set[tuple[Tile, int]] = {
            (tile, m) for tile, n in wf
            if (m := n * CityBuilder.num_connections(map, pos, tile)) > 0
        }

        if len(weighted) == 0:
            return wf

        return weighted

    @staticmethod
    def num_connections(map: Map, pos: Pos, tile: Tile) -> int:
        num_connections = 0

        for dir, other in map.around(pos):
            opp = dir.flip()

            if tile.has_city(dir) and other.has_city(opp):
                num_connections += 1

        return num_connections
