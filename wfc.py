from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache, cached_property
from itertools import chain
from math import exp, floor, log
from typing import Callable, Generator, Iterable, get_args, overload, override
from pygame.rect import Rect

from tileset import TileKind, Tileset
from geom import *

import random
import pygame


DebugLevel = Literal[0, 1, 2]
QUIET: DebugLevel = 0
INFO: DebugLevel = 1
DEBUG: DebugLevel = 2

DEBUG_LEVEL = QUIET


class Ternary(Enum):
    Never = 0
    Maybe = 1
    Must = 2


class WF:
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        return { (o, 1) for o in cell.valid_options }

    def entropy(self, map: Map, pos: Pos, cell: Cell, wf: set[tuple[Tile, int]]) -> float:
        if (total := sum(w for _, w in wf)) == 0:
            return -1

        return -sum(
            p * log(p) for _, w in wf
            if (p := float(w) / float(total)) > 0
        )

    def take(self, map: Map, pos: Pos, tile: Tile):
        pass

    def after_collapse(self, map: Map, reductions: int):
        pass

    def draw(self, map: Map, entropies: dict[Pos, float], scale: int, screen: pygame.Surface):
        pass

    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, entropies: dict[Pos, float], screen_pos: Pos, scale: int, screen: pygame.Surface):
        pass


class Piece(ABC):
    @abstractmethod
    def has_road(self, direction: Direction) -> bool: ...

    def is_road(self, direction: Direction) -> bool:
        return self.has_road(direction)

    @abstractmethod
    def has_city(self, direction: Direction) -> bool: ...

    def is_city(self, direction: Direction) -> bool:
        return self.has_city(direction)

    @abstractmethod
    def has_river(self, direction: Direction) -> bool: ...

    def is_river(self, direction: Direction) -> bool:
        return self.has_river(direction)

    @abstractmethod
    def has_monastery(self) -> bool: ...

    @abstractmethod
    def has_shield(self) -> bool: ...

    def connects_road(self, other: Piece, dir: Direction) -> bool:
        return self.has_road(dir) and other.has_road(dir.flip())

    def connects_city(self, other: Piece, dir: Direction) -> bool:
        return self.has_city(dir) and other.has_city(dir.flip())

    def connects_river(self, other: Piece, dir: Direction) -> bool:
        return self.has_river(dir) and other.has_river(dir.flip())

    def valid_beside(self, other: Piece, dir: Direction) -> bool:
        opp = dir.flip()

        if self.has_road(dir) != other.has_road(opp):
            return False

        if self.has_city(dir) != other.has_city(opp):
            return False

        if self.has_river(dir) != other.has_river(opp):
            return False

        return True


@dataclass
class Tile(Piece):
    kind: TileKind
    rotation: Angle
    __hash: int

    def __init__(self, kind: TileKind, rotation: Angle):
        self.kind = kind
        self.rotation = rotation
        self.__hash = hash((
            self.kind,
            self.has_monastery(),
            self.has_shield(),
            *(self.has_road(dir) for dir in Direction),
            *(self.has_city(dir) for dir in Direction),
            *(self.has_river(dir) for dir in Direction),
        ))

    @override
    def __hash__(self) -> int:
        return self.__hash

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Tile):
            return hash(self) == hash(other)

        return False

    @override
    def has_road(self, direction: Direction) -> bool:
        dir = direction.rotate(self.rotation, ccw=True)
        return dir in self.kind.roads

    @override
    def has_city(self, direction: Direction) -> bool:
        dir = direction.rotate(self.rotation, ccw=True)
        return any(dir in city for city in self.kind.cities)

    @override
    def has_river(self, direction: Direction) -> bool:
        dir = direction.rotate(self.rotation, ccw=True)
        return dir in self.kind.rivers

    @override
    def has_monastery(self) -> bool:
        return self.kind.monastery

    @override
    def has_shield(self) -> bool:
        return self.kind.shield

    @override
    def valid_beside(self, other: Piece, dir: Direction) -> bool:
        opp = dir.flip()

        if isinstance(other, Cell):
            if self.has_road(dir) and not other.has_road(opp):
                return False
            if self.has_city(dir) and not other.has_city(opp):
                return False
            if self.has_river(dir) and not other.has_river(opp):
                return False

            if other.is_road(opp) and not self.has_road(dir):
                return False
            if other.is_city(opp) and not self.has_city(dir):
                return False
            if other.is_river(opp) and not self.has_river(dir):
                return False
        else:
            if self.has_road(dir) != other.has_road(opp):
                return False

            if self.has_city(dir) != other.has_city(opp):
                return False

            if self.has_river(dir) != other.has_river(opp):
                return False

        return True


class Cell(Piece):
    pos: Pos
    map: Map

    # the set of possible tiles this cell could take, based only on validity (i.e.
    # connectedness) to its neighbours
    valid_options: set[Tile]

    # the last stage at which this cell was updated. used to prevent backtracking
    # in the iterative reduction process.
    stage: int

    # normally would just be all of the valid options, but we can override this
    # logic by implementing an EntropyDefinition, to e.g. weight the options, or
    # exclude some of them. this is stored here privately; it's precomputed, but
    # only w.r.t a given stage. it will need to be recomputed for later stages.
    __wave_function: set[tuple[Tile, int]]
    __wave_function_stage: int

    # caches the connection directions from this cell, according to its valid options
    __connect_road: dict[Direction, Ternary]
    __connect_city: dict[Direction, Ternary]
    __connect_river: dict[Direction, Ternary]

    # caches the stability of a cell
    __stable: bool

    def __init__(self, map: Map, pos: Pos, kinds: Iterable[TileKind]):
        self.map = map
        self.pos = pos
        self.stage = 0

        self.__wave_function_stage = -1
        self.__stable = False

        self.__connect_road = {dir: Ternary.Never for dir in Direction}
        self.__connect_city = {dir: Ternary.Never for dir in Direction}
        self.__connect_river = {dir: Ternary.Never for dir in Direction}

        self.valid_options = { Tile(k, a) for k in kinds for a in get_args(Angle) }
        self.recompute_connections()

    def __str__(self) -> str:
        if INFO <= DEBUG_LEVEL:
            roads = (str(dir) for dir in Direction if self.has_road(dir))
            cities = (str(dir) for dir in Direction if self.has_city(dir))
            rivers = (str(dir) for dir in Direction if self.has_river(dir))
            return f"Cell(stage {self.stage}; {len(self)} opts; roads: '{"".join(roads)}'; cities: '{"".join(cities)}'; rivers: '{"".join(rivers)}')"

        return f"Cell({len(self)} opts)"

    def __repr__(self) -> str:
        return str(self)

    def __len__(self) -> int:
        return len(self.valid_options)

    @property
    def is_stable(self) -> bool:
        return self.__stable

    @property
    def entropy(self) -> float:
        return self.map.wf_def.entropy(
            self.map, self.pos, self,
            self.wave_function
        )

    # get this cell's wave function (i.e. weighted possibilities) w.r.t its map
    # map. if already computed for the current stage, it will just be returned.
    # otherwise, it's computed and cached.
    #
    # also, if it's stable, the wave function is defined to just return the
    # tile which it has stabilised to
    @property
    def wave_function(self) -> set[tuple[Tile, int]]:
        if self.is_stable:
            return { (o, 1) for o in self.valid_options }

        if self.__wave_function_stage < self.map.latest:
            self.__wave_function = {
                (t, v) for t, v in self.map.wf_def.wave_function(self.map, self.pos, self)
                if v > 0
            }

            self.__wave_function_stage = self.map.latest

        return self.__wave_function

    def is_visible(self) -> bool:
        if self.is_stable:
            return True

        return any(other.is_stable for _, other in self.map.around(self.pos))

    def recompute_connections(self):
        for dir in Direction:
            n_road = len([ True for tile in self.valid_options if tile.has_road(dir) ])
            n_city = len([ True for tile in self.valid_options if tile.has_city(dir) ])
            n_river = len([ True for tile in self.valid_options if tile.has_river(dir) ])

            self.__connect_city[dir] = Ternary.Never if n_city == 0 else (Ternary.Must if n_city == len(self.valid_options) else Ternary.Maybe)
            self.__connect_road[dir] = Ternary.Never if n_road == 0 else (Ternary.Must if n_road == len(self.valid_options) else Ternary.Maybe)
            self.__connect_river[dir] = Ternary.Never if n_river == 0 else (Ternary.Must if n_river == len(self.valid_options) else Ternary.Maybe)

    @override
    def has_road(self, direction: Direction) -> bool:
        return self.__connect_road[direction] != Ternary.Never

    @override
    def is_road(self, direction: Direction) -> bool:
        return self.__connect_road[direction] == Ternary.Must

    @override
    def has_city(self, direction: Direction) -> bool:
        return self.__connect_city[direction] != Ternary.Never

    @override
    def is_city(self, direction: Direction) -> bool:
        return self.__connect_city[direction] == Ternary.Must

    @override
    def has_river(self, direction: Direction) -> bool:
        return self.__connect_river[direction] != Ternary.Never

    @override
    def is_river(self, direction: Direction) -> bool:
        return self.__connect_river[direction] == Ternary.Must

    @override
    def has_monastery(self) -> bool:
        return any(tile.has_monastery() for tile in self.valid_options)

    @override
    def has_shield(self) -> bool:
        return any(tile.has_shield() for tile in self.valid_options)

    def stabilise(self, tile: Tile) -> int:
        if tile in self.valid_options:
            old_len = len(self)
            self.valid_options = {tile}
            self.recompute_connections()
            self.__stable = True
            self.map.wf_def.take(self.map, self.pos, tile)
            return max(old_len - 1, 1)
        else:
            print(f"error: attempted to stabilise {self.pos} to invalid {tile.kind}")
            return 0

    # reduce the possibilities of this cell according to another cell, attached
    # to this one via the given direction. return the number of reductions made
    def reduce(self, other: Cell, dir: Direction) -> int:
        if self.is_stable:
            return 0

        old_len = len(self)
        self.valid_options.intersection_update([
            tile for tile in self.valid_options
            if tile.valid_beside(other, dir)
        ])

        self.recompute_connections()
        return old_len - len(self)


class Map:
    width: int
    height: int
    latest: int
    tileset: Tileset
    wf_def: WF

    _cells: list[list[Cell]]

    def __init__(self, width: int, height: int, tileset: Tileset):
        self.width = width
        self.height = height
        self._cells = [ [ Cell(self, Pos(x, y), tileset.kinds) for x in range(width) ] for y in range(height) ]
        self.latest = 0
        self.tileset = tileset
        self.wf_def = WF()

    @property
    def min(self) -> Pos:
        return Pos(0, 0)

    @property
    def max(self) -> Pos:
        return Pos(self.width-1, self.height-1)

    def __contains__(self, p: Pos) -> bool:
        return self.min <= p <= self.max

    @overload
    def __getitem__(self, p: Pos) -> Cell | None: ...
    @overload
    def __getitem__(self, p: tuple[int, int]) -> Cell | None: ...
    @overload
    def __getitem__(self, p: Iterable[Pos]) -> Generator[tuple[Pos, Cell]]: ...

    def __getitem__(self, p) -> Cell | Generator[tuple[Pos, Cell]] | None:
        if isinstance(p, Pos):
            if p in self:
                return self._cells[p.y][p.x]
        elif isinstance(p, tuple):
            return self[Pos(p[0], p[1])]
        elif isinstance(p, Iterable):
            return ((pos, cell) for pos in p if (cell := self[pos]))
        else:
            raise TypeError(f"Invalid key type for Map: {type(p)}")

    def __iter__(self) -> Iterator[tuple[Pos, Cell]]:
        return chain.from_iterable(
            [[ (Pos(x, y), c) for x, c in enumerate(row) ]
                for y, row in enumerate(self._cells) ])

    def bordering(self) -> Iterator[tuple[Pos, Cell]]:
        for pos, cell in self:
            if any(other.is_stable for _, other in self.around(pos)):
                yield pos, cell

    def visible(self) -> Iterator[tuple[Pos, Cell]]:
        for pos, cell in self:
            if cell.is_visible():
                yield pos, cell

    # faster, more direct entropy calculation for this simple case
    def entropy(self, map: Map, pos: Pos, cell: Cell) -> int:
        return len(cell)

    def draw(self, screen: pygame.Surface, scale: int, draw_extra: bool = True):
        entropies = {
            pos: cell.entropy for pos, cell in self.visible()
            if not cell.is_stable
        }

        for pos, cell in self.visible():
            dx, dy = self.screen_pos(pos, scale)
            p = Pos(dx, dy)
            shadow = self.tileset.shadows[scale]
            if cell.is_stable:
                shadow.set_alpha(60)
                screen.blit(shadow, p + Pos(2, 2))
            elif sum(w for _, w in cell.wave_function) > 0:
                shadow.set_alpha(30)
                sx, sy = sp = Pos(4, 4)
                screen.blit(shadow, p + sp, (sx, sy, scale-2, scale-2))

        for pos, cell in self.visible():
            wf = cell.wave_function
            total = sum(w for _, w in wf)
            dx, dy = dest = self.screen_pos(pos, scale)
            ins = 2

            for tile, w in wf:
                img = self.tileset.images[tile.kind.id, scale, tile.rotation]

                if cell.is_stable:
                    img.set_alpha(255)
                    screen.blit(img, dest)
                else:
                    img.set_alpha(int((w / total) * 220))
                    screen.blit(img, (dx+ins, dy+ins),
                        (ins-1, ins-1, scale-ins*2, scale-ins*2)
                    )


            if draw_extra:
                self.wf_def.draw_on_cell(self, pos, cell, entropies, dest, scale, screen)

        if draw_extra:
            self.wf_def.draw(self, entropies, scale, screen)

    def screen_pos(self, p: Pos, scale: int) -> Pos:
        return Pos(p.x, self.height - p.y - 1) * scale

    # the immediate neighbours of the cell at a position
    def around(self, p: Pos) -> Iterator[tuple[Direction, Cell]]:
        for dir in Direction:
            if cell := self[p + dir]:
                yield (dir, cell)

    # the immediate neighbours of the cell, grouped according to their staging.
    # we take the strictly newer ones than the given stage, and those which are
    # the same or older.
    def around_by_stage(self, p: Pos, stage: int) -> tuple[Iterable[tuple[Direction, Cell]], Iterable[tuple[Direction, Cell]]]:
        return (
            ((d, c) for (d, c) in self.around(p) if c.stage > stage),
            ((d, c) for (d, c) in self.around(p) if c.stage <= stage)
        )

    # take the cell at the given position, and a stage s.
    #  - if this cell is already at stage s, do nothing
    #  - update this cell's stage to be s
    #  - for all neighbours > stage s, reduce the possibilities of this
    #    cell to match with the newer neighbour
    #  - for all neighbours at the same stage or older, iteratively reduce
    #    them
    # returns the number of tile possibilities removed, and the number of tiles
    # visited (including this one).
    def reduce(self, p: Pos, stage: int, reductions: int = 0) -> tuple[int, int]:
        if not (this := self[p]):
            return reductions, 0

        visited = 1

        self.debug(f"stage {stage}: reducing {p}: {this}")

        this.stage = stage + 1

        newer, stale = self.around_by_stage(p, stage)
        for dir, other in newer:
            # other is a newer stage; update this to be consistent with it
            reductions += this.reduce(other, dir)

        if reductions > 0:
            for dir, other in stale:
                # other is the same or older than this; reduce it accordingly
                (r, v) = self.reduce(p + dir, stage)
                this.reduce(other, dir)
                reductions += r
                visited += v

        return (reductions, visited)

    # collapse the given cell to a set of possible options, and recursively
    #  reduce the rest of the board. updates the map's latest stage, and reduces
    #  based on this new stage.
    #
    # - impossible options (i.e. in the options argument but not an option of
    #   the cell) will be ignored.
    # - if we end up with no options, an error is raised.
    def collapse(self, p: Pos, chosen_tile: Tile | None = None) -> tuple[int, int]:
        if not (this := self[p]):
            return 0, 0

        if chosen_tile is None:
            # get the wave function for the cell (maybe compute it if it's dirty)
            # and then choose from it, weighted random.
            wf = this.wave_function
            if len(wf) == 0:
                self.debug(f"  no options to collapse {p}", INFO)
                return (0, 0)

            choices, weights = zip(*wf)
            chosen_tile = random.choices(choices, weights, k=1)[0]

        assert chosen_tile is not None

        if chosen_tile not in this.valid_options:
            raise ValueError(
                f"gave an option {chosen_tile} which is not a valid option,"
                f" at stage: {self.latest}, pos: {p}."
            )

        diff = this.stabilise(chosen_tile)

        self.latest += 1
        (reductions, visited) = self.reduce(p, self.latest, reductions=diff)

        self.wf_def.after_collapse(self, reductions)
        self.debug(f"collapsed. {reductions} reductions, visited {visited} tiles", INFO)

        return (reductions, visited)

    def collapse_min(self) -> tuple[int, int]:
        min_entropy = min((
            entropy
            for (_, cell) in self.bordering()

            # entropy <= -1 means that it has NO options
            if not cell.is_stable and (entropy := cell.entropy) > -1
        ), default=None)

        if min_entropy == None:
            self.wf_def.after_collapse(self, 0)
            self.latest += 1
            return (0, 0)

        minimum = [
            (pos, cell) for (pos, cell) in self.bordering()
            if not cell.is_stable and cell.entropy == min_entropy
        ]

        (pos, chosen_cell) = random.choice(minimum)
        self.debug(f"  {len(minimum)} cells to choose from, with entropy {min_entropy}", INFO)
        self.debug(f"  chosen {pos}, with {len(chosen_cell)} options", INFO)

        return self.collapse(pos)

    def collapse_random(self, k: float) -> tuple[int, int]:
        def f(e):
            try:
                return exp(-e * k)
            except OverflowError:
                return 1

        likelihoods = [
            (pos, entropy, f(entropy))
            for (pos, cell) in self.bordering()

            # entropy <= -1 means that it has NO options
            if not cell.is_stable and (entropy := cell.entropy) > -1
        ]

        for p, e, w in likelihoods:
            self.debug(f"pos {p}, entropy: {e}, weight: {w}", INFO)

        if len(likelihoods) == 0:
            self.wf_def.after_collapse(self, 0)
            self.latest += 1
            return (0, 0)

        xs, _, ps = zip(*likelihoods)
        pos = random.choices(xs, ps, k=1)[0]
        self.debug(f"  chosen {pos}", INFO)

        return self.collapse(pos)

    def show(self):
        for row in self._cells:
            for cell in row:
                print(f"{cell.stage},{len(cell):2d}", end="  ")
            print("\n")

    def debug(self, str, level: DebugLevel = DEBUG):
        if level <= DEBUG_LEVEL:
            print(str)
