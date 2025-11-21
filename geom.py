from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Literal, Sequence, overload, override


Angle = Literal[0, 1, 2, 3]


class Direction(Enum):
    Up = (0, 1)
    Down = (0, -1)
    Left = (-1, 0)
    Right = (1, 0)

    @property
    def x(self) -> Literal[-1, 0, 1]:
        return self.value[0]

    @property
    def y(self) -> Literal[-1, 0, 1]:
        return self.value[1]

    def __str__(self) -> str:
        match self:
            case Direction.Up:
                return "U"
            case Direction.Right:
                return "R"
            case Direction.Down:
                return "D"
            case Direction.Left:
                return "L"

    def __repr__(self) -> str:
        return str(self)

    def rotate(self, angle: Angle, ccw: bool = False) -> Direction:
        if ccw:
            angle = -angle % 4

        match angle:
            case 0:
                return self
            case 1:
                return {
                    Direction.Up: Direction.Right,
                    Direction.Right: Direction.Down,
                    Direction.Down: Direction.Left,
                    Direction.Left: Direction.Up,
                }[self]
            case n:
                return self.rotate(1).rotate(n - 1)

    def flip(self) -> Direction:
        return self.rotate(2)


U, D, L, R = Direction.Up, Direction.Down, Direction.Left, Direction.Right


@dataclass
class Pos(Sequence[float]):
    x: int
    y: int

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __len__(self) -> int:
        return 2

    def __getitem__(self, ix):
        return [self.x, self.y][ix]

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    @overload
    def __add__(self, other: Direction) -> Pos: ...
    @overload
    def __add__(self, other: Sequence[float]) -> Pos: ...

    def __add__(self, other: Direction | Sequence[float]) -> Pos:
        if isinstance(other, Direction):
            return Pos(self.x + other.x, self.y + other.y)
        elif isinstance(other, Sequence):
            return Pos(self.x + int(other[0]), self.y + int(other[1]))

    def __mul__(self, other: int) -> Pos:
        return Pos(self.x * other, self.y * other)

    def __rmul__(self, other: int) -> Pos:
        return Pos(self.x * other, self.y * other)

    def __le__(self, other: Pos | tuple[int, int]) -> bool:
        if isinstance(other, Pos):
            return self.x <= other.x and self.y <= other.y
        else:
            return self.x <= other[0] and self.y <= other[1]

    def __lt__(self, other: Pos | tuple[int, int]) -> bool:
        if isinstance(other, Pos):
            return self.x < other.x and self.y < other.y
        else:
            return self.x < other[0] and self.y < other[1]

    def __iter__(self) -> Iterator[int]:
        yield self.x
        yield self.y
