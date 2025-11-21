from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Literal


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
class Pos:
    x: int
    y: int

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __add__(self, other: Direction) -> Pos:
        return Pos(self.x + other.x, self.y + other.y)

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
