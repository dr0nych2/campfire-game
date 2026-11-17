"""
fire.py — 2.5D Diorama Fire Simulation in PS1 / Billboarding Aesthetic:
- Perspective 3D ground plane with natural distance light falloff (NO ugly yellow circle!)
- Real depth-sorted campfire: back stones -> bed of coals -> flames -> leaning logs -> front stones
- Rain interaction: steam puffs (white steam rising) + sizzle reaction
- Wind interaction: flames and embers tilt and drift in 3D perspective
"""
import pygame
import random
import math

from diorama import (
    Camera3D, DioramaGround, FireStone, DioramaLog,
    FlameBillboard, Ember3D, SteamPuff3D
)
from sound_synth import sounds


class FireSystem:
    def __init__(self, cx=400, cy=400):
        self.camera = Camera3D()
        self.ground = DioramaGround(self.camera)

        # Камни кострища в 3D эллипсе вокруг огня (от 0 до 360 градусов)
        self.stones = [FireStone(deg, rx=72, rz=46) for deg in range(0, 360, 25)]

        self.temperature = 0.0
        self.wind_x = 0.0
        self.is_raining = False

        self.logs_3d = []
        self.flames = []
        self.embers = []
        self.steam_puffs = []

        self._glow_phase = 0.0
        self._spawn_acc = 0.0
        self._steam_sizzle_cooldown = 0.0

        # Базовые стартовые бревна (образующие колодец/шалаш)
        self._init_base_logs()

    def _init_base_logs(self):
        self.logs_3d.clear()
        # Два перекрестных бревна на земле
        self.logs_3d.append(DioramaLog('log', -45, 0, 125, 45, 0, 155))
        self.logs_3d.append(DioramaLog('log', -40, 0, 155, 40, 0, 125))

    def clear_fuel(self):
        self.logs_3d.clear()
        self._init_base_logs()

    def add_fuel_visual(self, kind):
        """Добавляет полено, ветку или кору в 3D костер под естественным углом."""
        if len(self.logs_3d) >= 16:
            # Убираем старое самое сгоревшее полено
            self.logs_3d.sort(key=lambda l: l.life)
            self.logs_3d.pop(0)

        # Случайное позиционирование в 3D костре: поленья ложатся шалашом к центру
        side = random.choice([-1, 1])
        angle_deg = random.uniform(0, 360)
        rad = math.radians(angle_deg)
        dist = random.uniform(25, 52)

        x1 = dist * math.cos(rad)
        z1 = 140.0 + dist * math.sin(rad) * 0.65
        y1 = 0.0  # на земле

        # Верхний конец опирается на центр костра или на другие бревна
        x2 = random.uniform(-12, 12)
        z2 = 140.0 + random.uniform(-8, 8)
        y2 = random.uniform(-18, -32)  # приподнято вверх в шалаш

        self.logs_3d.append(DioramaLog(kind, x1, y1, z1, x2, y2, z2))

    def set_temperature(self, temp):
        self.temperature = max(0.0, min(100.0, temp))

    def set_wind(self, wind_x):
        self.wind_x = wind_x

    def burst_embers(self, count=15):
        for _ in range(count):
            if len(self.embers) < 85:
                e = Ember3D(
                    random.uniform(-18, 18),
                    random.uniform(-4, 2),
                    140.0 + random.uniform(-14, 14),
                    random.uniform(-1.2, 1.2),
                    random.uniform(-3.5, -1.5),
                    random.uniform(-0.8, 0.8),
                    random.uniform(0.6, 1.4),
                    size=random.randint(2, 4)
                )
                self.embers.append(e)

    def trigger_rain_hit(self):
        """Вызывается когда капли дождя попадают в горячий костёр."""
        if self.temperature > 12.0 and len(self.steam_puffs) < 30:
            sp = SteamPuff3D(
                random.uniform(-25, 25),
                random.uniform(-5, 0),
                140.0 + random.uniform(-18, 18)
            )
            self.steam_puffs.append(sp)

            # Звук шипения пара
            if self._steam_sizzle_cooldown <= 0:
                self._steam_sizzle_cooldown = random.uniform(0.35, 0.75)
                sounds.play('steam_hiss')

    def update(self, dt=1/60.0):
        self._glow_phase += 0.09
        temp_ratio = self.temperature / 100.0

        if self._steam_sizzle_cooldown > 0:
            self._steam_sizzle_cooldown -= dt

        # Обновление 3D брёвен
        for log in self.logs_3d:
            log.update(dt, temp_ratio, self.is_raining)
        self.logs_3d = [l for l in self.logs_3d if l.life > 0]

        # Спавн языков пламени в 3D пространстве костра
        if temp_ratio > 0.03:
            spawn_rate = (15.0 + 35.0 * temp_ratio) * dt
            self._spawn_acc += spawn_rate
            to_spawn = int(self._spawn_acc)
            self._spawn_acc -= to_spawn

            spread_r = 10.0 + 26.0 * temp_ratio
            for _ in range(min(to_spawn, 8)):
                ang = random.uniform(0, math.pi * 2)
                d = random.uniform(0, spread_r)
                fx = d * math.cos(ang)
                fz = 140.0 + d * math.sin(ang) * 0.65
                fy = random.uniform(-2, 2)
                sz = random.uniform(14, 28) * (0.6 + 0.8 * temp_ratio)
                lt = random.uniform(0.25, 0.55) * (0.6 + 0.8 * temp_ratio)
                self.flames.append(FlameBillboard(fx, fy, fz, sz, lt))

        # Обновление и очистка пламени
        for f in self.flames:
            f.update(dt, self.wind_x)
        self.flames = [f for f in self.flames if f.alive]

        # Обновление искр
        for e in self.embers:
            e.update(dt, self.wind_x)
        self.embers = [e for e in self.embers if e.alive]

        # Фоновые искры от сильного огня
        if temp_ratio > 0.35 and random.random() < 0.18 and len(self.embers) < 65:
            self.burst_embers(1)

        # Обновление пара
        for sp in self.steam_puffs:
            sp.update(dt, self.wind_x)
        self.steam_puffs = [sp for sp in self.steam_puffs if sp.alive]

    def draw_ground(self, surface):
        """Рисует перспективную 2.5D землю с честным световым затуханием."""
        self.ground.draw(surface, self.temperature, self._glow_phase)

    def draw(self, surface):
        """
        Рисует все объекты костра в едином цикле сортировки по глубине Z
        (Back-to-front Painter's Algorithm в стиле диорамы Paper Mario / Don't Starve).
        """
        # Слой раскалённой подушки углей в центре кострища
        temp_ratio = self.temperature / 100.0
        if temp_ratio > 0.02:
            bed_proj = self.camera.project(0, 0, 140)
            if bed_proj:
                bx, by, bscale, _ = bed_proj
                flick = 0.85 + 0.15 * math.sin(self._glow_phase * 2.5)
                bw = int(75 * bscale * (0.6 + 0.4 * temp_ratio))
                bh = int(38 * bscale * (0.6 + 0.4 * temp_ratio))
                ember_col = (
                    min(255, int(180 + 75 * temp_ratio)),
                    max(15, int(45 + 110 * temp_ratio * flick)),
                    10
                )
                # Подушка углей на земле
                pygame.draw.ellipse(surface, (20, 12, 10), (bx - bw // 2 - 4, by - bh // 2 - 2, bw + 8, bh + 4))
                pygame.draw.ellipse(surface, ember_col, (bx - bw // 2, by - bh // 2, bw, bh))

        # Собираем все 3D объекты для единой сортировки по Z
        render_queue = []

        # 1. Камни
        for st in self.stones:
            render_queue.append((st.z, 'stone', st))

        # 2. Дрова
        for log in self.logs_3d:
            render_queue.append((log.center_z, 'log', log))

        # 3. Пламя
        for fl in self.flames:
            render_queue.append((fl.z, 'flame', fl))

        # Сортируем: от самых дальних (большой Z) к ближним (малый Z)
        render_queue.sort(key=lambda item: item[0], reverse=True)

        # Отрисовка упорядоченных слоёв
        for z, kind, obj in render_queue:
            if kind == 'stone':
                obj.draw(surface, self.camera, self.temperature, self._glow_phase)
            elif kind == 'log':
                obj.draw(surface, self.camera, self.temperature, self._glow_phase)
            elif kind == 'flame':
                obj.draw(surface, self.camera)

        # 4. Искры и дым поверх костра
        for e in self.embers:
            e.draw(surface, self.camera)

        # 5. Столбики пара от дождя
        for sp in self.steam_puffs:
            sp.draw(surface, self.camera)

    def draw_ambient_light(self, surface):
        """
        Заменяет старый уродливый жёлтый круг!
        Теперь свет костра уже честно лежит НА ЗЕМЛЕ (в draw_ground),
        а здесь мы лишь мягко подсвечиваем нижний горизонт стволов сосен тёплым отблеском.
        """
        temp_ratio = self.temperature / 100.0
        if temp_ratio <= 0.05:
            return

        # Лёгкий теплый отблеск на дальних силуэтах деревьев
        flicker = 1.0 + 0.06 * math.sin(self._glow_phase * 2.2)
        alpha = int(22 * temp_ratio * flicker)
        if alpha > 1:
            w, h = surface.get_size()
            horizon_surf = pygame.Surface((w, 55), pygame.SRCALPHA)
            horizon_surf.fill((210, 85, 15, alpha))
            surface.blit(horizon_surf, (0, 310))
