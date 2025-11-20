import pygame

from geom import Pos
from tileset import Tileset
from wfc import Map, Tile

def main():
    w, h = 32, 32
    screen_size = 800
    tile_size = screen_size // w

    tiles = Tileset()
    tiles.cache_images(tile_size)

    map = Map(w, h, tiles)

    screen = pygame.display.set_mode((screen_size, screen_size))
    pygame.display.set_caption("Carcassonne!")
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        map.collapse_min()

        screen.fill("tan")
        map.draw(screen, tile_size)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
