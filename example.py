# Этот пример делала нейронка
import numpy as np
from game import Game, Entity
from components import Transform, Physics, Collider, Render, Script
import random


class SpaceShooter:
    def __init__(self):
        # Создаем игру с разрешением 80x40, 30 FPS, 60 тиков в секунду
        self.game = Game(
            resolution=(80, 40),
            fps=30,
            tickspeed=60,
            elasticity=0.5
        )
        
        # Настраиваем колбэки
        self.game.on_tick = self.on_tick
        self.game.on_frame = self.on_frame
        
        # Счетчики
        self.score = 0
        self.enemies_count = 0
        self.max_enemies = 15
        self.game_time = 0
        
        # Инициализируем игру
        self.init_game()
    
    def create_player(self):
        """Создает игрока (космический корабль)"""
        player = Entity(id=0)
        player.add_component(Transform(pos=np.array([10.0, 20.0], dtype=np.float32)))
        player.add_component(Physics(
            mass=1.0,
            velocity=np.array([0.0, 0.0], dtype=np.float32),
            acceleration=np.array([0.0, 0.0], dtype=np.float32),
            velocity_limit=5.0
        ))
        player.add_component(Collider(hitbox_x=3, hitbox_y=2, has_collision=True))
        player.add_component(Render(
            is_visible=True,
            draw_priority=2,
            texture_id="player"
        ))
        player.add_component(Script(
            on_tick=lambda game: self.update_player(player),
            on_collision=lambda entity, other: self.on_player_collision(entity, other)
        ))
        
        return player
    
    def create_bullet(self, pos, velocity):
        """Создает пулю"""
        bullet_id = random.randint(1000, 9999)
        bullet = Entity(id=bullet_id)
        bullet.add_component(Transform(pos=pos.copy()))
        bullet.add_component(Physics(
            mass=0.1,
            velocity=velocity,
            acceleration=np.array([0.0, 0.0], dtype=np.float32),
            velocity_limit=20.0
        ))
        bullet.add_component(Collider(hitbox_x=1, hitbox_y=1, has_collision=True))
        bullet.add_component(Render(
            is_visible=True,
            draw_priority=1,
            texture_id="bullet"
        ))
        bullet.add_component(Script(
            on_tick=lambda game: self.update_bullet(bullet),
            on_collision=lambda entity, other: self.on_bullet_collision(entity, other)
        ))
        
        self.game.add_entity(bullet)
        return bullet
    
    def create_enemy(self, pos):
        """Создает вражеский корабль"""
        enemy_id = random.randint(100, 999)
        enemy = Entity(id=enemy_id)
        enemy.add_component(Transform(pos=pos.copy()))
        enemy.add_component(Physics(
            mass=1.5,
            velocity=np.array([-1.0, random.uniform(-0.5, 0.5)], dtype=np.float32),
            acceleration=np.array([0.0, 0.0], dtype=np.float32),
            velocity_limit=3.0
        ))
        enemy.add_component(Collider(hitbox_x=4, hitbox_y=2, has_collision=True))
        enemy.add_component(Render(
            is_visible=True,
            draw_priority=1,
            texture_id="enemy"
        ))
        enemy.add_component(Script(
            on_tick=lambda game: self.update_enemy(enemy),
            on_collision=lambda entity, other: self.on_enemy_collision(entity, other)
        ))
        
        self.game.add_entity(enemy)
        self.enemies_count += 1
        return enemy
    
    def create_star(self):
        """Создает звезду (фон)"""
        star = Entity(id=random.randint(2000, 2999))
        star.add_component(Transform(
            pos=np.array([
                random.uniform(0, 79),
                random.uniform(0, 39)
            ], dtype=np.float32)
        ))
        star.add_component(Render(
            is_visible=True,
            draw_priority=0,
            texture_id="star"
        ))
        star.add_component(Script(
            on_tick=lambda game: self.update_star(star)
        ))
        
        self.game.add_entity(star)
        return star
    
    def update_player(self, player):
        """Обновляет состояние игрока"""
        physics = player.physics
        if physics is None:
            return
        
        # Сбрасываем ускорение
        physics.acceleration = np.array([0.0, 0.0], dtype=np.float32)
        
        # Управление с клавиатуры
        move_speed = 8.0
        if self.game.input.is_pressed('w'):
            physics.acceleration[1] = move_speed
        if self.game.input.is_pressed('s'):
            physics.acceleration[1] = -move_speed
        if self.game.input.is_pressed('a'):
            physics.acceleration[0] = -move_speed
        if self.game.input.is_pressed('d'):
            physics.acceleration[0] = move_speed
        
        # Стрельба
        if self.game.input.is_pressed(' '):
            self.shoot_bullet(player)
        
        # Удержание в границах экрана
        transform = player.transform
        if transform.pos[1] < 1:
            transform.pos[1] = 1
            physics.velocity[1] = 0
        elif transform.pos[1] > 37:
            transform.pos[1] = 37
            physics.velocity[1] = 0
        
        if transform.pos[0] < 1:
            transform.pos[0] = 1
            physics.velocity[0] = 0
    
    def shoot_bullet(self, player):
        """Стрельба пулями"""
        if self.game.tick % 5 != 0:  # Ограничение скорости стрельбы
            return
        
        player_pos = player.transform.pos
        bullet_velocity = np.array([15.0, 0.0], dtype=np.float32)
        bullet_pos = player_pos + np.array([3.0, 1.0], dtype=np.float32)
        
        self.create_bullet(bullet_pos, bullet_velocity)
    
    def update_bullet(self, bullet):
        """Обновление пули"""
        transform = bullet.transform
        physics = bullet.physics
        
        # Удаляем пулю, если она вышла за экран
        if transform.pos[0] > 82 or transform.pos[0] < -5:
            self.game.remove_entity(bullet.id)
    
    def update_enemy(self, enemy):
        """Обновление врага"""
        transform = enemy.transform
        
        # Удаляем врага, если он вышел за левую границу
        if transform.pos[0] < -5:
            self.game.remove_entity(enemy.id)
            self.enemies_count -= 1
        
        # Случайное изменение направления по Y
        if random.random() < 0.05:
            enemy.physics.velocity[1] = random.uniform(-1.0, 1.0)
    
    def update_star(self, star):
        """Обновление звезды (движение влево)"""
        transform = star.transform
        transform.pos[0] -= 0.2
        
        # Если звезда ушла за левую границу, перемещаем ее вправо
        if transform.pos[0] < -1:
            transform.pos[0] = 80
            transform.pos[1] = random.uniform(0, 39)
    
    def on_player_collision(self, player, other):
        """Обработка столкновения игрока"""
        if "enemy" in str(other.render.texture_id):
            print("GAME OVER! Final Score:", self.score)
            self.game.is_running = False
    
    def on_bullet_collision(self, bullet, other):
        """Обработка столкновения пули"""
        if "enemy" in str(other.render.texture_id):
            self.score += 100
            self.game.remove_entity(bullet.id)
            self.game.remove_entity(other.id)
            self.enemies_count -= 1
    
    def on_enemy_collision(self, enemy, other):
        """Обработка столкновения врага"""
        pass
    
    def spawn_enemies(self):
        """Спавн новых врагов"""
        if self.enemies_count < self.max_enemies and random.random() < 0.1:
            pos = np.array([
                78,  # Правая граница
                random.uniform(5, 35)
            ], dtype=np.float32)
            self.create_enemy(pos)
    
    def spawn_stars(self):
        """Создание фоновых звезд"""
        if len([e for e in self.game.entities_list if "star" in str(e.render.texture_id)]) < 30:
            self.create_star()
    
    def on_tick(self, game):
        """Вызывается каждый тик игры"""
        self.game_time += 1
        self.spawn_enemies()
        self.spawn_stars()
        
        # Постепенное увеличение сложности
        if self.game_time % 300 == 0:
            self.max_enemies = min(25, self.max_enemies + 2)
    
    def on_frame(self, game):
        """Вызывается каждый кадр"""
        # Можно добавить визуальные эффекты здесь
    
    def setup_input(self):
        """Настройка управления"""
        self.game.input.bind_key('w')
        self.game.input.bind_key('a')
        self.game.input.bind_key('s')
        self.game.input.bind_key('d')
        self.game.input.bind_key(' ')  # Пробел для стрельбы
        
        # Выход из игры
        self.game.input.bind_key('q', on_press=lambda: self.quit_game())
        self.game.input.bind_key('esc', on_press=lambda: self.quit_game())
    
    def quit_game(self):
        """Выход из игры"""
        print(f"Game ended. Final score: {self.score}")
        self.game.is_running = False
    
    def init_game(self):
        """Инициализация игры"""
        # Создаем игрока
        player = self.create_player()
        self.game.add_entity(player)
        self.game.set_player(player)
        
        # Настраиваем управление
        self.setup_input()
        
        # Создаем начальных врагов
        for _ in range(5):
            pos = np.array([
                random.uniform(30, 70),
                random.uniform(5, 35)
            ], dtype=np.float32)
            self.create_enemy(pos)
        
        # Создаем фоновые звезды
        for _ in range(20):
            self.create_star()
        
        print("=== SPACE SHOOTER ===")
        print("Controls: W/A/S/D - Move, SPACE - Shoot, Q/ESC - Quit")
        print("Destroy enemies to score points!")
        print("=" * 30)
    
    def run(self):
        """Запуск игры"""
        try:
            self.game.run()
        except KeyboardInterrupt:
            print(f"\nGame interrupted. Final score: {self.score}")

if __name__ == "__main__":
    game = SpaceShooter()
    game.run()