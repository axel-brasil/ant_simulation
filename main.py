#!/usr/bin/env python3
"""
Ant Colony Simulation with Pheromone Trails
=============================================
Features:
  - Pheromone-based pathfinding (food trail & home trail)
  - Food sources (click to place, or auto-generated)
  - Central nest with visual indicator
  - Colony statistics overlay
  - Pause/resume (Space), speed controls (+/-), clear food (C)
"""

import pygame
import pygame._freetype
from pygame._freetype import Font as _FTFont
import math
import random
import sys

# ── Configuration ──────────────────────────────────────────────────────────
WIDTH, HEIGHT = 900, 700
FPS = 60

NUM_ANTS = 500
ANT_SPEED = 1.8
ANT_SENSOR_RANGE = 40        # how far ant can "smell" pheromones
ANT_SENSOR_ANGLE = math.pi / 4  # half-angle of sensor arc
ANT_TURN_RATE = math.pi / 6    # max turn per frame
ANT_WANDER_STRENGTH = 0.4       # random jitter weight

NEST_RADIUS = 18
NEST_POS = (WIDTH // 2, HEIGHT // 2)

PHEROMONE_DECAY = 0.997        # per-frame multiplier
PHEROMONE_DEPOSIT = 3.0        # amount dropped each step
PHEROMONE_MAX = 255.0
PHEROMONE_GRID = 4             # pixel size of each pheromone cell

FOOD_RADIUS = 12
FOOD_AMOUNT = 80               # units per food source
FOOD_AUTO_COUNT = 5            # auto-generated food sources

BG_COLOR = (30, 30, 30)
NEST_COLOR = (180, 140, 60)
FOOD_COLOR = (40, 200, 80)
ANT_COLOR = (220, 220, 220)
ANT_CARRYING_COLOR = (255, 200, 50)

# Pheromone display colors (R, G, B)
FOOD_TRAIL_COLOR = (0, 180, 255)   # blue-ish — "food here!"
HOME_TRAIL_COLOR = (255, 100, 50)  # reddish — "home this way"


# ── Helper ─────────────────────────────────────────────────────────────────
def dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def angle_toward(x1, y1, x2, y2):
    """Angle from (x1,y1) to (x2,y2) in radians."""
    return math.atan2(y2 - y1, x2 - x1)


def wrap_angle(a):
    """Keep angle in [-pi, pi]."""
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


# ── Pheromone Grid ────────────────────────────────────────────────────────
class PheromoneGrid:
    """Two grids: one for 'food' pheromone (dropped by ants carrying food),
    one for 'home' pheromone (dropped by ants searching for food)."""

    def __init__(self, w, h, cell_size):
        self.cell_size = cell_size
        self.cols = w // cell_size
        self.rows = h // cell_size
        # Store as flat lists of floats for speed
        size = self.cols * self.rows
        self.food_pheromone = [0.0] * size
        self.home_pheromone = [0.0] * size

    def _index(self, x, y):
        col = int(x) // self.cell_size
        row = int(y) // self.cell_size
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return row * self.cols + col
        return -1

    def deposit(self, x, y, amount, kind):
        """kind: 'food' or 'home'"""
        grid = self.food_pheromone if kind == "food" else self.home_pheromone
        # Spread deposit to 3x3 area for smoother trails
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                idx = self._index(x + dx * self.cell_size, y + dy * self.cell_size)
                if idx >= 0:
                    grid[idx] = min(grid[idx] + amount * (0.5 if (dx or dy) else 1.0), PHEROMONE_MAX)

    def sample(self, x, y, kind):
        """Return pheromone intensity at position."""
        grid = self.food_pheromone if kind == "food" else self.home_pheromone
        idx = self._index(x, y)
        return grid[idx] if idx >= 0 else 0.0

    def decay(self):
        """Apply decay to both grids."""
        for i in range(len(self.food_pheromone)):
            self.food_pheromone[i] *= PHEROMONE_DECAY
            self.home_pheromone[i] *= PHEROMONE_DECAY
            if self.food_pheromone[i] < 0.5:
                self.food_pheromone[i] = 0.0
            if self.home_pheromone[i] < 0.5:
                self.home_pheromone[i] = 0.0

    def clear(self):
        size = self.cols * self.rows
        self.food_pheromone = [0.0] * size
        self.home_pheromone = [0.0] * size


# ── Food Source ────────────────────────────────────────────────────────────
class FoodSource:
    def __init__(self, x, y, amount=FOOD_AMOUNT):
        self.x = x
        self.y = y
        self.amount = amount
        self.max_amount = amount

    @property
    def depleted(self):
        return self.amount <= 0

    def take(self):
        if self.amount > 0:
            self.amount -= 1
            return True
        return False

    def draw(self, surface):
        # Shrink radius as food depletes
        r = max(4, int(FOOD_RADIUS * (self.amount / self.max_amount)))
        pygame.draw.circle(surface, FOOD_COLOR, (int(self.x), int(self.y)), r)
        # Inner highlight
        pygame.draw.circle(surface, (80, 240, 120), (int(self.x), int(self.y)), max(2, r - 4))


# ── Ant ────────────────────────────────────────────────────────────────────
class Ant:
    def __init__(self, nest_x, nest_y):
        self.x = float(nest_x)
        self.y = float(nest_y)
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = ANT_SPEED
        self.carrying_food = False
        self.target_food = None  # locked onto a specific food source

    def update(self, pheromones, foods, nest_x, nest_y):
        """Main per-frame behaviour."""
        if self.carrying_food:
            self._return_home(pheromones, nest_x, nest_y)
        else:
            self._search_food(pheromones, foods)

        # Move forward
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

        # Bounce off walls
        margin = 2
        if self.x < margin:
            self.x = margin
            self.angle = math.pi - self.angle
        elif self.x > WIDTH - margin:
            self.x = WIDTH - margin
            self.angle = math.pi - self.angle
        if self.y < margin:
            self.y = margin
            self.angle = -self.angle
        elif self.y > HEIGHT - margin:
            self.y = HEIGHT - margin
            self.angle = -self.angle

        # Deposit pheromone
        if self.carrying_food:
            pheromones.deposit(self.x, self.y, PHEROMONE_DEPOSIT, "food")
        else:
            pheromones.deposit(self.x, self.y, PHEROMONE_DEPOSIT * 0.3, "home")

        # Check if reached nest while carrying
        if self.carrying_food and dist(self.x, self.y, nest_x, nest_y) < NEST_RADIUS:
            self.carrying_food = False
            self.target_food = None
            # Turn around
            self.angle += math.pi + random.uniform(-0.5, 0.5)

    def _search_food(self, pheromones, foods):
        """Ant is looking for food — follow food pheromone, check for direct food."""
        # Direct food detection
        for food in foods:
            if food.depleted:
                continue
            d = dist(self.x, self.y, food.x, food.y)
            if d < FOOD_RADIUS + 5:
                if food.take():
                    self.carrying_food = True
                    self.angle = angle_toward(self.x, self.y, food.x, food.y)
                    return

        # Follow food pheromone trail
        self._follow_pheromone(pheromones, "food")

    def _return_home(self, pheromones, nest_x, nest_y):
        """Ant carries food — follow home pheromone + general direction to nest."""
        # Blend: follow home pheromone + direct pull toward nest
        nest_angle = angle_toward(self.x, self.y, nest_x, nest_y)
        nest_dist = dist(self.x, self.y, nest_x, nest_y)

        # Stronger direct pull when far, weaker when close
        direct_weight = min(0.7, 30.0 / max(nest_dist, 30))

        pheromone_angle = self._sense_pheromone(pheromones, "home")
        if pheromone_angle is not None:
            target = pheromone_angle * (1 - direct_weight) + nest_angle * direct_weight
        else:
            target = nest_angle

        self._turn_toward(target, ANT_TURN_RATE * 1.5)

    def _follow_pheromone(self, pheromones, kind):
        """Sense pheromone ahead and turn toward strongest signal."""
        best_angle = self._sense_pheromone(pheromones, kind)
        if best_angle is not None:
            # Blend pheromone following with random wander
            target = best_angle
            self._turn_toward(target, ANT_TURN_RATE)
        else:
            # Random wander
            self.angle += random.uniform(-ANT_WANDER_STRENGTH, ANT_WANDER_STRENGTH)

        # Always add a small random jitter so paths aren't perfectly straight
        self.angle += random.uniform(-ANT_WANDER_STRENGTH * 0.3, ANT_WANDER_STRENGTH * 0.3)

    def _sense_pheromone(self, pheromones, kind):
        """Sample pheromone in a fan ahead. Returns best angle or None."""
        best_val = 0.0
        best_angle = None
        samples = 7
        for i in range(samples):
            a = self.angle + (i - samples // 2) * (ANT_SENSOR_ANGLE / (samples // 2))
            sx = self.x + math.cos(a) * ANT_SENSOR_RANGE
            sy = self.y + math.sin(a) * ANT_SENSOR_RANGE
            val = pheromones.sample(sx, sy, kind)
            if val > best_val:
                best_val = val
                best_angle = a
        return best_angle

    def _turn_toward(self, target_angle, max_turn):
        """Smoothly rotate toward target_angle."""
        diff = wrap_angle(target_angle - self.angle)
        if abs(diff) < max_turn:
            self.angle = target_angle
        else:
            self.angle += max_turn if diff > 0 else -max_turn

    def draw(self, surface):
        color = ANT_CARRYING_COLOR if self.carrying_food else ANT_COLOR
        # Body
        bx = int(self.x)
        by = int(self.y)
        pygame.draw.circle(surface, color, (bx, by), 2)
        # Direction indicator (small line ahead)
        ex = int(self.x + math.cos(self.angle) * 5)
        ey = int(self.y + math.sin(self.angle) * 5)
        pygame.draw.line(surface, color, (bx, by), (ex, ey), 1)


# ── Colony / Simulation ───────────────────────────────────────────────────
class Colony:
    def __init__(self):
        self.nest_x, self.nest_y = NEST_POS
        self.pheromones = PheromoneGrid(WIDTH, HEIGHT, PHEROMONE_GRID)
        self.ants = [Ant(self.nest_x, self.nest_y) for _ in range(NUM_ANTS)]
        self.food_sources: list[FoodSource] = []
        self.food_collected = 0
        self.total_food_in_world = 0

        # Auto-generate some food sources
        for _ in range(FOOD_AUTO_COUNT):
            self._spawn_random_food()

    def _spawn_random_food(self):
        margin = 80
        x = random.randint(margin, WIDTH - margin)
        y = random.randint(margin, HEIGHT - margin)
        # Make sure it's not too close to the nest
        while dist(x, y, self.nest_x, self.nest_y) < 120:
            x = random.randint(margin, WIDTH - margin)
            y = random.randint(margin, HEIGHT - margin)
        amount = random.randint(50, 150)
        self.food_sources.append(FoodSource(x, y, amount))
        self.total_food_in_world += amount

    def add_food(self, x, y, amount=FOOD_AMOUNT):
        self.food_sources.append(FoodSource(x, y, amount))
        self.total_food_in_world += amount

    def update(self):
        # Update ants
        for ant in self.ants:
            was_carrying = ant.carrying_food
            ant.update(self.pheromones, self.food_sources, self.nest_x, self.nest_y)
            if was_carrying and not ant.carrying_food:
                self.food_collected += 1

        # Remove depleted food
        self.food_sources = [f for f in self.food_sources if not f.depleted]

        # Decay pheromones
        self.pheromones.decay()

    def draw(self, surface):
        # Draw pheromone layer
        self._draw_pheromones(surface)

        # Draw nest
        pygame.draw.circle(surface, NEST_COLOR, (self.nest_x, self.nest_y), NEST_RADIUS)
        pygame.draw.circle(surface, (220, 180, 90), (self.nest_x, self.nest_y), NEST_RADIUS - 4)
        pygame.draw.circle(surface, (100, 70, 20), (self.nest_x, self.nest_y), 6)

        # Draw food sources
        for food in self.food_sources:
            food.draw(surface)

        # Draw ants
        for ant in self.ants:
            ant.draw(surface)

    def _draw_pheromones(self, surface):
        """Render pheromone grids onto surface with colored blending."""
        cs = self.pheromones.cell_size
        for row in range(self.pheromones.rows):
            for col in range(self.pheromones.cols):
                idx = row * self.pheromones.cols + col
                fv = self.pheromones.food_pheromone[idx]
                hv = self.pheromones.home_pheromone[idx]

                if fv < 1 and hv < 1:
                    continue

                r, g, b = 0, 0, 0
                if fv > 0:
                    intensity = min(fv / 80.0, 1.0)
                    r += int(FOOD_TRAIL_COLOR[0] * intensity)
                    g += int(FOOD_TRAIL_COLOR[1] * intensity)
                    b += int(FOOD_TRAIL_COLOR[2] * intensity)
                if hv > 0:
                    intensity = min(hv / 80.0, 1.0)
                    r += int(HOME_TRAIL_COLOR[0] * intensity)
                    g += int(HOME_TRAIL_COLOR[1] * intensity)
                    b += int(HOME_TRAIL_COLOR[2] * intensity)

                r = min(r, 255)
                g = min(g, 255)
                b = min(b, 255)

                if r or g or b:
                    rect = pygame.Rect(col * cs, row * cs, cs, cs)
                    pygame.draw.rect(surface, (r, g, b), rect)


# ── HUD / Stats ───────────────────────────────────────────────────────────
class HUD:
    def __init__(self):
        pygame._freetype.init()
        self.font = _FTFont(None, 14)

    def draw(self, surface, colony, paused, speed_mult):
        lines = [
            f"Ants:      {len(colony.ants)}",
            f"Food left: {sum(f.amount for f in colony.food_sources)}",
            f"Collected: {colony.food_collected}",
            f"Sources:   {len(colony.food_sources)}",
            f"Speed:     {speed_mult:.1f}x",
            f"{'PAUSED' if paused else 'Running'}",
        ]
        y = 8
        for line in lines:
            surf, _ = self.font.render(line, (220, 220, 220), (0, 0, 0))
            surface.blit(surf, (8, y))
            y += 18

        # Controls help (bottom)
        help_text = "[Space] Pause  [Click] Place food  [+/-] Speed  [C] Clear pheromones  [R] Reset"
        hs, _ = self.font.render(help_text, (150, 150, 150), (0, 0, 0))
        surface.blit(hs, (8, HEIGHT - 22))


# ── Main Loop ─────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ant Colony Simulation")
    clock = pygame.time.Clock()

    colony = Colony()
    hud = HUD()
    paused = False
    speed_mult = 1.0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    speed_mult = min(speed_mult + 0.5, 5.0)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed_mult = max(speed_mult - 0.5, 0.5)
                elif event.key == pygame.K_c:
                    colony.pheromones.clear()
                elif event.key == pygame.K_r:
                    colony = Colony()
                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click — place food
                    mx, my = event.pos
                    colony.add_food(mx, my)

        # Simulation step (may run multiple times for speed > 1)
        if not paused:
            steps = int(speed_mult)
            if random.random() < (speed_mult - steps):
                steps += 1
            for _ in range(steps):
                colony.update()

        # Draw
        screen.fill(BG_COLOR)
        colony.draw(screen)
        hud.draw(screen, colony, paused, speed_mult)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
