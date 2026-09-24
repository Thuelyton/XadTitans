"""XadTitans - ponto de entrada.

Abre a janela principal (1024x768) e fecha com Esc ou no X da janela.
"""

import sys

import pygame

TITLE = "XadTitans"
WIDTH = 1024
HEIGHT = 768
FPS = 30


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill((16, 20, 26))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
