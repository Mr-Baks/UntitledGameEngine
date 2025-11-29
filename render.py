from physics import Object, Static_object
import json

class Scene:
    def __init__(self, resolution, *objects):
        self.objects = objects
        self.obj_list = []
        self.symbols = '@123456789ABCDEF'
        self.resolution = resolution
        self.textures_table = {}
        self.target = None

        with open('textures.json') as f:
            self.textures = json.load(f)
        
        for obj in objects:
            match obj['type']:
                case 'static': 
                    new_object = Static_object(
                        obj['pos'], 
                        hitbox_x=obj.get('hitbox_x', (0, 0)), 
                        hitbox_y=obj.get('hitbox_y', (0, 0)), 
                        mass=obj.get('mass', 1),
                        has_collision=obj.get("has_collision", True)
                    )
                case 'mobile': 
                    new_object = Object(
                        obj['pos'], 
                        obj['velocity'],
                        obj['acceleration'],
                        mass=obj.get('mass', 1), 
                        hitbox_x=obj.get('hitbox_x', (0, 0)), 
                        hitbox_y=obj.get('hitbox_y', (0, 0)), 
                        acc_limit=obj.get('acc_limit', 1), 
                        vel_limit=obj.get('vel_limit', 5),
                        has_collision=obj.get("has_collision", True)
                    )

            draw_priority = obj.get('draw_priority', 0)
            self.obj_list.append((draw_priority, new_object))
            self.textures_table[new_object] = obj.get('texture')
            if obj.get('target'): 
                self.target = new_object
        
        self.obj_list.sort(key=lambda x: x[0])
        self.obj_list = [obj for _, obj in self.obj_list]

    def print_scene(self):
        scene = [[' ' for _ in range(self.resolution[0])] for _ in range(self.resolution[1])]
        center_x, center_y = self.resolution[0] // 2 - int(self.target.pos[0]), self.resolution[1] // 2 + int(self.target.pos[1])

        for i, obj in enumerate(self.obj_list):
            obj_screen_x = center_x + obj.pos[0]
            obj_screen_y = center_y - obj.pos[1]
            
            screen_x_min = int(obj_screen_x)
            screen_x_max = int(obj_screen_x + obj.hitbox_x) + 1
            screen_y_min = int(obj_screen_y - obj.hitbox_y)
            screen_y_max = int(obj_screen_y) + 1

            texture_offset_x = 0
            texture_offset_y = 0
            if screen_x_min < 0:
                texture_offset_x = -screen_x_min
                screen_x_min = 0
            if screen_y_min < 0:
                texture_offset_y = -screen_y_min
                screen_y_min = 0
            
            screen_x_max = min(screen_x_max, self.resolution[0])
            screen_y_max = min(screen_y_max, self.resolution[1])

            sym = self.symbols[i % len(self.symbols)]
            texture = self.textures.get(self.textures_table[obj])
            if texture is None:
                texture_width = max(1, int(abs(obj.hitbox_x)) + 1)
                texture_height = max(1, int(abs(obj.hitbox_y)) + 1)
                texture = [[sym for _ in range(texture_width)] for _ in range(texture_height)]
        
            for screen_y in range(screen_y_min, screen_y_max):
                texture_y = (screen_y - int(obj_screen_y - obj.hitbox_y)) + texture_offset_y
                if texture_y < 0 or texture_y >= len(texture): continue  
                for screen_x in range(screen_x_min, screen_x_max):
                    texture_x = (screen_x - int(obj_screen_x)) + texture_offset_x
                    if texture_x < 0 or texture_x >= len(texture[texture_y]): continue
                    scene[screen_y][screen_x] = texture[texture_y][texture_x]

        print('+' + '-' * self.resolution[0] + '+')
        for row in scene:
            print('|' + ''.join(row) + '|')
        print('+' + '-' * self.resolution[0] + '+' + '\r')
