"""
textures.py — Texture manager for Campfire Simulator.
Loads custom PNG textures from assets/textures/ if provided by the user,
or dynamically creates detailed retro pixel-art sprites with shading and wood grain.
"""
import pygame
import os

TEXTURES_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'textures')
os.makedirs(TEXTURES_DIR, exist_ok=True)

class TextureManager:
    _cache = {}

    @classmethod
    def get(cls, name: str, default_size=(48, 48)) -> pygame.Surface:
        """Returns loaded PNG texture from assets/textures/ or generated retro pixel-art sprite."""
        if name in cls._cache:
            return cls._cache[name]

        # 1. Попытка загрузить пользовательскую текстуру PNG
        png_path = os.path.join(TEXTURES_DIR, f"{name}.png")
        if os.path.isfile(png_path):
            try:
                surf = pygame.image.load(png_path).convert_alpha()
                cls._cache[name] = surf
                return surf
            except Exception as e:
                print(f"Failed to load {png_path}: {e}")

        # 2. Если файла нет — создаём красивый детальный ретро пиксель-арт спрайт
        surf = cls._generate_retro_sprite(name, default_size)
        cls._cache[name] = surf
        return surf

    @classmethod
    def _generate_retro_sprite(cls, name: str, size: tuple) -> pygame.Surface:
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        if name == 'tinder':
            # Свиток белой бересты с чёрными черточками берёзовой коры
            pygame.draw.ellipse(surf, (235, 222, 195), (4, 8, w - 8, h - 16))
            pygame.draw.ellipse(surf, (190, 175, 145), (4, 8, w - 8, h - 16), 2)
            for i in range(5):
                pygame.draw.line(surf, (50, 42, 35), (10 + i * 7, 14 + (i % 3) * 6),
                                 (16 + i * 7, 14 + (i % 3) * 6), 2)

        elif name == 'kindling':
            # Связка тонких сухих сучьев с сучками и корой
            for i, (ox, oy, ang) in enumerate([(-8, -4, 15), (0, 0, -10), (8, 4, 25)]):
                pygame.draw.line(surf, (140, 95, 55), (w // 2 + ox - 16, h // 2 + oy - 12),
                                 (w // 2 + ox + 16, h // 2 + oy + 12), 4)
                pygame.draw.line(surf, (95, 60, 30), (w // 2 + ox - 16, h // 2 + oy - 12),
                                 (w // 2 + ox + 16, h // 2 + oy + 12), 1)

        elif name == 'bark':
            # Изогнутый кусок сосновой коры с рельефными бороздками
            pygame.draw.rect(surf, (115, 75, 45), (6, 10, w - 12, h - 20), border_radius=5)
            pygame.draw.rect(surf, (75, 48, 28), (6, 10, w - 12, h - 20), width=2, border_radius=5)
            for y in range(16, h - 14, 5):
                pygame.draw.line(surf, (60, 38, 20), (10, y), (w - 12, y), 2)

        elif name == 'moss':
            # Бархатистая кочка лесного мха с бликами
            pygame.draw.circle(surf, (45, 85, 35), (w // 2, h // 2 + 2), 16)
            pygame.draw.circle(surf, (65, 120, 45), (w // 2 - 4, h // 2 - 2), 13)
            pygame.draw.circle(surf, (95, 155, 60), (w // 2 - 6, h // 2 - 5), 8)
            pygame.draw.circle(surf, (135, 195, 80), (w // 2 - 7, h // 2 - 7), 3)

        elif name == 'log':
            # Настоящее полено со спилом, годовыми кольцами и корой
            pygame.draw.rect(surf, (145, 110, 70), (4, 12, w - 20, h - 24), border_radius=4)
            pygame.draw.rect(surf, (90, 65, 40), (4, 12, w - 20, h - 24), width=2, border_radius=4)
            # Спил бревна
            pygame.draw.ellipse(surf, (200, 175, 130), (w - 22, 12, 18, h - 24))
            pygame.draw.ellipse(surf, (160, 130, 90), (w - 18, 16, 10, h - 32), 1)
            pygame.draw.circle(surf, (110, 80, 50), (w - 13, h // 2), 2)

        elif name == 'poker':
            # Кованая железная кочерга с загнутым наконечником и кольцом рукояти
            pygame.draw.line(surf, (140, 145, 155), (8, h - 8), (w - 12, 12), 4)
            pygame.draw.line(surf, (190, 195, 205), (8, h - 8), (w - 12, 12), 1)
            # Крюк
            pygame.draw.line(surf, (190, 195, 205), (w - 12, 12), (w - 6, 22), 4)
            # Рукоять
            pygame.draw.circle(surf, (100, 105, 115), (8, h - 8), 5, 2)

        elif name == 'marsh_bag':
            # Пакетик маршмеллоу со швом и белыми зефирками
            pygame.draw.rect(surf, (190, 65, 80), (6, 8, w - 12, h - 16), border_radius=6)
            pygame.draw.rect(surf, (240, 220, 225), (10, 12, w - 20, h - 24), border_radius=4)
            # Зефирки внутри
            pygame.draw.circle(surf, (255, 250, 245), (w // 2 - 8, h // 2), 7)
            pygame.draw.circle(surf, (255, 250, 245), (w // 2 + 8, h // 2), 7)
            pygame.draw.circle(surf, (255, 250, 245), (w // 2, h // 2 - 5), 6)

        return surf
