# НАПИСАНО НЕЙРОНКОЙ
import numpy as np
import random
from typing import List, Tuple
from entity import Entity
from components import Transform, Physics, Collider, Render
from event_system import EventBus, Phase
from game import Game, Input
import time
from game import *

class PlayerController:
    """Система управления игроком через события"""
    def __init__(self, game: Game, player: Entity):
        self.game = game
        self.player = player
        self.jump_force = 200.0
        self.move_force = 150.0
        
        # Подписываемся на события
        game.event_bus.subscribe(
            id=100,
            phase=Phase.REACTION,
            event_type=EntityTickEvent,
            handler=self._on_player_tick
        )
        
        # Настройка управления
        self._setup_controls()
    
    def _setup_controls(self):
        """Настройка клавиш управления"""
        input_system = self.game.input
        
        # Прыжок (пробел)
        input_system.bind_key(
            key=' ',
            on_press=self._jump
        )
        
        # Движение влево (A/стрелка влево)
        input_system.bind_key(
            key='a',
            on_press=lambda: self._start_move(-1),
            on_release=self._stop_move
        )
        input_system.bind_key(
            key='left',
            on_press=lambda: self._start_move(-1),
            on_release=self._stop_move
        )
        
        # Движение вправо (D/стрелка вправо)
        input_system.bind_key(
            key='d',
            on_press=lambda: self._start_move(1),
            on_release=self._stop_move
        )
        input_system.bind_key(
            key='right',
            on_press=lambda: self._start_move(1),
            on_release=self._stop_move
        )
        
        # Пауза (P)
        input_system.bind_key(
            key='p',
            on_press=self._toggle_pause
        )
    
    def _jump(self):
        """Обработка прыжка"""
        if self.player.physics:
            # Проверяем, стоит ли игрок на земле (упрощенно)
            if abs(self.player.physics.velocity[1]) < 1.0:
                self.player.physics.velocity[1] = self.jump_force
    
    def _start_move(self, direction: int):
        """Начало движения"""
        if self.player.physics:
            self.player.physics.acceleration[0] = direction * self.move_force
    
    def _stop_move(self):
        """Остановка движения"""
        if self.player.physics:
            self.player.physics.acceleration[0] = 0.0
    
    def _toggle_pause(self):
        """Переключение паузы"""
        print("\n=== ПАУЗА ===")
        print("Нажмите P для продолжения")
    
    def _on_player_tick(self, event: EntityTickEvent):
        """Обработка каждого тика для игрока"""
        if event.entity != self.player:
            return
        
        # Ограничиваем максимальную скорость падения
        if self.player.physics.velocity[1] < -300:
            self.player.physics.velocity[1] = -300
        
        # Гравитация
        self.player.physics.acceleration[1] = -500.0

class CoinSystem:
    """Система монеток и подсчета очков"""
    def __init__(self, game: Game):
        self.game = game
        self.coins_collected = 0
        self.total_coins = 0
        
        # Подписываемся на события столкновений
        game.event_bus.subscribe(
            id=101,
            phase=Phase.REACTION,
            event_type=CollisionEvent,
            handler=self._on_collision
        )
        
        # Подписываемся на каждый тик для обновления UI
        game.event_bus.subscribe(
            id=102,
            phase=Phase.REACTION,
            event_type=TickEvent,
            handler=self._on_tick
        )
    
    def _on_collision(self, event: CollisionEvent):
        """Обработка столкновений"""
        player = None
        coin = None
        
        # Определяем, кто есть кто
        if event.e1.render and event.e1.render.texture_id == 'player':
            player = event.e1
            other = event.e2
        elif event.e2.render and event.e2.render.texture_id == 'player':
            player = event.e2
            other = event.e1
        else:
            return
        
        # Если столкнулись с монеткой
        if other.render and other.render.texture_id == 'coin':
            self.coins_collected += 1
            print(f"\nМонетка собрана! Всего: {self.coins_collected}/{self.total_coins}")
            
            # Удаляем монетку
            self.game.remove_entity(other.id)
            
            # Проверка победы
            if self.coins_collected >= self.total_coins:
                print("\n" + "="*40)
                print("ПОБЕДА! Все монетки собраны!")
                print("="*40)
                time.sleep(3)
                self.game.is_running = False
    
    def _on_tick(self, event: TickEvent):
        """Обновление UI каждый тик"""
        # В реальной игре здесь был бы вывод на экран
        pass

class EnemyAI:
    """ИИ для врагов"""
    def __init__(self, game: Game):
        self.game = game
        
        game.event_bus.subscribe(
            id=103,
            phase=Phase.REACTION,
            event_type=EntityTickEvent,
            handler=self._on_enemy_tick
        )
    
    def _on_enemy_tick(self, event: EntityTickEvent):
        """Обработка тика для врага"""
        entity = event.entity
        
        # Проверяем, что это враг
        if not (entity.render and entity.render.texture_id == 'enemy'):
            return
        
        # Простой патрулирующий ИИ
        if entity.physics:
            # Меняем направление каждые 3 секунды
            current_time = time.time()
            if hasattr(entity, 'last_direction_change'):
                if current_time - entity.last_direction_change > 3:
                    entity.move_direction *= -1
                    entity.last_direction_change = current_time
            else:
                entity.move_direction = 1 if random.random() > 0.5 else -1
                entity.last_direction_change = current_time
            
            # Применяем движение
            entity.physics.velocity[0] = entity.move_direction * 50

def create_platform(game: Game, x: float, y: float, width: int, height: int) -> Entity:
    """Создание платформы"""
    platform = Entity(len(game.entities_list))
    platform.add_component(Transform(np.array([x, y], dtype=np.float32)))
    platform.add_component(Physics(
        mass=1000.0,  # Очень тяжелая
        velocity=np.array([0.0, 0.0], dtype=np.float32),
        acceleration=np.array([0.0, 0.0], dtype=np.float32),
        velocity_limit=0.0
    ))
    platform.add_component(Collider(
        hitbox_x=width,
        hitbox_y=height,
        has_collision=True
    ))
    platform.add_component(Render(
        is_visible=True,
        draw_priority=1,
        texture_id='platform'
    ))
    return platform

def create_coin(game: Game, x: float, y: float) -> Entity:
    """Создание монетки"""
    coin = Entity(len(game.entities_list))
    coin.add_component(Transform(np.array([x, y], dtype=np.float32)))
    coin.add_component(Physics(
        mass=1.0,
        velocity=np.array([0.0, 0.0], dtype=np.float32),
        acceleration=np.array([0.0, 0.0], dtype=np.float32),
        velocity_limit=0.0
    ))
    coin.add_component(Collider(
        hitbox_x=2,
        hitbox_y=2,
        has_collision=True
    ))
    coin.add_component(Render(
        is_visible=True,
        draw_priority=3,
        texture_id='coin'
    ))
    return coin

def create_enemy(game: Game, x: float, y: float) -> Entity:
    """Создание врага"""
    enemy = Entity(len(game.entities_list))
    enemy.add_component(Transform(np.array([x, y], dtype=np.float32)))
    enemy.add_component(Physics(
        mass=10.0,
        velocity=np.array([0.0, 0.0], dtype=np.float32),
        acceleration=np.array([0.0, 0.0], dtype=np.float32),
        velocity_limit=100.0
    ))
    enemy.add_component(Collider(
        hitbox_x=3,
        hitbox_y=3,
        has_collision=True
    ))
    enemy.add_component(Render(
        is_visible=True,
        draw_priority=2,
        texture_id='enemy'
    ))
    return enemy

def create_player(game: Game, x: float, y: float) -> Entity:
    """Создание игрока"""
    player = Entity(len(game.entities_list))
    player.add_component(Transform(np.array([x, y], dtype=np.float32)))
    player.add_component(Physics(
        mass=10.0,
        velocity=np.array([0.0, 0.0], dtype=np.float32),
        acceleration=np.array([0.0, -500.0], dtype=np.float32),  # Гравитация
        velocity_limit=200.0
    ))
    player.add_component(Collider(
        hitbox_x=4,
        hitbox_y=4,
        has_collision=True
    ))
    player.add_component(Render(
        is_visible=True,
        draw_priority=4,  # Игрок рисуется поверх всего
        texture_id='player'
    ))
    return player

def load_textures():
    """Загрузка текстур для игры"""
    textures = {
        "player": [" ██ ", "████", " ██ ", " ██ "],
        "platform": ["████████", "████████", "████████"],
        "coin": [" $$ ", "$  $", " $$ "],
        "enemy": [" /\\ ", "<██>", " \\/ "]
    }
    
    # Сохраняем в файл (как ожидает движок)
    import json
    with open('textures.json', 'w') as f:
        json.dump(textures, f, indent=2)

def create_level(game: Game) -> Tuple[Entity, int]:
    """Создание уровня"""
    print("Создание уровня...")
    
    # Создаем платформы
    platforms = [
        # Пол
        (0, 5, 40, 2),
        # Платформы
        (5, 10, 8, 2),
        (20, 12, 8, 2),
        (10, 16, 6, 2),
        (28, 18, 6, 2),
        # Стены
        (38, 7, 2, 15),
        (0, 7, 2, 15)
    ]
    
    for x, y, w, h in platforms:
        game.add_entity(create_platform(game, x, y, w, h))
    
    # Создаем монетки
    coin_positions = [
        (8, 12), (25, 14), (12, 18), (30, 20),
        (15, 8), (22, 8), (30, 10)
    ]
    
    for x, y in coin_positions:
        game.add_entity(create_coin(game, x, y))
    
    # Создаем врагов
    enemy_positions = [
        (15, 12), (25, 18)
    ]
    
    for x, y in enemy_positions:
        game.add_entity(create_enemy(game, x, y))
    
    # Создаем игрока
    player = create_player(game, 5.0, 15.0)
    game.add_entity(player)
    
    return player, len(coin_positions)

def main():
    """Основная функция игры"""
    print("="*50)
    print("    ПЛАТФОРМЕР - СОБЕРИ ВСЕ МОНЕТКИ!")
    print("="*50)
    print("\nУправление:")
    print("  A/← - Влево")
    print("  D/→ - Вправо")
    print("  Пробел - Прыжок")
    print("  P - Пауза")
    print("\nЦель: собрать все монетки, избегая врагов!")
    print("="*50)
    
    # Загружаем текстуры
    load_textures()
    
    # Создаем игру
    game = Game(
        resolution=(80, 30),  # Широкий экран для платформера
        fps=60,
        tickspeed=120,
        elasticity=0.3  # Немного отскока
    )
    
    # Создаем уровень
    player, total_coins = create_level(game)
    
    # Настраиваем игрока
    game.set_player(player)
    
    # Инициализируем системы
    player_controller = PlayerController(game, player)
    coin_system = CoinSystem(game)
    enemy_ai = EnemyAI(game)
    
    # Устанавливаем общее количество монеток
    coin_system.total_coins = total_coins
    
    # Подписываемся на столкновение с врагами (проигрыш)
    def on_enemy_collision(event: CollisionEvent):
        """Обработка столкновения с врагом"""
        entities = (event.e1, event.e2)
        if player in entities:
            print("\n" + "="*40)
            print("ВЫ ПРОИГРАЛИ! Столкнулись с врагом!")
            print("="*40)
            time.sleep(3)
            game.is_running = False
    
    game.event_bus.subscribe(
        id=104,
        phase=Phase.REACTION,
        event_type=CollisionEvent,
        handler=on_enemy_collision
    )
    
    # Подписываемся на падение в бездну
    def on_player_tick(event: EntityTickEvent):
        """Проверка падения игрока"""
        if event.entity != player:
            return
        
        # Если игрок упал слишком низко
        if player.transform.pos[1] < -10:
            print("\n" + "="*40)
            print("ВЫ ПРОИГРАЛИ! Упали в бездну!")
            print("="*40)
            time.sleep(3)
            game.is_running = False
    
    game.event_bus.subscribe(
        id=105,
        phase=Phase.REACTION,
        event_type=EntityTickEvent,
        handler=on_player_tick
    )
    
    # Запускаем игру
    print("\nЗапуск игры... Удачи!")
    time.sleep(2)
    
    try:
        game.run()
    except KeyboardInterrupt:
        print("\n\nИгра прервана пользователем")
    finally:
        print("\n" + "="*50)
        print(f"Игра окончена! Собрано монет: {coin_system.coins_collected}/{total_coins}")
        print("="*50)

if __name__ == "__main__":
    main()