import pygame

from geom import Pos
from tileset import Tileset
from wfc import WF, Map, Tile
from wave_functions import CityBuilder, Deck, RealDeck


def main():
    w, h = 16, 16
    screen_size = 800
    tile_size = screen_size // w

    tiles = Tileset()
    tiles.cache_images(tile_size)

    map = Map(w, h, tiles)
    map.entropy_def = RealDeck(Deck(WF(), tiles, decks=2))
    # map.entropy_def = CityBuilder(WF())
    # map.entropy_def = Deck(WF(), tiles, decks=2)
    # map.entropy_def = CityBuilder(Deck(WF(), tiles, decks=3))
    map.collapse(Pos(w // 2, h // 2), Tile(tiles.get_by_name("u.lr"), 0))

    screen = pygame.display.set_mode((screen_size, screen_size))
    pygame.display.set_caption("Carcassonne!")
    clock = pygame.time.Clock()
    running = True
    auto = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    auto = not auto
                elif event.key == pygame.K_RETURN:
                    map.collapse_min()

        if auto:
            map.collapse_min()

        screen.fill("tan")
        # screen.fill((83, 182, 95))
        map.draw(screen, tile_size)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
