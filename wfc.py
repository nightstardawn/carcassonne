from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import chain
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


class WF:
    def wave_function(self, map: Map, pos: Pos, cell: Cell) -> set[tuple[Tile, int]]:
        return { (o, 1) for o in cell.valid_options }

    def take(self, map: Map, tile: Tile):
        pass

    def new_stage(self, map: Map):
        pass

    def draw(self, map: Map, screen: pygame.Surface):
        pass

    def draw_on_cell(self, map: Map, pos: Pos, cell: Cell, screen_pos: Pos, screen: pygame.Surface):
        pass


class Piece(ABC):
    @abstractmethod
    def has_road(self, direction: Direction) -> bool: ...

    @abstractmethod
    def has_city(self, direction: Direction) -> bool: ...

    @abstractmethod
    def has_monastery(self) -> bool: ...

    @abstractmethod
    def has_shield(self) -> bool: ...

    def valid_beside(self, other: Piece, dir: Direction) -> bool:
        opp = dir.flip()

        if self.has_road(dir) != other.has_road(opp):
            return False

        if self.has_city(dir) != other.has_city(opp):
            return False

        return True


@dataclass
class Tile(Piece):
    kind: TileKind
    rotation: Angle

    @override
    def __hash__(self) -> int:
        return hash(self.kind) * 4 + self.rotation

    def has_road(self, direction: Direction) -> bool:
        dir = direction.rotate(self.rotation, ccw=True)
        return dir in self.kind.roads

    def has_city(self, direction: Direction) -> bool:
        dir = direction.rotate(self.rotation, ccw=True)
        return any(dir in city for city in self.kind.cities)

    def has_monastery(self) -> bool:
        return self.kind.monastery

    def has_shield(self) -> bool:
        return self.kind.shield


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

    # caches the stability of a cell
    __stable: bool

    def __init__(self, map: Map, pos: Pos, kinds: Iterable[TileKind]):
        self.map = map
        self.pos = pos
        self.valid_options = { Tile(k, a) for k in kinds for a in get_args(Angle) }
        self.stage = 0
        self.__wave_function_stage = -1
        self.__stable = False

    def __str__(self) -> str:
        roads = (str(dir) for dir in Direction if self.has_road(dir))
        cities = (str(dir) for dir in Direction if self.has_city(dir))
        return f"Cell(stage {self.stage}; {len(self)} opts; roads: '{"".join(roads)}'; cities: '{"".join(cities)}')"

    def __repr__(self) -> str:
        return str(self)

    def __len__(self) -> int:
        return len(self.valid_options)

    @property
    def is_stable(self) -> bool:
        return len(self) <= 1

    @property
    def entropy(self) -> int:
        return sum(w for _, w in self.wave_function)

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
                (t, v) for t, v in self.map.entropy_def.wave_function(self.map, self.pos, self)
                if v > 0
            }

            self.__wave_function_stage = self.map.latest

        return self.__wave_function

    def has_road(self, direction: Direction) -> bool:
        return any(tile.has_road(direction) for tile in self.valid_options)

    def has_city(self, direction: Direction) -> bool:
        return any(tile.has_city(direction) for tile in self.valid_options)

    def has_monastery(self) -> bool:
        return any(tile.has_monastery() for tile in self.valid_options)

    def has_shield(self) -> bool:
        return any(tile.has_shield() for tile in self.valid_options)

    # reduce the possibilities of this cell according to another cell, attached
    # to this one via the given direction. return the number of reductions made
    def reduce(self, other: Cell, dir: Direction) -> int:
        if self.is_stable:
            return 0

        old_len = len(self)
        self.valid_options = {
            tile for tile in self.valid_options
            if any(tile.valid_beside(other_tile, dir) for other_tile in other.valid_options)
        }
        return old_len - len(self)


class Map:
    width: int
    height: int
    latest: int
    tileset: Tileset
    entropy_def: WF

    _cells: list[list[Cell]]

    def __init__(self, width: int, height: int, tileset: Tileset):
        self.width = width
        self.height = height
        self._cells = [ [ Cell(self, Pos(x, y), tileset.kinds) for x in range(width) ] for y in range(height) ]
        self.latest = 0
        self.tileset = tileset
        self.entropy_def = WF()

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

    # faster, more direct entropy calculation for this simple case
    def entropy(self, map: Map, pos: Pos, cell: Cell) -> int:
        return len(cell)

    def draw(self, screen: pygame.Surface, scale: int):
        for pos, cell in self:
            if len(cell) == self.tileset.num_tiles:
                # don't draw tiles in full superposition
                continue

            wf = cell.wave_function
            entropy = cell.entropy

            dest = self.screen_pos(pos, scale)
            for tile, w in wf:
                img = self.tileset.images[tile.kind.id, tile.rotation]

                if cell.is_stable:
                    img.set_alpha(255)
                elif entropy > 0:
                    img.set_alpha((w * 128) // entropy)
                else:
                    # should never happen
                    print(f"weird!\n  entropy = {entropy} at {pos}\n  with wf: {wf}\n  but it's not stable\n  with possible: {cell.valid_options}")
                    img.set_alpha((w * 64) // (entropy+1))

                screen.blit(img, tuple(dest))

        self.entropy_def.draw(self, screen)

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
            self.debug(f"  {p}+{dir} is newer (@{other.stage})")
            reductions += this.reduce(other, dir)

        if reductions > 0:
            for dir, other in stale:
                # other is the same or older than this; reduce it accordingly
                self.debug(f"  {p}+{dir} is stale")
                (r, v) = self.reduce(p + dir, stage)
                this.reduce(other, dir)
                reductions += r
                visited += v
        else:
            self.debug(f"  no reductions at {p}, so skipping stale neighbours")

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

        if chosen_tile not in this.valid_options:
            raise ValueError(
                f"gave an option {chosen_tile} which is not a valid option,"
                f" at stage: {self.latest}, pos: {p}."
            )

        old_len = len(this)
        this.valid_options = {chosen_tile}
        self.entropy_def.take(self, chosen_tile)

        diff = old_len - len(this)

        self.latest += 1
        self.entropy_def.new_stage(self)
        self.debug(f"collapsing, stage {self.latest}", INFO)

        (reductions, visited) = self.reduce(p, self.latest, reductions=diff)
        self.debug(f"collapsed. {reductions} reductions, visited {visited} tiles", INFO)

        return (reductions, visited)

    def collapse_min(self) -> tuple[int, int]:
        min_entropy = min((
            entropy
            for (pos, cell) in self.bordering()
            # if not cell.is_stable and (entropy := self.entropy_def.entropy(self, pos, cell)) > 0
            if not cell.is_stable and (entropy := cell.entropy) > 0
        ), default=None)

        if min_entropy == None:
            self.entropy_def.new_stage(self)
            self.latest += 1
            return (0, 0)


        minimum = [
            (pos, cell) for (pos, cell) in self.bordering()
            # if not cell.is_stable and self.entropy_def.entropy(self, pos, cell) == min_entropy
            if not cell.is_stable and cell.entropy == min_entropy
        ]

        (pos, chosen_cell) = random.choice(minimum)
        self.debug(f"{len(minimum)} cells to choose from, with entropy {min_entropy}", INFO)
        self.debug(f"  chosen {pos}, with {len(chosen_cell)} options", INFO)

        return self.collapse(pos)

    def show(self):
        for row in self._cells:
            for cell in row:
                print(f"{cell.stage},{len(cell):2d}", end="  ")
            print("\n")

    def debug(self, str, level: DebugLevel = DEBUG):
        if level <= DEBUG_LEVEL:
            print(str)


test_map = Map(5, 5, Tileset())
