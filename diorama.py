"""
diorama.py — 2.5D Diorama / Billboarding System with PS1 Aesthetic.
Renders a 3D perspective scene with paper-theater billboarded sprites,
depth-sorted logs, stones in perspective, ground illumination (NO ugly yellow circle),
and true 3D particle projection for flames, smoke, steam, and embers.
"""
import pygame
import math
import random

SCREEN_W = 800
SCREEN_H = 600

class Camera3D:
    def __init__(self):
        # Позиция камеры: чуть приподнята и смотрит на кострище вперед и вниз
        self.x = 0.0
        self.y = -85.0   # высота над землей (Y направлен вниз)
        self.z = -130.0  # расстояние до центра костра
        self.fov = 360.0 # фокусное расстояние перспективы

    def project(self, x, y, z):
        """Проецирует 3D точку (X, Y, Z) на 2D экран с честной перспективой."""
        rel_x = x - self.x
        rel_y = y - self.y
        rel_z = z - self.z
        if rel_z <= 2.0:
            return None
        scale = self.fov / rel_z
        sx = int(SCREEN_W / 2 + rel_x * scale)
        sy = int(SCREEN_H / 2 + rel_y * scale - 25)  # костёр центрируется на Y=388, выше слотов инвентаря
        return (sx, sy, scale, rel_z)


class DioramaGround:
    """Пикселизированная перспективная земля (поляна в лесу с честным затуханием света костра)."""
    def __init__(self, camera: Camera3D):
        self.camera = camera
        # Сетка тайлов земли в мировых координатах (X, Z)
        self.grid = []
        step_x = 35
        step_z = 32
        for z in range(20, 480, step_z):
            row = []
            for x in range(-360, 361, step_x):
                # Вариация типа грунта: земля, хвоя, тёмный мох
                noise = (math.sin(x * 0.05) + math.cos(z * 0.04)) * 0.5
                row.append((x, z, noise))
            self.grid.append(row)

    def draw(self, surface, fire_temp, glow_phase):
        cam = self.camera
        temp_ratio = fire_temp / 100.0
        flicker = 1.0 + 0.06 * math.sin(glow_phase * 2.8) + 0.04 * math.sin(glow_phase * 5.1)
        fire_r = (65 + 180 * temp_ratio) * flicker

        # Рисуем полигоны земли сеткой от дальних к ближним
        for r_idx in range(len(self.grid) - 1, 0, -1):
            row_back = self.grid[r_idx]
            row_front = self.grid[r_idx - 1]

            for c_idx in range(len(row_back) - 1):
                p0 = row_front[c_idx]
                p1 = row_front[c_idx + 1]
                p2 = row_back[c_idx + 1]
                p3 = row_back[c_idx]

                # Проекция 4 вершин тайла
                proj0 = cam.project(p0[0], 0, p0[1])
                proj1 = cam.project(p1[0], 0, p1[1])
                proj2 = cam.project(p2[0], 0, p2[1])
                proj3 = cam.project(p3[0], 0, p3[1])

                if not (proj0 and proj1 and proj2 and proj3):
                    continue

                # Расчёт освещения костром в центре тайла (костёр в X=0, Z=140)
                cx = (p0[0] + p1[0] + p2[0] + p3[0]) * 0.25
                cz = (p0[1] + p1[1] + p2[1] + p3[1]) * 0.25
                dist = math.hypot(cx - 0, cz - 140)

                # Затухание света: в центре тёплый рыжеватый свет, далее — глубокая темнота
                light_factor = 0.0
                if dist < fire_r and fire_temp > 2:
                    light_factor = (1.0 - (dist / fire_r)) ** 1.6

                noise = (p0[2] + p2[2]) * 0.5

                # Базовый ночной цвет земли
                base_r = int(12 + 6 * noise)
                base_g = int(9 + 5 * noise)
                base_b = int(7 + 4 * noise)

                # Добавляем тёплое пламя (без всяких мутных жёлтых кругов!)
                lit_r = min(255, int(base_r + (165 + 40 * noise) * light_factor * temp_ratio))
                lit_g = min(255, int(base_g + (85 + 25 * noise) * light_factor * temp_ratio))
                lit_b = min(255, int(base_b + (25 + 10 * noise) * light_factor * temp_ratio))

                col = (lit_r, lit_g, lit_b)
                pts = [(proj0[0], proj0[1]), (proj1[0], proj1[1]),
                       (proj2[0], proj2[1]), (proj3[0], proj3[1])]
                pygame.draw.polygon(surface, col, pts)


class FireStone:
    """Камень очага в 3D пространстве с освещённой внутренней гранью."""
    def __init__(self, angle_deg, rx=72, rz=46):
        rad = math.radians(angle_deg)
        self.x = rx * math.cos(rad) + random.uniform(-4, 4)
        self.z = 140.0 + rz * math.sin(rad) + random.uniform(-3, 3)
        self.y = 0.0
        self.w = random.randint(18, 26)
        self.h = random.randint(12, 18)
        self.angle_deg = angle_deg

    def draw(self, surface, camera: Camera3D, fire_temp, glow_phase):
        proj = camera.project(self.x, self.y, self.z)
        if not proj:
            return
        sx, sy, scale, z = proj
        bw = max(6, int(self.w * scale))
        bh = max(4, int(self.h * scale))

        temp_ratio = fire_temp / 100.0
        # Внутренняя сторона камня (обращенная к костру) освещена пламенем
        # Камни впереди (Z < 140) смотрят задней темной стороной на камеру, а передние (Z > 140) — освещенной
        is_back = (self.z > 140.0)

        flicker = 1.0 + 0.08 * math.sin(glow_phase * 3.1 + self.angle_deg)
        light_boost = temp_ratio * flicker

        if is_back:
            # Освещённая внутренняя грань задних камней
            top_col = (
                min(255, int(75 + 110 * light_boost)),
                min(255, int(55 + 60 * light_boost)),
                min(255, int(45 + 15 * light_boost))
            )
            side_col = (
                min(255, int(50 + 80 * light_boost)),
                min(255, int(35 + 40 * light_boost)),
                min(255, int(30 + 10 * light_boost))
            )
        else:
            # Теневая внешняя грань передних камней (силуэт на фоне костра)
            top_col = (
                min(255, int(45 + 25 * light_boost)),
                min(255, int(35 + 18 * light_boost)),
                min(255, int(30 + 10 * light_boost))
            )
            side_col = (25, 20, 18)

        # Тень от камня на земле
        pygame.draw.ellipse(surface, (10, 8, 7), (sx - bw // 2 - 2, sy - bh // 4 + 2, bw + 4, bh // 2 + 3))
        # Тело камня (пиксельный полигон)
        pts = [
            (sx - bw // 2, sy),
            (sx - bw // 3, sy - bh),
            (sx + bw // 3, sy - bh),
            (sx + bw // 2, sy),
            (sx + bw // 3, sy + bh // 3),
            (sx - bw // 3, sy + bh // 3)
        ]
        pygame.draw.polygon(surface, side_col, pts)
        pygame.draw.polygon(surface, top_col, [(sx - bw // 3, sy - bh), (sx + bw // 3, sy - bh),
                                              (sx + bw // 4, sy - bh // 2), (sx - bw // 4, sy - bh // 2)])
        pygame.draw.polygon(surface, (15, 12, 10), pts, 1)


class DioramaLog:
    """3D Полено в костре, уложенное в объёме под углом."""
    def __init__(self, kind, x1, y1, z1, x2, y2, z2):
        self.kind = kind
        self.p1 = [x1, y1, z1]
        self.p2 = [x2, y2, z2]
        self.char = 0.0
        self.life = 1.0
        self.wetness = 0.0  # 0.0 = сухое, 1.0 = намокшее от дождя

        if kind == 'tinder':
            self.thick = 6
            self.base_col = (215, 195, 160)
            self.burn_speed = 0.045
        elif kind == 'kindling':
            self.thick = 7
            self.base_col = (135, 95, 55)
            self.burn_speed = 0.022
        elif kind == 'bark':
            self.thick = 9
            self.base_col = (115, 75, 45)
            self.burn_speed = 0.028
        elif kind == 'moss':
            self.thick = 12
            self.base_col = (65, 110, 50)
            self.burn_speed = 0.015
        else: # log
            self.thick = 18
            self.base_col = (145, 115, 75)
            self.burn_speed = 0.008

    @property
    def center_z(self):
        return (self.p1[2] + self.p2[2]) * 0.5

    def update(self, dt, temp_ratio, is_raining):
        if is_raining:
            self.wetness = min(1.0, self.wetness + dt * 0.08)
        else:
            self.wetness = max(0.0, self.wetness - dt * 0.15)

        # Мокрое дерево сначала должно высохнуть от жара углей
        eff_burn = self.burn_speed * (0.3 + 1.2 * temp_ratio) * (1.0 - self.wetness * 0.7)
        self.char = min(1.0, self.char + eff_burn * dt * 1.8)
        self.life -= eff_burn * dt * 0.75

    def draw(self, surface, camera: Camera3D, fire_temp, glow_phase):
        proj1 = camera.project(*self.p1)
        proj2 = camera.project(*self.p2)
        if not (proj1 and proj2):
            return

        sx1, sy1, sc1, _ = proj1
        sx2, sy2, sc2, _ = proj2
        avg_scale = (sc1 + sc2) * 0.5
        th = max(2, int(self.thick * avg_scale * (0.6 + 0.4 * self.life)))

        # Плавный переход в обугленный уголь
        c = self.char
        r = int(self.base_col[0] * (1 - c) + 26 * c)
        g = int(self.base_col[1] * (1 - c) + 20 * c)
        b = int(self.base_col[2] * (1 - c) + 18 * c)

        # Если мокрое — темнеет от влаги
        if self.wetness > 0.1:
            w_factor = 1.0 - self.wetness * 0.45
            r = int(r * w_factor)
            g = int(g * w_factor)
            b = int(b * w_factor)

        pygame.draw.line(surface, (r, g, b), (sx1, sy1), (sx2, sy2), th)
        # Текстурные грани и кора
        pygame.draw.line(surface, (max(0, r - 20), max(0, g - 15), max(0, b - 15)),
                         (sx1, sy1 + 2), (sx2, sy2 + 2), max(1, th // 3))

        # Тлеющие светящиеся трещины углей на обгоревшей древесине
        if c > 0.30 and fire_temp > 5:
            temp_ratio = fire_temp / 100.0
            glow = int(min(255, 210 * c * temp_ratio * (0.8 + 0.2 * math.sin(glow_phase * 2.5 + self.p1[0]))))
            if glow > 30:
                glow_col = (255, int(glow * 0.55), 15)
                pygame.draw.line(surface, glow_col, (sx1, sy1), (sx2, sy2), max(1, th // 3))


class FlameBillboard:
    """Язык пламени как 2.5D плоский спрайт в 3D мире с наклоном от ветра."""
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "life", "max_life", "size", "tilt")

    def __init__(self, x, y, z, size, life):
        self.x = x
        self.y = y
        self.z = z
        self.vx = random.uniform(-0.25, 0.25)
        self.vy = random.uniform(-1.8, -0.9)  # подъем вверх
        self.vz = random.uniform(-0.2, 0.2)
        self.life = life
        self.max_life = life
        self.size = size
        self.tilt = 0.0

    def update(self, dt, wind_strength):
        self.tilt = wind_strength * 0.4
        self.x += (self.vx + wind_strength * 0.02)
        self.y += self.vy
        self.z += self.vz
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surface, camera: Camera3D):
        proj = camera.project(self.x, self.y, self.z)
        if not proj:
            return
        sx, sy, scale, _ = proj
        ratio = max(0.0, self.life / self.max_life)
        sz = max(2, int(self.size * scale * (0.4 + 0.6 * ratio)))

        # PS1 ретро-пламя: ядро жёлтое, края огненно-оранжевые, кончик красный
        if ratio > 0.6:
            col = (255, 240, 90)
        elif ratio > 0.3:
            col = (255, 145, 25)
        else:
            col = (210, 45, 10)

        # Смещённый наклон языка пламени от ветра
        tilt_px = int(self.tilt * scale * (1.0 - ratio) * 12)
        pts = [
            (sx - sz // 2, sy + sz // 2),
            (sx + sz // 2, sy + sz // 2),
            (sx + tilt_px, sy - sz)
        ]
        pygame.draw.polygon(surface, col, pts)


class Ember3D:
    """Искры и угольки, летящие в 3D пространстве."""
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "life", "max_life", "size")

    def __init__(self, x, y, z, vx, vy, vz, life, size=3):
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.life = life
        self.max_life = life
        self.size = size

    def update(self, dt, wind_strength):
        self.x += (self.vx + wind_strength * 0.05)
        self.y += self.vy
        self.z += self.vz
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surface, camera: Camera3D):
        proj = camera.project(self.x, self.y, self.z)
        if not proj:
            return
        sx, sy, scale, _ = proj
        ratio = max(0.0, self.life / self.max_life)
        col = (255, int(180 * ratio + 60), 20)
        pygame.draw.circle(surface, col, (sx, sy), max(1, int(self.size * scale)))


class SteamPuff3D:
    """Белый пар при попадании капель дождя на раскалённый костёр."""
    __slots__ = ("x", "y", "z", "vx", "vy", "life", "max_life", "size")

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-1.2, -0.6)
        self.life = random.uniform(0.5, 0.9)
        self.max_life = self.life
        self.size = random.randint(8, 16)

    def update(self, dt, wind_strength):
        self.x += (self.vx + wind_strength * 0.03)
        self.y += self.vy
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surface, camera: Camera3D):
        proj = camera.project(self.x, self.y, self.z)
        if not proj:
            return
        sx, sy, scale, _ = proj
        ratio = max(0.0, self.life / self.max_life)
        sz = int(self.size * scale * (1.5 - 0.5 * ratio))
        alpha = int(140 * ratio)
        s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (210, 215, 225, alpha), (sz, sz), sz)
        surface.blit(s, (sx - sz, sy - sz))
