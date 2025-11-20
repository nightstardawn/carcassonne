import pygame

from geom import Pos
from tileset import Tileset
from wfc import Map, Tile
from entropy import CityBuilder, Deck, RealDeck, frequencies


def main():
    w, h = 32, 32
    screen_size = 800
    tile_size = screen_size // w

    tiles = Tileset()
    tiles.cache_images(tile_size)

    map = Map(w, h, tiles)
    # map.entropy_def = Deck(tiles, frequencies(numdecks=4))
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

        # screen.fill((83, 182, 95))
        screen.fill("tan")
        map.draw(screen, tile_size)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
