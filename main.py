"""
main.py — Entry point for the Campfire Simulator.
Run with: python main.py
"""
import sys
import pygame

SCREEN_W = 800
SCREEN_H = 600
TITLE    = "Костёр — Симулятор разжигания костра"


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))

    # Import here so pygame.init() runs first (font system must be ready)
    from game import Game
    game = Game(screen)
    game.run()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
