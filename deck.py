import random
from tileset import Tileset
from wfc import Cell, Tile, EntropyDefinition
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

    def choices(self, pos: Pos, cell: Cell) -> list[Tile]:
        return [
            tile for tile in cell.options
            if self.hand.get(tile.kind.id, 0) > 0 ]

    def take(self, tile: Tile):
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

    def choices(self, pos: Pos, cell: Cell) -> list[Tile]:
        return [ tile for tile in cell.options if tile.kind.id == self.top ]

    def take(self, tile: Tile):
        self.hand[tile.kind.id] -= 1
        self.shuffle()

def default_deck(tiles: Tileset) -> Deck:
    return Deck(tiles, {
        "m": 4,

        "u": 5,
        "u-d": 3,
        "u-r": 2,
        "lr": 1,
        "lr.s": 2,
        "ur": 3,
        "ur.s": 2,
        "ulr": 3,
        "ulr.s": 1,
        "udlr.s": 1,

        "m.d": 2,
        "ulr.d": 1,
        "ulr.s.d": 2,

        "-.lr": 8,
        "-.ld": 9,
        "u.lr": 4,
        "u.ld": 3,
        "u.rd": 3,
        "ur.ld": 3,
        "ur.s.ld": 3,

        "-.lrd": 4,
        "u.lrd": 3,
        "-.ulrd": 1,
    })
