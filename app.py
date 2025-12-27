import pygame
import sys
import random
import os

# --- Constants ---
WIDTH, HEIGHT = 1024, 576
SKY_BLUE = (135, 206, 235)
GROUND_COLOR = (34, 139, 34)
PLATFORM_COLOR = (139, 69, 19)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

GRAVITY = 1500.0
PLAYER_SPEED = 300.0
ENEMY_SPEED = 299.0
JUMP_STRENGTH = -650.0
GROUND_Y = HEIGHT - 80
ASSETS_DIR = 'assets'

# --- Helper ---
def load_image(name, scale=None):
    fullname = os.path.join(ASSETS_DIR, name)
    try:
        image = pygame.image.load(fullname).convert_alpha()
    except pygame.error:
        print(f"Cannot load image: {name}")
        return pygame.Surface((1,1)) # Return dummy surface
    if scale:
        image = pygame.transform.scale(image, scale)
    return image

# --- Base Entity Class ---
class Entity:
    def __init__(self, game, image, world_x, world_y):
        self.game = game
        self.base_image = image
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.world_x = float(world_x)
        self.world_y = float(world_y)
        self.rect.topleft = (self.world_x, self.world_y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False

    def handle_horizontal_collision(self):
        for plat in self.game.platforms:
            if self.rect.colliderect(plat):
                if self.vel_x > 0: self.rect.right = plat.left
                elif self.vel_x < 0: self.rect.left = plat.right
                self.vel_x = 0.0
        self.world_x = self.rect.x

    def handle_vertical_collision(self):
        self.on_ground = False
        for plat in self.game.platforms:
            if self.rect.colliderect(plat):
                if self.vel_y > 0:
                    self.rect.bottom = plat.top
                    self.vel_y = 0.0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = plat.bottom
                    self.vel_y = 0.0
        self.world_y = self.rect.y

    def update_physics(self, dt):
        self.world_x += self.vel_x * dt
        self.rect.x = self.world_x
        self.handle_horizontal_collision()
        self.world_y += self.vel_y * dt
        self.rect.y = self.world_y
        self.handle_vertical_collision()

    def get_screen_pos(self, camera_x):
        return self.world_x - camera_x, self.world_y

# --- Player ---
class Player(Entity):
    def __init__(self, game):
        super().__init__(game, game.assets['chor'], 100.0, GROUND_Y - 68)
        self.direction = 1

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.vel_x = 0.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
            self.direction = 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
            self.direction = -1
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH
        self.vel_y += GRAVITY * dt
        self.update_physics(dt)
        self.image = pygame.transform.flip(self.base_image, self.direction == -1, False)

# --- Enemy ---
class Enemy(Entity):
    def __init__(self, game, world_x, world_y):
        img = random.choice([game.assets['police1'], game.assets['police2']])
        super().__init__(game, img, world_x, world_y)
        self.direction = 1.0
        self.react_timer = 0.0

    def update(self, dt):
        player = self.game.player
        dist_x = player.world_x - self.world_x
        self.react_timer += dt
        if self.react_timer > 0.4:
            if abs(dist_x) > 50: self.direction = 1.0 if dist_x > 0 else -1.0
            self.react_timer = 0.0
        self.vel_x = self.direction * ENEMY_SPEED
        if self.on_ground:
            if (player.world_y < self.world_y - 60 and abs(dist_x) < 140):
                self.vel_y = JUMP_STRENGTH * 0.8
            probe_x = self.world_x + self.direction * 60
            wall_exists = any(p.collidepoint(probe_x, self.world_y + 30) for p in self.game.platforms)
            if wall_exists: self.vel_y = JUMP_STRENGTH * 0.82
        self.vel_y += GRAVITY * dt
        self.update_physics(dt)
        self.image = pygame.transform.flip(self.base_image, self.direction < 0, False)

# --- Game ---
class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chor Police Adventure")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 40)
        self.big_font = pygame.font.SysFont(None, 80)
        self.state = 'start'
        self.camera_x = 0
        self.load_assets()
        self.play_music('intro')

    def load_assets(self):
        self.assets = {
            'chor': load_image('chor.png', scale=(40, 68)),
            'police1': load_image('police.png', scale=(40, 68)),
            'police2': load_image('police2.png', scale=(40, 68)),
            'intro_bg': load_image('intro.png', scale=(WIDTH, HEIGHT)),
            'win_bg': load_image('victory.png', scale=(WIDTH, HEIGHT)),
            'fail_bg': load_image('failed.png', scale=(WIDTH, HEIGHT)),
            'flag': load_image('flag.png', scale=(70, 220))
        }
        self.music = {
            'intro': os.path.join(ASSETS_DIR, 'intro.mp3'),
            'background': os.path.join(ASSETS_DIR, 'background.mp3'),
            'win': os.path.join(ASSETS_DIR, 'victory.mp3'),
            'fail': os.path.join(ASSETS_DIR, 'failed.mp3')
        }

    def play_music(self, track_name, loops=0):
        if track_name not in self.music:
            print(f"Music track '{track_name}' not found!")
            return
        pygame.mixer.music.load(self.music[track_name])
        pygame.mixer.music.play(loops)

    def create_level(self):
        self.platforms = []
        for x in range(0, 3400, 100):
            self.platforms.append(pygame.Rect(x, GROUND_Y, 100, HEIGHT - GROUND_Y))
        extra_platforms = [
            (550, GROUND_Y - 130, 280, 25), (950, GROUND_Y - 240, 220, 25),
            (1350, GROUND_Y - 170, 280, 25), (1750, GROUND_Y - 300, 320, 25),
            (2150, GROUND_Y - 130, 220, 25), (2500, GROUND_Y - 200, 180, 25),
            (2800, GROUND_Y - 350, 150, 25), (3100, GROUND_Y - 100, 200, 25),
        ]
        for pos in extra_platforms: self.platforms.append(pygame.Rect(pos))
        self.goal = self.assets['flag'].get_rect(topleft=(3250, GROUND_Y - 220))

    def reset(self):
        self.create_level()
        self.player = Player(self)
        self.enemies = [
            Enemy(self, 780, GROUND_Y - 68),
            Enemy(self, 1480, GROUND_Y - 170 - 68),
            Enemy(self, 2180, GROUND_Y - 130 - 68),
        ]
        self.score = 0
        self.state = 'playing'
        self.camera_x = 0
        self.play_music('background', loops=-1)

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            if self.state == 'playing': self.update(dt)
            self.draw()
            pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.state == 'start': self.reset()
                elif self.state in ['game_over', 'win']:
                    if event.key == pygame.K_r:
                        self.state = 'start'
                        self.play_music('intro', loops=-1)

    def update(self, dt):
        self.player.update(dt)
        for enemy in self.enemies:
            enemy.update(dt)
            if self.player.rect.colliderect(enemy.rect):
                self.state = 'game_over'
                self.play_music('fail')
                return
        if self.player.rect.colliderect(self.goal):
            self.state = 'win'
            self.play_music('win')
        target_cam = max(0, self.player.world_x - WIDTH // 3)
        self.camera_x += (target_cam - self.camera_x) * 0.1
        self.score = int(self.player.world_x / 10)

    def draw(self):
        if self.state == 'start': self.draw_start(); return
        self.screen.fill(SKY_BLUE)
        cam = self.camera_x
        for plat in self.platforms:
            color = GROUND_COLOR if plat.height > 50 else PLATFORM_COLOR
            pygame.draw.rect(self.screen, color, plat.move(-cam, 0))
        self.screen.blit(self.assets['flag'], self.goal.move(-cam, 0))
        for e in self.enemies: self.screen.blit(e.image, e.get_screen_pos(cam))
        self.screen.blit(self.player.image, self.player.get_screen_pos(cam))
        score_t = self.font.render(f"Score: {self.score}", True, BLACK)
        self.screen.blit(score_t, (20, 20))
        if self.state == 'game_over': self.draw_overlay('fail_bg', "CAUGHT BY POLICE!", RED)
        elif self.state == 'win': self.draw_overlay('win_bg', "YOU ESCAPED! 🏆", (0, 200, 0))

    def draw_start(self):
        self.screen.blit(self.assets['intro_bg'], (0, 0))
        title = self.big_font.render("Chor Police Adventure", True, WHITE)
        prompt = self.font.render("Press any key to start the chase!", True, WHITE)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 60))
        self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 + 20))

    def draw_overlay(self, bg_image_key, msg, color):
        self.screen.blit(self.assets[bg_image_key], (0, 0))
        msg_t = self.big_font.render(msg, True, color)
        restart_t = self.font.render("Press R to return to the main menu", True, WHITE)
        self.screen.blit(msg_t, (WIDTH//2 - msg_t.get_width()//2, HEIGHT//2 - 80))
        self.screen.blit(restart_t, (WIDTH//2 - restart_t.get_width()//2, HEIGHT//2 + 40))

if __name__ == '__main__':
    Game().run()