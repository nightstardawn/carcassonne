from abc import ABC
import random
from typing import Self, override

import pygame
from tileset import Tileset
from wfc import Cell, Map, Tile, WF
from geom import *


class Extend[T: WF](WF):
    inner: T

    @override
    def __init__(self, inner: T) -> None:
        super().__init__()
        self.inner = inner

    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        return self.inner.wave_function(map, pos, cell)

    @override
    def take(self, map: Map, pos: Pos, tile: Tile):
        self.inner.take(map, pos, tile)

    @override
    def new_stage(self, map: Map):
        return super().new_stage(map)

    @override
    def draw(self, map: Map, scale: int, screen: pygame.Surface):
        return super().draw(map, scale, screen)

    @override
    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, screen_pos: Pos, scale: int, screen: pygame.Surface):
        return super().draw_on_cell(map, pos, cell, screen_pos, scale, screen)


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

    @override
    def __init__(self, inner: WF, tiles: Tileset, weight: bool = False, decks: int = 1):
        super().__init__(inner)
        self.tiles = tiles
        self.weight = weight
        self.hand = {}

        for img_src, amount in Deck.TileFrequencies.items():
            kind = next(tile for tile in self.tiles.kinds if tile.img_src == img_src)
            self.hand[kind.id] = amount * decks

    @override
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

    @override
    def take(self, map: Map, pos: Pos, tile: Tile):
        super().take(map, pos, tile)
        self.hand[tile.kind.id] -= 1

class RealDeck(Extend[Deck]):
    top: int | None

    def shuffle(self):
        ids = [ id for id, amount in self.inner.hand.items() if amount > 0 ]
        if len(ids) > 0:
            self.top = random.choice(ids)
        else:
            self.top = None

    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)

        return {
            (tile, n) for tile, n in wf
            if tile.kind.id == self.top
        }

    @override
    def new_stage(self, map: Map):
        super().new_stage(map)
        self.shuffle()

    @override
    def draw(self, map: Map, scale: int, screen: pygame.Surface):
        super().draw(map, scale, screen)

        if self.top:
            img = self.inner.tiles.images[self.top, 0]
            img.set_alpha(255)
            x, y = 25, 25
            screen.blit(img, (x, y))


# A definition of a wave function in which, if it's possible for the chosen tile
# to connect to an existing city, we won't even consider placing roads.
class CityBuilder(Extend[WF]):
    @override
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

            if tile.connects_city(other, dir):
                num_connections += 1

        return num_connections


class RoadBuilder(Extend[WF]):
    class Road:
        positions: set[Pos]
        colour: pygame.Color

        def __init__(self, pos: Pos) -> None:
            self.positions = {pos}
            self.colour = pygame.Color(random.randrange(255), random.randrange(255), random.randrange(255))

        def __len__(self) -> int:
            return len(self.positions)

    # Roads are shared between all cells which constitute a part of that road,
    # so that their lengths are interlinked
    roads: dict[Pos, Road]
    should_draw: bool

    def __init__(self, draw: bool, inner: WF) -> None:
        super().__init__(inner)
        self.roads = {}
        self.should_draw = draw

    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)
        return { (tile, w * self.forecast(map, pos, tile)) for tile, w in wf }

    @override
    def take(self, map: Map, pos: Pos, tile: Tile):
        super().take(map, pos, tile)

        if len(tile.kind.roads) > 0:
            for dir, other in map.around(pos):
                if (other_road := self.roads.get(other.pos)) and tile.connects_road(other, dir):
                    self.attach(pos, other_road)

            if pos not in self.roads:
                self.roads[pos] = RoadBuilder.Road(pos)

    def forecast(self, map: Map, pos: Pos, tile: Tile) -> int:
        # if we put tile at pos, what length road would it be part of?
        if len(tile.kind.roads) == 0:
            return 0

        return sum(
            len(road) for dir, other in map.around(pos)
            if (road := self.roads.get(other.pos))
            and tile.connects_road(other, dir)
        )

    def attach(self, pos: Pos, other_road: Road):
        if (this_road := self.roads.get(pos)):
            for other_pos in other_road.positions:
                self.roads[other_pos] = this_road
            this_road.positions |= other_road.positions
        else:
            self.roads[pos] = other_road
            other_road.positions.add(pos)

    @override
    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, screen_pos: Pos, scale: int, screen: pygame.Surface):
        super().draw_on_cell(map, pos, cell, screen_pos, scale, screen)

        if self.should_draw and (road := self.roads.get(pos)):
            pygame.draw.circle(screen, road.colour, screen_pos + (scale // 2, scale // 2), 5)
