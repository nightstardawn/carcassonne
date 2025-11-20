from dataclasses import dataclass, field
from typing import get_args, override
import pygame

from geom import U, R, D, L, Angle, Direction

pygame.init()

@dataclass
class TileKind:
    img_src: str
    _id: int = field(default_factory=lambda: TileKind._get_id())
    roads: set[Direction] = field(default_factory=set)
    cities: list[set[Direction]] = field(default_factory=list)
    monastery: bool = field(default=False)
    shield: bool = field(default=False)

    _next_id: int = 0

    @override
    def __hash__(self) -> int:
        return self._id

    @staticmethod
    def _get_id() -> int:
        TileKind._next_id += 1
        return TileKind._next_id

class Tileset:
    kinds: list[TileKind]
    images: dict[tuple[int, Angle], pygame.Surface]

    __ALL_TILE_TYPES: list[TileKind] = [
        TileKind(img_src="tiles/m.bmp", monastery=True),

        TileKind(img_src="tiles/u.bmp", cities=[{U}]),
        TileKind(img_src="tiles/u-d.bmp", cities=[{U}, {D}]),
        TileKind(img_src="tiles/u-r.bmp", cities=[{U}, {R}]),
        TileKind(img_src="tiles/lr.bmp", cities=[{L, R}]),
        TileKind(img_src="tiles/lr.s.bmp", cities=[{L, R}], shield=True),
        TileKind(img_src="tiles/ur.bmp", cities=[{U, R}]),
        TileKind(img_src="tiles/ur.s.bmp", cities=[{U, R}], shield=True),
        TileKind(img_src="tiles/ulr.bmp", cities=[{U, L, R}]),
        TileKind(img_src="tiles/ulr.s.bmp", cities=[{U, L, R}], shield=True),
        TileKind(img_src="tiles/udlr.s.bmp", cities=[{U, D, L, R}], shield=True),

        TileKind(img_src="tiles/m.d.bmp", roads={D}, monastery=True),
        TileKind(img_src="tiles/ulr.d.bmp", roads={D}, cities=[{U, L, R}]),
        TileKind(img_src="tiles/ulr.s.d.bmp", roads={D}, cities=[{U, L, R}], shield=True),

        TileKind(img_src="tiles/-.lr.bmp", roads={L, R}),
        TileKind(img_src="tiles/-.ld.bmp", roads={L, D}),
        TileKind(img_src="tiles/u.lr.bmp", roads={L, R}, cities=[{U}]),
        TileKind(img_src="tiles/u.ld.bmp", roads={L, D}, cities=[{U}]),
        TileKind(img_src="tiles/u.rd.bmp", roads={R, D}, cities=[{U}]),
        TileKind(img_src="tiles/ur.ld.bmp", roads={L, D}, cities=[{U, R}]),
        TileKind(img_src="tiles/ur.s.ld.bmp", roads={L, D}, cities=[{U, R}], shield=True),

        TileKind(img_src="tiles/-.lrd.bmp", roads={L, R, D}),
        TileKind(img_src="tiles/u.lrd.bmp", roads={L, R, D}, cities=[{U}]),
        TileKind(img_src="tiles/-.ulrd.bmp", roads={U, L, R, D}),
    ]

    def __init__(self, kinds: list[TileKind] = __ALL_TILE_TYPES):
        self.kinds = kinds
        self.images = {}

    @property
    def num_tiles(self) -> int:
        return len(self.kinds) * 4

    def cache_images(self, scale: int):
        for kind in self.kinds:
            base = pygame.image.load(kind.img_src)
            scaled = pygame.transform.smoothscale(base, (scale, scale))
            for angle in get_args(Angle):
                rotated = pygame.transform.rotate(scaled, -angle * 90)
                self.images[kind._id, angle] = rotated
