import numpy as np

class UIElement:
    def __init__(self, pos: tuple[float], width: float, height: float, text: str, has_focus: bool = False, line_length: int | None = None):
        self.pos = pos
        self.width = width - 2
        self.height = height - 2
        self.text = text
        self.has_focus = has_focus
        self.is_focused = False
        self.update_func = None

        self.highlight_symbols = {
            'standart': ('+', '-', '|'),
            'focused': ('@', '=', 'I'),
        }
        
        if line_length is None:
            self.line_length = int(self.width)
        elif line_length > int(self.width):
            self.line_length = int(self.width)
        else:
            self.line_length = line_length

    def _get_spaces_length(self, position: str, length: int):
        match position:
            case 'left' | 'top': 
                left_spaces = 0
                right_spaces = length
            case 'center': 
                left_spaces = length // 2
                right_spaces = length - left_spaces
            case 'right' | 'bottom': 
                left_spaces = length
                right_spaces = 0

        return int(left_spaces), int(right_spaces)

    def set_texture(self, update_func=None, horizontal_position: str = 'center', vertical_position: str = 'center'):
        corner_sym, ceil_sym, wall_sym = self.highlight_symbols['focused'] if self.is_focused and self.has_focus else self.highlight_symbols['standart']

        self.texture = []
        self.texture.append(corner_sym + ceil_sym * self.line_length + corner_sym)

        for line_number in range(1, int(self.height) + 1):
            total_lines = np.ceil(len(self.text) / self.line_length)
            top_empty_lines, _ = self._get_spaces_length(vertical_position, self.height - total_lines)

            if line_number > top_empty_lines:
                line_text = self.text[self.line_length * (line_number - top_empty_lines - 1):self.line_length * (line_number - top_empty_lines)]
                spaces_length = self.line_length - len(line_text)
            else:
                line_text = ''
                spaces_length = self.line_length  # Исправлено с self.width на self.line_length
            
            left_spaces, right_spaces = self._get_spaces_length(horizontal_position, spaces_length)
            self.texture.append(wall_sym + ' ' * left_spaces + line_text + ' ' * right_spaces + wall_sym)

        self.texture.append(corner_sym + ceil_sym * self.line_length + corner_sym)
        
        if update_func:
            update_func()

    def focus(self):
        self.is_focused = not self.is_focused
        self.set_texture()

    def click(self): pass

class Button(UIElement):
    def __init__(self, pos, width, height, text, line_length=None, on_click=None):
        super().__init__(pos, width, height, text, has_focus=True, line_length=line_length)  # Добавлен has_focus
        self.on_click = on_click

    def click(self, UI=None):
        if self.on_click:
            self.on_click(UI)

class Label(UIElement):
    def __init__(self, pos, width, height, text, line_length=None):
        super().__init__(pos, width, height, text, has_focus=False, line_length=line_length)  

class ProgressBar(UIElement):
    def __init__(self, pos, width, height, text, line_length=None, fill_sym: str = '#', empty_sym: str = '-'):
        super().__init__(pos, width, height, text, has_focus=False, line_length=line_length)
        self.fill_sym = fill_sym
        self.empty_sym = empty_sym
        self.progress = 0.0

    def update(self, current: float, maximum: float):
        filled = int((current / maximum) * self.width * self.height)
        self.text = self.fill_sym * filled + self.empty_sym * (self.width * self.height - filled)
        self.set_texture(horizontal_position='left')
        

class UI:
    def __init__(self, resolution, *UI_elements):
        self.elements_list = []
        self.elements_list_focus = []
        self.resolution = resolution
        self.focus_index = 0
        for elem in UI_elements: 
            self.elements_list.append(elem)
            if elem.has_focus: self.elements_list_focus.append(elem)
            elem.update_func = 1
            elem.set_texture()  
        self.update_screen()

    def update_screen(self):
        for elem in self.elements_list:
            elem.set_texture()


    def print_screen(self):
        screen = [[' ' for _ in range(self.resolution[0])] for _ in range(self.resolution[1])]

        for elem in self.elements_list:
            texture = elem.texture

            screen_x_start = int(self.resolution[0] // 2 + elem.pos[0])
            screen_x_end = screen_x_start + int(elem.width) + 2
            screen_y_start = int(self.resolution[1] // 2 - elem.pos[1] - elem.height)
            screen_y_end = screen_y_start + int(elem.height) + 2 
                
            screen_x_min = max(0, screen_x_start)
            screen_x_max = min(self.resolution[0], screen_x_end)
            screen_y_min = max(0, screen_y_start)
            screen_y_max = min(self.resolution[1], screen_y_end)
                
            for screen_y in range(screen_y_min, screen_y_max):
                texture_y = screen_y - screen_y_start
                if texture_y < 0 or texture_y >= len(texture):
                    continue
                for screen_x in range(screen_x_min, screen_x_max):
                    texture_x = screen_x - screen_x_start
                    if texture_x < 0 or texture_x >= len(texture[texture_y]):
                        continue
                    screen[screen_y][screen_x] = texture[texture_y][texture_x]
            
        for row in screen:
            print(''.join(row))

    def main_loop(self):
        while True:
            focused_elem = self.elements_list_focus[self.focus_index]
            focused_elem.focus()
            self.print_screen() 
            focused_elem.focus()
            match input():
                case 'q': break
                case 'a': self.focus_index = (self.focus_index - 1) % len(self.elements_list_focus)
                case 'd': self.focus_index = (self.focus_index + 1) % len(self.elements_list_focus)
                case 'z': focused_elem.click(self)

z = 1500
def plus(UI):
    global z
    z = min(25, z + 1)
    UI.elements_list[-2].text = str(z)
    UI.elements_list[-2].set_texture()
    UI.elements_list[-1].update(z, 25)

def minus(UI):
    global z
    z = max(0, z - 1)
    UI.elements_list[-2].text = str(z)
    UI.elements_list[-2].set_texture()
    UI.elements_list[-1].update(z, 25)



# a = UI((120, 25), 
#     Label((0, 10), 30, 3, '!COUNTER!'),
#     Button((19, 0), 11, 5, '+1', on_click=plus),
#     Button((0, 0), 11, 5, '-1', on_click=minus),
#     Label((10, 5), 10, 5, '1500'), 
#     ProgressBar((0, -5), 30, 3, 'progress!')

# )

# a.elements_list[-1].update(8, 10)
# print(a.elements_list[-1].text + 'a')
# a.main_loop()

# import time
# for i in range(34):
#     a.elements_list[0].line_length = i + 1
#     a.elements_list[0].width = i + 3
#     a.elements_list[0].set_texture()
#     a.print_screen()
#     time.sleep(0.1)