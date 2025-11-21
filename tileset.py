from dataclasses import dataclass, field
from typing import get_args, override
import pygame

from geom import U, R, D, L, Angle, Direction

pygame.init()

@dataclass
class TileKind:
    img_src: str
    id: int = field(default_factory=lambda: TileKind._get_id())
    roads: set[Direction] = field(default_factory=set)
    cities: list[set[Direction]] = field(default_factory=list)
    monastery: bool = field(default=False)
    shield: bool = field(default=False)

    _next_id: int = 0

    @override
    def __hash__(self) -> int:
        return self.id

    @staticmethod
    def _get_id() -> int:
        TileKind._next_id += 1
        return TileKind._next_id

class Tileset:
    kinds: list[TileKind]
    images: dict[tuple[int, Angle], pygame.Surface]

    __ALL_TILE_TYPES: list[TileKind] = [
        TileKind(img_src="m", monastery=True),

        TileKind(img_src="u", cities=[{U}]),
        TileKind(img_src="u-d", cities=[{U}, {D}]),
        TileKind(img_src="u-r", cities=[{U}, {R}]),
        TileKind(img_src="lr", cities=[{L, R}]),
        TileKind(img_src="lr.s", cities=[{L, R}], shield=True),
        TileKind(img_src="ur", cities=[{U, R}]),
        TileKind(img_src="ur.s", cities=[{U, R}], shield=True),
        TileKind(img_src="ulr", cities=[{U, L, R}]),
        TileKind(img_src="ulr.s", cities=[{U, L, R}], shield=True),
        TileKind(img_src="udlr.s", cities=[{U, D, L, R}], shield=True),

        TileKind(img_src="m.d", roads={D}, monastery=True),
        TileKind(img_src="ulr.d", roads={D}, cities=[{U, L, R}]),
        TileKind(img_src="ulr.s.d", roads={D}, cities=[{U, L, R}], shield=True),

        TileKind(img_src="-.lr", roads={L, R}),
        TileKind(img_src="-.ld", roads={L, D}),
        TileKind(img_src="u.lr", roads={L, R}, cities=[{U}]),
        TileKind(img_src="u.ld", roads={L, D}, cities=[{U}]),
        TileKind(img_src="u.rd", roads={R, D}, cities=[{U}]),
        TileKind(img_src="ur.ld", roads={L, D}, cities=[{U, R}]),
        TileKind(img_src="ur.s.ld", roads={L, D}, cities=[{U, R}], shield=True),

        TileKind(img_src="-.lrd", roads={L, R, D}),
        TileKind(img_src="u.lrd", roads={L, R, D}, cities=[{U}]),
        TileKind(img_src="-.ulrd", roads={U, L, R, D}),
    ]

    def __init__(self, kinds: list[TileKind] = __ALL_TILE_TYPES):
        self.kinds = kinds
        self.images = {}

    @property
    def num_tiles(self) -> int:
        return len(self.kinds) * 4

    def get_by_name(self, name: str) -> TileKind:
        return next(kind for kind in self.kinds if kind.img_src == name)

    def __getitem__(self, id: int) -> TileKind:
        return next(kind for kind in self.kinds if kind.id == id)

    def cache_images(self, scale: int, crop_inset: int = 0):
        for kind in self.kinds:
            base = pygame.image.load(f"tiles/{kind.img_src}.bmp")

            if crop_inset > 0:
                w, h = base.get_size()
                base = base.subsurface((crop_inset, crop_inset, w-crop_inset*2, h-crop_inset*2))

            scaled = pygame.transform.smoothscale(base, (scale, scale))
            for angle in get_args(Angle):
                rotated = pygame.transform.rotate(scaled, -angle * 90)
                self.images[kind.id, angle] = rotated
