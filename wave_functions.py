from abc import ABC, abstractmethod
import random
from typing import Self, override

import pygame
from tileset import TileKind, Tileset
from wfc import Cell, Map, Piece, Tile, WF
from geom import *


class Extend[T: WF](WF):
    inner: T

    @override
    def __init__(self, inner: T) -> None:
        super().__init__()
        self.inner = inner
        print(f"... with {self.__class__.__name__}")

    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        return self.inner.wave_function(map, pos, cell)

    @override
    def take(self, map: Map, pos: Pos, tile: Tile):
        self.inner.take(map, pos, tile)

    @override
    def after_collapse(self, map: Map, reductions: int):
        return self.inner.after_collapse(map, reductions)

    @override
    def draw(self, map: Map, entropies: dict[Pos, int], scale: int, screen: pygame.Surface):
        return self.inner.draw(map, entropies, scale, screen)

    @override
    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, entropies: dict[Pos, int], screen_pos: Pos, scale: int, screen: pygame.Surface):
        return self.inner.draw_on_cell(map, pos, cell, entropies, screen_pos, scale, screen)


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

    def __init__(self, inner: Deck) -> None:
        super().__init__(inner)
        self.shuffle()

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
    def after_collapse(self, map: Map, reductions: int):
        super().after_collapse(map, reductions)
        self.shuffle()

    @override
    def draw(self, map: Map, entropies: dict[Pos, int], scale: int, screen: pygame.Surface):
        super().draw(map, entropies, scale, screen)

        if self.top:
            img = self.inner.tiles.images[self.top, 0]
            img.set_alpha(255)
            x, y = 25, 25
            screen.blit(img, (x, y))


# A definition of a wave function in which, if it's possible for the chosen tile
# to connect to an existing city, we won't even consider placing roads.
class LargeCities(Extend[WF]):
    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)

        weighted: set[tuple[Tile, int]] = {
            (tile, m) for tile, n in wf
            if (m := n * LargeCities.num_connections(map, pos, tile)) > 0
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


class WeLikeConnections(Extend[WF], ABC):
    class Group:
        positions: set[Pos]
        colour: pygame.Color

        def __init__(self, pos: Pos) -> None:
            self.positions = {pos}
            self.colour = pygame.Color(random.randrange(255), random.randrange(255), random.randrange(255))

        def __len__(self) -> int:
            return len(self.positions)

    # Groups are shared between all cells which constitute a part of that group,
    # so that their lengths are interlinked
    groups: dict[Pos, Group]
    should_draw: bool
    strict: bool

    def __init__(self, inner: WF, draw: bool = False) -> None:
        super().__init__(inner)
        self.groups = {}
        self.should_draw = draw
        self.strict = True

    @staticmethod
    @abstractmethod
    def forms_group(kind: TileKind) -> bool: ...

    @staticmethod
    @abstractmethod
    def connects(this: Piece, that: Piece, dir: Direction) -> bool: ...

    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)

        return { (tile, w * self.forecast(map, pos, tile)) for tile, w in wf }

    @override
    def after_collapse(self, map: Map, reductions: int):
        super().after_collapse(map, reductions)
        self.strict = reductions > 0

    @override
    def take(self, map: Map, pos: Pos, tile: Tile):
        super().take(map, pos, tile)

        if self.forms_group(tile.kind):
            for dir, other in map.around(pos):
                if (other_group := self.groups.get(other.pos)) and self.connects(tile, other, dir):
                    self.attach(pos, other_group)

            if pos not in self.groups:
                self.groups[pos] = WeLikeConnections.Group(pos)

    def forecast(self, map: Map, pos: Pos, tile: Tile) -> int:
        shift = 0 if self.strict else 1

        # if we put tile at pos, what length group would it be part of?
        if not self.forms_group(tile.kind):
            return shift

        return sum(
            len(group) for dir, other in map.around(pos)
            if (group := self.groups.get(other.pos))
            and self.connects(tile, other, dir)
        ) + shift

    def attach(self, pos: Pos, other_group: Group):
        if (this_group := self.groups.get(pos)):
            for other_pos in other_group.positions:
                self.groups[other_pos] = this_group
            this_group.positions |= other_group.positions
        else:
            self.groups[pos] = other_group
            other_group.positions.add(pos)

    @override
    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, entropies: dict[Pos, int], screen_pos: Pos, scale: int, screen: pygame.Surface):
        super().draw_on_cell(map, pos, cell, entropies, screen_pos, scale, screen)

        if self.should_draw and (group := self.groups.get(pos)):
            pygame.draw.circle(screen, group.colour, screen_pos + (scale // 2, scale // 2), 5)


class RoadBuilder(WeLikeConnections):
    def __init__(self, inner: WF, draw: bool = False) -> None:
        super().__init__(inner, draw)

    @override
    @staticmethod
    def forms_group(kind: TileKind) -> bool:
        return len(kind.roads) > 0


    @override
    @staticmethod
    def connects(this: Piece, that: Piece, dir: Direction) -> bool:
        return this.connects_road(that, dir)


class CityBuilder(WeLikeConnections):
    def __init__(self, inner: WF, draw: bool = False) -> None:
        super().__init__(inner, draw)

    @override
    @staticmethod
    def forms_group(kind: TileKind) -> bool:
        return len(kind.cities) > 0


    @override
    @staticmethod
    def connects(this: Piece, that: Piece, dir: Direction) -> bool:
        return this.connects_city(that, dir)


class DebugOverlay(Extend[WF]):
    last_taken: Pos | None

    @override
    def __init__(self, inner: WF) -> None:
        super().__init__(inner)

    @override
    def take(self, map: Map, pos: Pos, tile: Tile):
        super().take(map, pos, tile)
        self.last_taken = pos

    @override
    def after_collapse(self, map: Map, reductions: int):
        super().after_collapse(map, reductions)
        if reductions == 0:
            self.last_taken = None

    @override
    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, entropies: dict[Pos, int], screen_pos: Pos, scale: int, screen: pygame.Surface):
        super().draw_on_cell(map, pos, cell, entropies, screen_pos, scale, screen)

        rect = (screen_pos, (scale, scale))
        if pos == self.last_taken:
            pygame.draw.rect(screen, (255, 255, 0), rect, 2)
            return

        if len(entropies) == 0:
            return

        max_entropy = max(entropies.values())
        min_entropy = min((v for v in entropies.values() if v > 1), default=1)

        if not cell.is_stable and (entropy := entropies.get(pos, 0)) > 0:
            if max_entropy == min_entropy:
                p = 1
            else:
                p = 1 - ((entropy - min_entropy) / (max_entropy - min_entropy))

            p = max(0, min(p, 1))

            w = 4 if entropy == min_entropy else 2

            pygame.draw.rect(screen, (128 - int(128 * p), int(255 * p), int(128 * p)), rect, w)
