import pygame

from geom import Pos
from tileset import Tileset
from wfc import WF, Map, Tile
from wave_functions import CityBuilder, LargeCities, DebugOverlay, Deck, Opportunistic, RealDeck, RoadBuilder, WeLikeConnections, Yas


W, H = 32, 32
SCREEN_W = 800
BACKGROUND = "tan"
# BACKGROUND = (83, 182, 95) # the background of the tiles
CROP = True


def main():
    screen_h = SCREEN_W * (H / W)
    tile_size = SCREEN_W // W

    # tiles = Tileset(Tileset.BaseTiles + Tileset.Rivers)
    tiles = Tileset(Tileset.BaseTiles)
    tiles.cache_images(tile_size, crop_inset=58 if CROP else 0)

    map = Map(W, H, tiles)
    # map.wf_def = CityBuilder(map.wf_def)
    # map.wf_def = Deck(WF(), tiles, decks=2)
    # map.wf_def = CityBuilder(Deck(WF(), tiles, decks=3))
    map.wf_def = RealDeck(Deck(map.wf_def, tiles, decks=3, infinite=False))
    map.wf_def = CityBuilder(map.wf_def, draw=False)
    map.wf_def = RoadBuilder(map.wf_def, draw=False)
    # map.wf_def = Yas(map.wf_def)
    map.wf_def = Opportunistic(map.wf_def)
    map.wf_def = DebugOverlay(map.wf_def)

    map.collapse(Pos(int(W * 0.5), int(H * 0.5)), Tile(tiles.get_by_name("u.lr"), 0))

    screen = pygame.display.set_mode((SCREEN_W, screen_h))
    pygame.display.set_caption("Carcassonne!")
    clock = pygame.time.Clock()
    running = True
    auto = False

    screen.fill(BACKGROUND)
    map.draw(screen, tile_size)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    auto = not auto
                elif event.key == pygame.K_RETURN:
                    step(screen, map, tile_size)

        if auto:
            step(screen, map, tile_size)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def step(screen: pygame.Surface, map: Map, tile_size: int):
    map.collapse_min()
    screen.fill(BACKGROUND)
    map.draw(screen, tile_size)

if __name__ == "__main__":
    main()
