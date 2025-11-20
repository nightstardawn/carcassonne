from dataclasses import dataclass
from enum import Enum
from itertools import chain
from random import choice
from typing import Generator, Iterable, get_args, overload, override
import pygame
from pygame.rect import Rect

from tileset import TileKind, Tileset
from geom import *

DebugLevel = Literal[0, 1, 2]
QUIET: DebugLevel = 0
INFO: DebugLevel = 1
DEBUG: DebugLevel = 2

DEBUG_LEVEL = QUIET

@dataclass
class Tile:
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

    # does this tile connect to the other tile, if we were to place the other
    # tile on the given side of this one?
    def connects(self, other: Tile, dir: Direction) -> bool:
        opp = dir.flip()

        if self.has_road(dir) != other.has_road(opp):
            return False

        if self.has_city(dir) != other.has_city(opp):
            return False

        return True


class Cell:
    options: set[Tile]
    stage: int

    def __init__(self, kinds: Iterable[TileKind]):
        self.options = { Tile(k, a) for k in kinds for a in get_args(Angle) }
        self.stage = 0

    def __str__(self) -> str:
        roads = (str(dir) for dir in Direction if self.has_road(dir))
        cities = (str(dir) for dir in Direction if self.has_city(dir))
        return f"Cell(stage {self.stage}; {self.len} opts; roads: '{"".join(roads)}'; cities: '{"".join(cities)}')"

    def __repr__(self) -> str:
        return str(self)

    @property
    def len(self) -> int:
        return len(self.options)

    @property
    def is_stable(self) -> bool:
        return self.len <= 1

    def has_road(self, direction: Direction) -> bool:
        return any(tile.has_road(direction) for tile in self.options)

    def has_city(self, direction: Direction) -> bool:
        return any(tile.has_city(direction) for tile in self.options)

    def has_monastery(self) -> bool:
        return any(tile.has_monastery() for tile in self.options)

    def has_shield(self) -> bool:
        return any(tile.has_shield() for tile in self.options)

    # reduce the possibilities of this cell according to another cell, attached
    # to this one via the given direction. return the number of reductions made
    def reduce(self, other: Cell, dir: Direction) -> int:
        old_len = self.len
        self.options = {
            tile for tile in self.options
            if any(tile.connects(other_tile, dir) for other_tile in other.options)
        }
        return old_len - self.len


class Map:
    width: int
    height: int
    latest: int

    tileset: Tileset

    _cells: list[list[Cell]]

    def __init__(self, width: int, height: int, tileset: Tileset):
        self.width = width
        self.height = height
        self._cells = [ [ Cell(tileset.kinds) for _ in range(width) ] for _ in range(height) ]
        self.latest = 0
        self.tileset = tileset

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

    def draw(self, screen: pygame.Surface, scale: int):
        for pos, cell in self:
            if cell.len == self.tileset.num_tiles:
                # don't draw tiles in full superposition
                continue

            dest = self.screen_pos(pos, scale)
            for tile in list(cell.options):
                img = self.tileset.images[tile.kind._id, tile.rotation]
                img.set_alpha(int(255 / cell.len))
                screen.blit(img, tuple(dest))

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
    def collapse(self, p: Pos, option: Tile | set[Tile]) -> tuple[int, int]:
        if not (this := self[p]):
            return 0, 0

        if isinstance(option, Tile):
            option = {option}

        old_num = this.len
        this.options &= option
        if this.len == 0:
            raise ValueError(f"collapsed cell at {p} to zero options!")

        diff = old_num - this.len

        self.latest += 1
        self.debug(f"collapsing, stage {self.latest}", INFO)
        (reductions, visited) = self.reduce(p, self.latest, reductions=diff)
        self.debug(f"collapsed. {reductions} reductions, visited {visited} tiles", INFO)
        return (reductions, visited)

    def collapse_min(self) -> tuple[int, int]:
        min_cell = min(
            (cell for (_, cell) in self if not cell.is_stable),
            key=lambda k: k.len,
            default=None)

        if min_cell == None:
            self.debug("all cells are fully collapsed already", DEBUG)
            return (0, 0)

        minimum = [ (pos, cell) for (pos, cell) in self if cell.len == min_cell.len]
        self.debug(f"{len(minimum)} cells to choose from, with entropy {min_cell.len}", INFO)

        (pos, cell) = choice(minimum)
        chosen_tile = choice(list(cell.options))
        self.debug(f"  chosen {pos}, with {cell.len} options", INFO)
        self.debug(f"  chosen tile: {chosen_tile}", INFO)

        return self.collapse(pos, chosen_tile)

    def show(self):
        for row in self._cells:
            for cell in row:
                print(f"{cell.stage},{cell.len:2d}", end="  ")
            print("\n")

    def debug(self, str, level: DebugLevel = DEBUG):
        if level <= DEBUG_LEVEL:
            print(str)


test_map = Map(5, 5, Tileset())
