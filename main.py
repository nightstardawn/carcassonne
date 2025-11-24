import pygame

from geom import Pos
from tileset import Tileset
from wfc import INFO, WF, Map, Tile
from wave_functions import CityBuilder, LargeCities, DebugOverlay, Deck, Opportunistic, RealDeck, RiverBuilder, RiversFirst, RoadBuilder, WeLikeConnections, Yas


W, H = 32, 32
# W, H = 20, 20
SCREEN_W = 800
BACKGROUND = "tan"   # BACKGROUND = (83, 182, 95) # the background of the tiles
CROP = True
RANDOM_K = 50


def main(screen: pygame.Surface) -> bool:
    tile_size = SCREEN_W // W
    collapse_random = False
    draw_extra = True

    tiles = Tileset(
        Tileset.BaseTiles
        + Tileset.Rivers
    )
    tiles.cache_images(tile_size, crop_inset=58 if CROP else 0)

    map = Map(W, H, tiles)

    deck = Deck(
        WF(), tiles,
        decks=1, infinite=True, infinite_rivers=False,
        hint_scale=50
    )

    map.wf_def = deck
    map.wf_def = RealDeck(deck)

    # map.wf_def = CityBuilder(map.wf_def, draw=False)
    # map.wf_def = RoadBuilder(map.wf_def, draw=False)
    # map.wf_def = RiverBuilder(map.wf_def, draw=False)

    # map.wf_def = Opportunistic(map.wf_def)
    map.wf_def = DebugOverlay(map.wf_def)

    map.collapse(
        Pos(int(W * 0.5), int(H * 0.5)),
        Tile(tiles.get_by_name("u.lr"), 0),
        # Tile(tiles.get_by_name("river-d"), 0),
    )

    clock = pygame.time.Clock()
    auto = False

    screen.fill(BACKGROUND)
    map.draw(screen, tile_size)

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

                screen.fill(BACKGROUND)
                map.draw(screen, tile_size, draw_extra)

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

    screen.fill(BACKGROUND)
    map.draw(screen, tile_size, draw_extra)

if __name__ == "__main__":
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_W * (H / W)))
    pygame.display.set_caption("Carcassonne!")

    while True:
        if not main(screen):
            break

    pygame.quit()
