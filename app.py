import pygame
import sys
import random
import time

# --- Constants ---
WIDTH, HEIGHT = 1024, 576
SKY_BLUE = (135, 206, 235)
GREEN = (34, 139, 34)
BROWN = (139, 69, 19)
BRICK_LINE = (101, 67, 33)
BLUE = (0, 100, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

GRAVITY = 0.8
PLAYER_MAX_SPEED = 7.0
JUMP_STRENGTH = -15
GROUND_Y = HEIGHT - 80

# --- Game Classes ---

class Player:
    def __init__(self, game):
        self.game = game
        self.w = 32
        self.h = 48
        self.world_x = 200.0
        self.world_y = GROUND_Y - self.h
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = True
        self.invincible = False
        self.invincible_end_time = 0.0
        self.rect = pygame.Rect(0, 0, self.w, self.h)

    def move_x(self, dx):
        self.rect.x += dx
        for solid in self.game.platforms:
            if self.rect.colliderect(solid):
                if dx > 0: self.rect.right = solid.left
                elif dx < 0: self.rect.left = solid.right
                self.vel_x = 0.0
        self.world_x = self.rect.x

    def move_y(self, dy):
        self.rect.y += dy
        self.on_ground = False
        for solid in self.game.platforms:
            if self.rect.colliderect(solid):
                if dy > 0:
                    self.rect.bottom = solid.top
                    self.vel_y = 0.0
                    self.on_ground = True
                elif dy < 0:
                    self.rect.top = solid.bottom
                    self.vel_y = 0.0
        self.world_y = self.rect.y

    def update(self, dt):
        keys = pygame.key.get_pressed()
        accel = 40.0 * dt

        # --- Movement ---
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.vel_x += accel
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.vel_x -= accel
        self.vel_x += 15.0 * dt  # Auto-run
        self.vel_x = max(-PLAYER_MAX_SPEED * 0.4, min(self.vel_x, PLAYER_MAX_SPEED))
        self.vel_x *= 0.92

        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            self.on_ground = False

        self.vel_y += GRAVITY * dt * 60

        # --- Position & Collision Update ---
        self.rect.topleft = (self.world_x, self.world_y)
        self.move_x(self.vel_x * dt * 60)
        self.move_y(self.vel_y * dt * 60)

        if self.world_y > GROUND_Y - self.h:
            self.world_y = GROUND_Y - self.h
            self.rect.y = self.world_y
            self.vel_y = 0.0
            self.on_ground = True

        # --- Collisions with items/enemies ---
        self.check_collisions()

        # --- Power-up Timer ---
        if self.invincible and time.time() > self.invincible_end_time:
            self.invincible = False

    def check_collisions(self):
        # Enemies
        for enemy in self.game.enemies[:]:
            if self.rect.colliderect(enemy.rect):
                if self.invincible:
                    self.game.enemies.remove(enemy)
                    self.game.score += 100
                    continue
                # Stomp
                if self.vel_y > 1 and self.rect.bottom < enemy.rect.centery + 10:
                    self.game.enemies.remove(enemy)
                    self.game.score += 50
                    self.vel_y = JUMP_STRENGTH * 0.6
                else: # Caught
                    self.game.state = 'game_over'

        # Coins
        for coin in self.game.coins[:]:
            if self.rect.colliderect(coin):
                self.game.coins.remove(coin)
                self.game.score += 10

        # Power-ups
        for pu in self.game.power_ups[:]:
            if self.rect.colliderect(pu):
                self.game.power_ups.remove(pu)
                self.invincible = True
                self.invincible_end_time = time.time() + 5.0

    def get_screen_pos(self, camera_x):
        return int(self.world_x - camera_x), int(self.world_y)

class Enemy:
    def __init__(self, game, world_x):
        self.game = game
        self.w = 28
        self.h = 40
        self.world_x = world_x
        self.world_y = GROUND_Y - self.h
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = True
        self.rect = pygame.Rect(0, 0, self.w, self.h)

    def move_x(self, dx):
        self.rect.x += dx
        for solid in self.game.platforms:
            if self.rect.colliderect(solid):
                if dx > 0: self.rect.right = solid.left
                elif dx < 0: self.rect.left = solid.right
                self.vel_x = 0.0
        self.world_x = self.rect.x

    def move_y(self, dy):
        self.rect.y += dy
        self.on_ground = False
        for solid in self.game.platforms:
            if self.rect.colliderect(solid):
                if dy > 0:
                    self.rect.bottom = solid.top
                    self.vel_y = 0.0
                    self.on_ground = True
                elif dy < 0:
                    self.rect.top = solid.bottom
                    self.vel_y = 0.0
        self.world_y = self.rect.y

    def update(self, dt):
        target_vel = PLAYER_MAX_SPEED + 1.5 + (self.game.level * 0.4)
        if self.game.player.world_x > self.world_x:
            self.vel_x += 25.0 * dt
            self.vel_x = min(self.vel_x, target_vel)
        else:
            self.vel_x -= 15.0 * dt
        self.vel_x *= 0.95

        self.vel_y += GRAVITY * dt * 60

        self.rect.topleft = (self.world_x, self.world_y)
        self.move_x(self.vel_x * dt * 60)
        self.move_y(self.vel_y * dt * 60)

        if self.world_y > GROUND_Y - self.h:
            self.world_y = GROUND_Y - self.h
            self.rect.y = self.world_y
            self.vel_y = 0.0
            self.on_ground = True

    def get_screen_pos(self, camera_x):
        return int(self.world_x - camera_x), int(self.world_y)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chor Police Mario Adventure")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.large_font = pygame.font.SysFont(None, 72)
        self.running = True
        self.state = 'start_screen'
        self.high_score = 0

    def reset(self):
        self.player = Player(self)
        self.platforms = []
        self.enemies = [Enemy(self, 50), Enemy(self, -100)]
        self.coins = []
        self.power_ups = []
        self.score = 0
        self.level = 1
        self.spawn_timer = 0.0
        self.camera_x = 0
        self.state = 'playing'

    def run(self):
        while self.running:
            self.dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update()
            self.draw()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if self.state == 'start_screen':
                    self.reset()
                elif self.state == 'game_over' and event.key == pygame.K_r:
                    self.reset()

    def update(self):
        if self.state != 'playing':
            return

        # Updates
        self.player.update(self.dt)
        for enemy in self.enemies[:]:
            enemy.update(self.dt)
            if enemy.world_x < self.player.world_x - 1000:
                self.enemies.remove(enemy)

        # World Generation
        self.generate_world()

        # Level up
        new_level = 1 + int(self.player.world_x / 20000)
        if new_level > self.level:
            self.level = new_level

        # Camera
        self.camera_x = self.player.world_x - WIDTH // 3

    def generate_world(self):
        # Platforms
        if len(self.platforms) < 20 or self.platforms[-1].x < self.player.world_x + 1000:
            x = self.player.world_x + random.randint(600, 1200)
            if random.random() < 0.7:
                h = random.randint(40, 70)
                self.platforms.append(pygame.Rect(x, GROUND_Y - h, random.randint(50, 90), h))
            else:
                self.platforms.append(pygame.Rect(x, GROUND_Y - random.randint(100, 220), random.randint(70, 140), 20))
        self.platforms = [p for p in self.platforms if p.right > self.player.world_x - 500]

        # Coins
        if len(self.coins) < 12 and random.random() < 0.015:
            x = self.player.world_x + random.randint(400, 1000)
            y = GROUND_Y - random.randint(40, 200)
            self.coins.append(pygame.Rect(x, y, 16, 16))
        self.coins = [c for c in self.coins if c.right > self.player.world_x - 500]

        # Power-ups
        if len(self.power_ups) == 0 and random.random() < 0.0008:
            x = self.player.world_x + random.randint(1500, 2500)
            y = GROUND_Y - random.randint(60, 180)
            self.power_ups.append(pygame.Rect(x, y, 24, 24))
        self.power_ups = [pu for pu in self.power_ups if pu.right > self.player.world_x - 500]

        # Enemies
        self.spawn_timer += self.dt
        spawn_interval = max(2.0 - self.level * 0.15, 0.8)
        if self.spawn_timer > spawn_interval:
            self.spawn_timer = 0.0
            spawn_x = self.player.world_x - random.randint(250, 450)
            self.enemies.append(Enemy(self, spawn_x))

    def draw(self):
        self.screen.fill(SKY_BLUE)
        if self.state == 'start_screen':
            self.draw_start_screen()
        elif self.state == 'playing':
            self.draw_game()
        elif self.state == 'game_over':
            self.draw_game() # Draw final frame
            self.draw_game_over_screen()
        pygame.display.flip()

    def draw_game(self):
        # Ground
        pygame.draw.rect(self.screen, GREEN, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))

        # Platforms
        for plat in self.platforms:
            sx = plat.x - self.camera_x
            pygame.draw.rect(self.screen, BROWN, (sx, plat.y, plat.width, plat.height))
            pygame.draw.line(self.screen, BRICK_LINE, (sx, plat.y + 8), (sx + plat.width, plat.y + 8), 2)

        # Items
        for coin in self.coins:
            sx = coin.x - self.camera_x
            pygame.draw.rect(self.screen, YELLOW, (sx, coin.y, 16, 16))
            pygame.draw.rect(self.screen, WHITE, (sx + 4, coin.y + 4, 8, 8))
        for pu in self.power_ups:
            sx = pu.x - self.camera_x
            pygame.draw.rect(self.screen, GREEN, (sx, pu.y, 24, 24))
            pygame.draw.rect(self.screen, WHITE, (sx + 6, pu.y + 6, 12, 12))

        # Enemies
        for enemy in self.enemies:
            sx, sy = enemy.get_screen_pos(self.camera_x)
            pygame.draw.rect(self.screen, RED, (sx, sy, enemy.w, enemy.h))

        # Player
        px, py = self.player.get_screen_pos(self.camera_x)
        color = BLUE
        if self.player.invincible:
            color = YELLOW if int(time.time() * 10) % 2 else GREEN
        pygame.draw.rect(self.screen, color, (px, py, self.player.w, self.player.h))
        pygame.draw.circle(self.screen, WHITE, (px + 8, py + 12), 5)
        pygame.draw.circle(self.screen, WHITE, (px + 20, py + 12), 5)
        pygame.draw.circle(self.screen, BLACK, (px + 9, py + 13), 2)
        pygame.draw.circle(self.screen, BLACK, (px + 21, py + 13), 2)

        # UI
        distance = int(self.player.world_x / 10)
        total_score = self.score + distance
        ui_text = self.font.render(f"Score: {total_score}  Level: {self.level}  Distance: {distance // 10}m", True, BLACK)
        self.screen.blit(ui_text, (10, 10))

    def draw_start_screen(self):
        title = self.large_font.render("Chor Police Adventure", True, BLACK)
        prompt = self.font.render("Press any key to start", True, BLACK)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 100))
        self.screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 20))

    def draw_game_over_screen(self):
        distance = int(self.player.world_x / 10)
        total_score = self.score + distance
        self.high_score = max(self.high_score, total_score)

        over_text = self.large_font.render("CAUGHT! GAME OVER", True, RED)
        final_score = self.font.render(f"Final Score: {total_score}  High: {self.high_score}", True, BLACK)
        restart_text = self.font.render("Press R to Restart", True, BLACK)
        self.screen.blit(over_text, (WIDTH // 2 - over_text.get_width() // 2, HEIGHT // 2 - 100))
        self.screen.blit(final_score, (WIDTH // 2 - final_score.get_width() // 2, HEIGHT // 2 - 20))
        self.screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 60))

# --- Main Execution ---
if __name__ == '__main__':
    game = Game()
    game.run()
    pygame.quit()
    sys.exit()
