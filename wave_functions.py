from abc import ABC, abstractmethod
import random
from typing import Self, override

import pygame
from tileset import TileKind, Tileset
from wfc import INFO, Cell, Map, Piece, Tile, WF
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
    def entropy(self, map: Map, pos: Pos, cell: Cell, wf: set[tuple[Tile, int]]) -> float:
        return self.inner.entropy(map, pos, cell, wf)

    @override
    def take(self, map: Map, pos: Pos, tile: Tile):
        self.inner.take(map, pos, tile)

    @override
    def after_collapse(self, map: Map, reductions: int):
        return self.inner.after_collapse(map, reductions)

    @override
    def draw(self, map: Map, entropies: dict[Pos, float], scale: int, screen: pygame.Surface):
        return self.inner.draw(map, entropies, scale, screen)

    @override
    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, entropies: dict[Pos, float], screen_pos: Pos, scale: int, screen: pygame.Surface):
        return self.inner.draw_on_cell(map, pos, cell, entropies, screen_pos, scale, screen)


class Deck(Extend[WF]):
    tiles: Tileset
    weight: bool
    hand: dict[int, int] # a dictionary of in our hand, and their amounts
    decks: int
    infinite: bool
    infinite_rivers: bool
    hint_scale: int | None

    TileFrequencies = {
        "m": 4, "u": 5, "u-d": 3, "u-r": 2, "lr": 1, "lr.s": 2, "ur": 3,
        "ur.s": 2, "ulr": 3, "ulr.s": 1, "udlr.s": 1, "m.d": 2, "ulr.d": 1,
        "ulr.s.d": 2, "-.lr": 8, "-.ld": 9, "u.lr": 4, "u.ld": 3, "u.rd": 3,
        "ur.ld": 3, "ur.s.ld": 2, "-.lrd": 4, "u.lrd": 3, "-.ulrd": 1,

        "river-d": 2, "river-ld": 2, "river-ld.ur": 1, "river-lr": 2,
        "river-lr.-.ud": 1, "river-lr.-.ur": 1, "river-lr.m.d": 1,
        "river-lr.u.d": 1, "river-lr.ud": 1,
    }

    @override
    def __init__(
        self,
        inner: WF, tiles: Tileset,
        weight: bool = False, decks: int = 1,
        infinite: bool = False, infinite_rivers: bool = False,
        hint_scale: int | None = 64,
    ):
        super().__init__(inner)
        self.tiles = tiles
        self.weight = weight
        self.hand = {}
        self.decks = decks
        self.infinite = infinite
        self.infinite_rivers = infinite_rivers
        self.hint_scale = hint_scale

        if self.hint_scale:
            self.tiles.cache_images(self.hint_scale, 0)

        self.reset(True)

    def reset(self, with_rivers: bool | None = None):
        if with_rivers == None:
            with_rivers = self.infinite_rivers

        for kind in self.tiles.kinds:
            if "river" in kind.img_src and not with_rivers:
                continue

            amount = Deck.TileFrequencies.get(kind.img_src, 1)
            self.hand[kind.id] = amount * self.decks

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

        if self.infinite and all(amount == 0 for _, amount in self.hand.items()):
            self.reset()

    @override
    def draw(self, map: Map, entropies: dict[Pos, float], scale: int, screen: pygame.Surface):
        super().draw(map, entropies, scale, screen)

        if not (hs := self.hint_scale):
            return

        kinds = [ (tile, amount) for (tile, amount) in self.hand.items() if amount > 0 ]
        self.draw_deck(20, screen.get_height() - 20 - hs, kinds, hs, screen)

    def draw_deck(self, x_b: int, y_b: int, kinds: list[tuple[int, int]], hs: int, screen: pygame.Surface):
        if len(kinds) == 0:
            return

        total_width = screen.get_width() - x_b - hs
        x_per_tile = min(total_width / len(kinds), hs + 10)

        x = x_b
        for tile, amount in kinds:
            for j in reversed(range(amount)):
                k = j / amount
                y = y_b - j * 15
                img = self.tiles.images[tile, hs, 0]
                img.set_alpha(255 if j == 0 else int(64 + 128 * (1 - k)))
                pygame.draw.rect(screen, "black", (x, y, hs, hs))
                screen.blit(img, (x, y))

            x += x_per_tile


class RealDeck(Extend[Deck]):
    top: int | None
    hint_scale: int | None

    def __init__(self, inner: Deck, hint_scale: int | None = None) -> None:
        super().__init__(inner)
        self.hint_scale = hint_scale or inner.hint_scale

        self.shuffle()
        if self.hint_scale is not None:
            self.inner.tiles.cache_images(self.hint_scale, 0)

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
    def draw(self, map: Map, entropies: dict[Pos, float], scale: int, screen: pygame.Surface):
        if not self.inner.hint_scale or not (hs := self.hint_scale) or not self.top:
            super().draw(map, entropies, scale, screen)
            return

        top_kinds = [(self.top, self.inner.hand[self.top])]
        self.inner.draw_deck(20, screen.get_height() - 20 - hs, top_kinds, hs, screen)

        kinds = [
            (tile, amount) for (tile, amount) in self.inner.hand.items()
            if amount > 0 and tile != self.top
        ]
        self.inner.draw_deck(
            40 + hs, screen.get_height() - 20 - self.inner.hint_scale,
            kinds, self.inner.hint_scale, screen
        )


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
        shields: int
        colour: pygame.Color

        def __init__(self, pos: Pos, shield: bool) -> None:
            self.positions = {pos}
            self.shields = 1 if shield else 0
            self.colour = pygame.Color(
                random.randrange(255),
                random.randrange(255),
                random.randrange(255),
            )

        def __len__(self) -> int:
            return len(self.positions)

    # Groups are shared between all cells which constitute a part of that group,
    # so that their lengths are interlinked
    groups: dict[Pos, Group]
    should_draw: bool
    strict: bool
    uses_shield_score: bool

    def __init__(self, inner: WF, draw: bool = False) -> None:
        super().__init__(inner)
        self.groups = {}
        self.should_draw = draw
        self.strict = True
        self.uses_shield_score = False

    @staticmethod
    @abstractmethod
    def forms_group(kind: TileKind) -> bool: ...

    @staticmethod
    @abstractmethod
    def connects(this: Piece, that: Piece, dir: Direction) -> bool: ...

    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)

        return {
            (tile, w * f * 5) if (f := self.forecast(map, pos, tile)) > 0 else (tile, w)
            for tile, w in wf
        }

    @override
    def entropy(self, map: Map, pos: Pos, cell: Cell, wf: set[tuple[Tile, int]]) -> float:
        if len(wf) == 0:
            return -1

        e = (1.0 / max(w for _, w in wf))
        return e * len(wf)

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
                    self.attach(pos, tile, other_group)

            if pos not in self.groups:
                self.groups[pos] = WeLikeConnections.Group(pos, tile.has_shield())

    def forecast(self, map: Map, pos: Pos, tile: Tile) -> int:
        shift = 0 if self.strict else 1

        # if we put tile at pos, what length group would it be part of?
        if not self.forms_group(tile.kind):
            return shift

        return sum(
            len(group) + (group.shields if self.uses_shield_score else 0)
            for dir, other in map.around(pos)
            if (group := self.groups.get(other.pos))
            and self.connects(tile, other, dir)
        ) + shift

    def attach(self, pos: Pos, tile: Tile, other_group: Group):
        if tile.has_shield():
            other_group.shields += 1

        if (this_group := self.groups.get(pos)):
            for other_pos in other_group.positions:
                self.groups[other_pos] = this_group
            this_group.positions |= other_group.positions
            this_group.shields += other_group.shields
        else:
            self.groups[pos] = other_group
            other_group.positions.add(pos)

    @override
    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, entropies: dict[Pos, float], screen_pos: Pos, scale: int, screen: pygame.Surface):
        super().draw_on_cell(map, pos, cell, entropies, screen_pos, scale, screen)

        if self.should_draw and (group := self.groups.get(pos)):
            if cell.has_shield() and self.uses_shield_score:
                pygame.draw.circle(screen, (0, 0, 0), screen_pos + (int(scale * 0.3), scale // 2), 7)
                pygame.draw.circle(screen, (0, 0, 0), screen_pos + (int(scale * 0.7), scale // 2), 7)
                pygame.draw.circle(screen, group.colour, screen_pos + (int(scale * 0.3), scale // 2), 5)
                pygame.draw.circle(screen, group.colour, screen_pos + (int(scale * 0.7), scale // 2), 5)
            else:
                pygame.draw.circle(screen, (0, 0, 0), screen_pos + (scale // 2, scale // 2), 7)
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
        self.uses_shield_score = True

    @override
    @staticmethod
    def forms_group(kind: TileKind) -> bool:
        return len(kind.cities) > 0

    @override
    @staticmethod
    def connects(this: Piece, that: Piece, dir: Direction) -> bool:
        return this.connects_city(that, dir)


class RiverBuilder(WeLikeConnections):
    def __init__(self, inner: WF, draw: bool = False) -> None:
        super().__init__(inner, draw)

    @override
    @staticmethod
    def forms_group(kind: TileKind) -> bool:
        return len(kind.rivers) > 0

    @override
    @staticmethod
    def connects(this: Piece, that: Piece, dir: Direction) -> bool:
        return this.connects_river(that, dir)


class Opportunistic(Extend[WF]):
    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)
        return { (tile, w * len(cell)) for tile, w in wf }


# Yasemin Yilmaz wave function implementation
class Yas(Extend[WF]):
    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)

        return {
            (tile, w - 2 * len([True for dir, other in map.around(pos) if self.connects(tile, other, dir)]))
            for tile, w in wf
        }

    @staticmethod
    def connects(this: Piece, that: Piece, dir: Direction) -> bool:
        return this.connects_city(that, dir) or this.connects_road(that, dir)


class RiversFirst(Extend[WF]):
    @override
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        wf = super().wave_function(map, pos, cell)

        joined_rivers = {
            (tile, w) for tile, w in wf
            if (not tile.kind.rivers) or any(
                other.is_river(dir.flip())
                for dir, other in map.around(pos)
            )
        }

        with_rivers = {
            (tile, w) for tile, w in joined_rivers if tile.kind.rivers
        }

        return with_rivers

    @override
    def entropy(self, map: Map, pos: Pos, cell: Cell, wf: set[tuple[Tile, int]]) -> float:
        old = super().entropy(map, pos, cell, wf)

        if any(not tile.kind.rivers for tile, _ in wf):
            return old * 100

        return old


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
    def draw(self, map: Map, entropies: dict[Pos, float], scale: int, screen: pygame.Surface):
        super().draw(map, entropies, scale, screen)

    @override
    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, entropies: dict[Pos, float], screen_pos: Pos, scale: int, screen: pygame.Surface):
        super().draw_on_cell(map, pos, cell, entropies, screen_pos, scale, screen)

        rect = (screen_pos, (scale, scale))
        if pos == self.last_taken:
            pygame.draw.rect(screen, (255, 255, 0), rect, 2)
            return

        if len(entropies) == 0:
            return

        # get the max and min entropies in the whole map. we don't want to include
        # any ≤1 entropy cells for the min, though, because these are cells that
        # we don't want to collapse (already collapsed, or not valid)
        max_entropy = max(entropies.values())
        min_entropy = min((v for v in entropies.values() if v > -1), default=0)

        if not cell.is_stable and (entropy := entropies.get(pos, 0)) > -1:
            if max_entropy == min_entropy:
                p = 1.0
            else:
                p = 1.0 - ((entropy - min_entropy) / (max_entropy - min_entropy))

            p = max(0, min(p, 1))

            w: int = max(0, int(scale*0.05 + (scale*0.075)*p))

            pygame.draw.rect(screen, (0, int(170 * p * p) + 70, int(130 * p) + 25, 100), rect, w)
