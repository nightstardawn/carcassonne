import pygame

from geom import Pos
from tileset import Tileset
from wfc import INFO, WF, Map, Tile
from wave_functions import CityBuilder, LargeCities, DebugOverlay, Deck, Opportunistic, RealDeck, RiverBuilder, RiversFirst, RoadBuilder, WeLikeConnections, Yas


W, H = 25, 25

SCREEN_W = 800
SCREEN_H = SCREEN_W * (H / W)
MARGIN = 64
BACKGROUND = "tan"
BORDER = "wheat2"
CROP = True
RANDOM_K = -100


def setup_wave_function() -> WF:
    global deck

    wf = WF()

    deck = Deck(
        WF(), tiles,
        decks=1, infinite=True, infinite_rivers=False,
        hint_scale=55
    )

    wf = deck
    wf = RealDeck(wf)

    wf = CityBuilder(wf, draw=False)
    wf = RoadBuilder(wf, draw=False)
    # wf = RiverBuilder(wf, draw=False)

    wf = Opportunistic(wf, weight=1.0 / (len(tiles.kinds) * 4))
    wf = DebugOverlay(wf)

    return wf


def main(screen: pygame.Surface) -> bool:
    tile_size = SCREEN_W // W
    collapse_random = False
    draw_extra = True

    map = Map(W, H, tiles)
    map.wf_def = setup_wave_function()

    try:
        initial = tiles.get_by_name("u.lr")
        # initial = tiles.get_by_name("river-d")
    except StopIteration:
        initial = tiles.get_by_name("-.lr")

    map.collapse(
        Pos(int(W * 0.5), int(H * 0.5)),
        Tile(initial, 0),
    )

    clock = pygame.time.Clock()
    auto = False

    draw(screen, map, tile_size, draw_extra)

    frame_times = []

    exit_with = None
    while exit_with is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_with = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    auto = not auto
                elif event.key == pygame.K_RETURN:
                    step(screen, map, tile_size, collapse_random, draw_extra)
                elif event.key == pygame.K_ESCAPE:
                    exit_with = True
                elif event.key == pygame.K_p:
                    collapse_random = not collapse_random
                    pygame.display.set_caption("Carcassonne!" + (f" (Random collapsing, k={RANDOM_K})" if collapse_random else ""))
                elif event.key == pygame.K_r:
                    deck.reset()
                    map.latest += 1
                elif event.key == pygame.K_d:
                    draw_extra = not draw_extra

                draw(screen, map, tile_size, draw_extra)

        if auto:
            step(screen, map, tile_size, collapse_random, draw_extra)

        pygame.display.flip()

        frame_times.append(clock.tick(60))
        if sum(frame_times) >= 2500:
            fps = round(1000 / (sum(frame_times) / len(frame_times)))
            frame_times = []
            map.debug(f"fps: {fps}", INFO)

    return exit_with


def step(screen: pygame.Surface, map: Map, tile_size: int, random: bool, draw_extra: bool):
    if random:
        map.collapse_random(RANDOM_K)
    else:
        map.collapse_min()

    draw(screen, map, tile_size, draw_extra)


def draw(screen: pygame.Surface, map: Map, tile_size: int, draw_extra: bool):
    screen.fill(BACKGROUND)
    screen.blit(background, (0, 0), (0, 0, SCREEN_W, SCREEN_H))
    map.draw(screen, tile_size, draw_extra)


def init() -> pygame.Surface:
    global background
    global tiles

    screen = pygame.display.set_mode((SCREEN_W + MARGIN * 2, SCREEN_H + MARGIN * 2))
    pygame.display.set_caption("Carcassonne!")

    background = pygame.image.load("oak.bmp").convert()
    background.set_alpha(60)

    tile_size = SCREEN_W // W
    tiles = Tileset(
        Tileset.RoadTiles
        + Tileset.CityTiles
        # + Tileset.Rivers
    )
    tiles.cache_images(tile_size, crop_inset=58 if CROP else 0)

    return screen


if __name__ == "__main__":
    screen = init()
    screen.fill(BACKGROUND)
    pygame.draw.rect(screen, BORDER, (MARGIN-4, MARGIN-4, SCREEN_W+8, SCREEN_H+8))

    sub_screen = screen.subsurface((MARGIN, MARGIN, SCREEN_W, SCREEN_H))

    while True:
        try:
            if not main(sub_screen):
                break
        except KeyboardInterrupt:
            break

    pygame.quit()
