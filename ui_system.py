from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Optional
from copy import deepcopy
from system_manager import RenderSystem, Compositor
from event_system import Phase


class UIElement(ABC):
    def __init__(self, name: str, x: int, y: int, w: int, h: int, draw_priority: int = 0, is_visible: bool = True, transparent_sym: str = '`', fill_transparent: bool = True, background_sym: str = ' '):
        self.name = name
        self.x, self.y = x, y
        self.w, self.h = w, h
        self.size = w * h
        self.draw_priority = draw_priority
        self.is_visible = is_visible
        self.transparent_sym = transparent_sym
        self.background_sym = background_sym
        self.fill_transparent = fill_transparent
        self.children: dict[str, UIElement] = {}
        self.parent = None
        self.texture = [[self.transparent_sym for _ in range(self.w)] for _ in range(self.h)]
        self.own_texture = [[self.transparent_sym for _ in range(self.w)] for _ in range(self.h)]
        self.dirty = True
        self.own_dirty = True

    def _notify_dirty(self):
        self.dirty = True
        self.own_dirty = True
        if self.parent: 
            self.parent._notify_dirty()

    def add_child(self, child: UIElement) -> None:
        if child.is_visible: self._notify_dirty()
        child.parent = self
        self.children[child.name] = child

    def toggle_visible(self):
        self.is_visible = not self.is_visible 
        self._notify_dirty()

    def remove_child(self, name: str) -> Optional[UIElement]:
        if name in self.children:
            removed = self.children.pop(name)
            removed.parent = None
            self._notify_dirty()
            return removed
        return None

        return removed

    def get_texture(self) -> list[list[str]]: 
        if not self.dirty:
            return self.texture
        if self.own_dirty:
            self.rebuild()
            self.own_dirty = False

        self.texture = deepcopy(self.own_texture)

        sorted_children = sorted(self.children.values(), key=lambda e: e.draw_priority)
        for child in sorted_children:
            if not child.is_visible:
                continue
            child_tex = child.get_texture()

            for cy in range(child.h):
                for cx in range(child.w):
                    py = child.y + cy
                    px = child.x + cx
                    if 0 <= px < self.w and 0 <= py < self.h:
                        if child_tex[cy][cx] == child.transparent_sym:
                            if child.fill_transparent: sym = child.background_sym
                            else: continue
                        else: sym = child_tex[cy][cx]
                        self.texture[py][px] = sym

        self.dirty = False
        return self.texture

    @abstractmethod
    def rebuild(self): pass 

class UIElementFocusable(UIElement):
    def __init__(self, name: str, x: int, y: int, w: int, h: int, on_action: Optional[Callable] = None, on_focus: Optional[Callable] = None, on_blur: Optional[Callable] = None, draw_priority: int = 0, is_visible: bool = True, transparent_sym: str = '`', fill_transparent: bool = True, background_sym: str = ' '):
        super().__init__(name, x, y, w, h, draw_priority=draw_priority, is_visible=is_visible, transparent_sym=transparent_sym, fill_transparent=fill_transparent, background_sym=background_sym)
        self.on_action = on_action
        self.on_focus = on_focus
        self.on_blur = on_blur
        self.focused = False
        self.focusable = True

    @abstractmethod
    def set_focus(self): pass

    def handle_action(self, game: 'Game'):
        if self.on_action:
            self.on_action(game)
            
    def handle_focus(self, game: 'Game'):
        if self.on_focus:
            self.on_focus(game)

    def handle_blur(self, game: 'Game'):
        if self.on_blur:
            self.on_blur(game)

class UIScreen(UIElement):
    def __init__(self, name: str, resolution: tuple[int, int]):
        super().__init__(name, 0, 0, *resolution, fill_transparent=False)

    def rebuild(self):
        self.own_texture = [[self.transparent_sym for _ in range(self.w)] for i in range(self.h)]

class Align(Enum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2
    WIDTH = 3

class UIText(UIElement):
    def __init__(self, name: str, x: int, y: int, w: int, h: int, text: str, align: Align = Align.LEFT, draw_priority: int = 0, is_visible: bool = True, transparent_sym: str = '`', fill_transparent: bool = False, background_sym: str = ' '):
        super().__init__(name, x, y, w, h, draw_priority=draw_priority, is_visible=is_visible, transparent_sym=transparent_sym, fill_transparent=fill_transparent, background_sym=background_sym)
        self._text = text
        self.text = text
        self.align = align
        self.lines: list[str] = []

    def _align_line(self, line: list[str]) -> str:
        spaces = self.w - sum([len(s) for s in line])
        sline = ''

        match self.align:
            case Align.RIGHT:
                spaces_per_word = 1
                left_spaces = spaces - len(line) + 1
                right_spaces = 0
            case Align.LEFT:
                spaces_per_word = 1
                left_spaces = 0
                right_spaces = spaces - len(line) + 1
            case Align.CENTER:
                spaces_per_word = 1
                left_spaces = (spaces - len(line) + 1) // 2
                right_spaces = spaces - left_spaces
            case Align.WIDTH:
                if len(line) < 2:
                    spaces_per_word = 0
                    right_spaces = spaces - len(line) + 1
                else: 
                    spaces_per_word = spaces / (len(line) - 1)
                    right_spaces = 0
                left_spaces = 0

        sline += self.transparent_sym * left_spaces

        space_accumulator = 0
        for word in line:
            space_accumulator += spaces_per_word
            sline += word + ' ' * int(space_accumulator)
            space_accumulator -= int(space_accumulator)
        sline += self.transparent_sym * right_spaces

        return sline[:self.w]
            
    def _wrap_text(self) -> list[str]:
        if not self._text:
            return []

        words = self._text.replace('\n', ' __new_line ').split()
        lines = []
        current_line = [] 
        current_len = 0 

        for word in words:
            if word == '__new_line':
                if current_line:
                    lines.append(self._align_line(current_line))
                else:
                    lines.append('') 
                current_line = []
                current_len = 0
                continue

            word_len = len(word)

            if word_len > self.w:
                if current_line:
                    lines.append(self._align_line(current_line))
                    current_line = []
                    current_len = 0
            
                for i in range(0, word_len, self.w):
                    chunk = word[i:i + self.w]
                    lines.append(self._align_line([chunk]))
                continue

            needed = word_len if not current_line else word_len + 1

            if current_len + needed > self.w:
                lines.append(self._align_line(current_line))
                current_line = [word]
                current_len = word_len
            else:
                current_line.append(word)
                current_len += needed

        if current_line:
            lines.append(self._align_line(current_line))

        return lines[:self.h]

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, new_text: str):
        if new_text != self._text:
            self._text = new_text
            self._wrap_text()
            self._notify_dirty()

    def rebuild(self):
        self.own_texture = [[self.transparent_sym for _ in range(self.w)] for _ in range(self.h)]
        self.lines = self._wrap_text()
        print(self.lines)

        for y, line in enumerate(self.lines):
            if y >= self.h: 
                break
            for x, char in enumerate(line):
                if x >= self.w: 
                    break
                self.own_texture[y][x] = char
        
class UIButton(UIElementFocusable):
    def __init__(self, name: str, x: int, y: int, w: int, h: int, text: str, padding: int = 1, on_action: Optional[Callable] = None, on_focus: Optional[Callable] = None, on_blur: Optional[Callable] = None, draw_priority: int = 0, is_visible: bool = True, transparent_sym: str = '`', fill_transparent: bool = True, background_sym: str = ' '):
        super().__init__(name, x, y, w, h, draw_priority=draw_priority, is_visible=is_visible, on_action=on_action, on_blur=on_blur, on_focus=on_focus, transparent_sym=transparent_sym, fill_transparent=fill_transparent, background_sym=background_sym)
        self.padding = padding

        self.label = UIText(f"_{name}_label", padding, padding, w - 2 * padding, h - 2 * padding, text, align=Align.CENTER)
        self.add_child(self.label)

    @property
    def text(self) -> str:
        return self.label.text

    @text.setter
    def text(self, new_text: str):
        self.label.text = new_text

    def set_focus(self):
        if self.focused:
            border_top    = "╔" + "═" * (self.w - 2) + "╗"
            border_bottom = "╚" + "═" * (self.w - 2) + "╝"
            border_side   = "║"
            
            self.own_texture[0] = list(border_top)
            self.own_texture[-1] = list(border_bottom)
            
            for y in range(1, self.h - 1):
                self.own_texture[y][0] = border_side
                self.own_texture[y][-1] = border_side
                
            for y in range(1, self.h - 1):
                for x in range(1, self.w - 1):
                    if self.own_texture[y][x] == self.transparent_sym:
                        self.own_texture[y][x] = ' '
            
        else:
            border_top    = "┌" + "─" * (self.w - 2) + "┐"
            border_bottom = "└" + "─" * (self.w - 2) + "┘"
            border_side   = "│"
            
            self.own_texture[0] = list(border_top)
            self.own_texture[-1] = list(border_bottom)
            
            for y in range(1, self.h - 1):
                self.own_texture[y][0] = border_side
                self.own_texture[y][-1] = border_side

    def rebuild(self):
        self.own_texture = [[self.transparent_sym for _ in range(self.w)] for _ in range(self.h)]
        self.set_focus()
        
class UIProgressBar(UIElement):
    def __init__(self, name: str, x: int, y: int, w: int, h: int, value: float = 0, on_update: Optional[Callable] = None, draw_priority: int = 0, is_visible: bool = True, transparent_sym: str = '`', fill_transparent: bool = True, background_sym: str = ' '):
        super().__init__(name, x, y, w, h, draw_priority=draw_priority, is_visible=is_visible, focusable=False, transparent_sym=transparent_sym, fill_transparent=fill_transparent, background_sym=background_sym)
        self._value = max(0.0, min(1.0, value))
        self._filled_count = int(self.w * self._value) 
        self.filled_sym = '#'
        self.empty_sym = '_'
        self.on_update = on_update

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, new_value: float):
        new_value = max(0.0, min(1.0, new_value))
        new_filled = int(self.w * new_value)
        
        if new_filled == self._filled_count and new_value == self._value:
            return
            
        self._value = new_value
        self._filled_count = new_filled
        self._notify_dirty()
        
        if self.on_update:
            self.on_update(new_value)

    def rebuild(self):
        self.own_texture = [[self.transparent_sym for _ in range(self.w)] for _ in range(self.h)]
        
        for x in range(self._filled_count):
            for y in range(self.h):
                self.own_texture[y][x] = self.filled_sym

class UISystem(RenderSystem):
    def __init__(self, compositor: Compositor, game: 'Game'):
        super().__init__(Phase.RENDER, 5000, frozenset(), compositor)
        self._compositor = compositor
        self._game = game
        
        self.screens: dict[str, UIScreen] = {}
        self.root_screen = None
        self.all_elements: dict[str, UIElement] = {} 
        
        self.focused = None
        self.focusable_elements: list[UIElementFocusable] = [] 

    def register_screen(self, screen: UIScreen):
        if screen.name in self.screens:
            return
        self.screens[screen.name] = screen
        self.root_screen = screen
        self._register_element_recursive(screen)
        self._rebuild_focusable_list()

    def _register_element_recursive(self, element: UIElement):
        self.all_elements[element.name] = element

        for child in element.children.values():
            self._register_element_recursive(child)

    def add_element(self, screen_name: str, element: UIElement, parent_name: Optional[str] = None):
        screen = self.screens.get(screen_name)
        if not screen:
            return 
            
        if parent_name:
            parent = self.all_elements.get(parent_name)
            if parent:
                parent.add_child(element)
        else:
            screen.add_child(element)
            
        self._register_element_recursive(element)

    def _rebuild_focusable_list(self):
        self.focusable_elements.clear()
        if self.root_screen.is_visible:
            self._collect_focusable(self.root_screen)
        if self.focusable_elements and not self.focused:
            self.set_focus(self.focusable_elements[0])

    def _collect_focusable(self, element: UIElement):
        if isinstance(element, UIElementFocusable) and element.focusable and element.is_visible:
            print('z' * 300)
            self.focusable_elements.append(element)
        for child in element.children.values():
            self._collect_focusable(child)

    def set_focus(self, element: Optional[UIElementFocusable]):
        if self.focused == element:
            return
        if element.is_visible and element.focusable:
            if self.focused:
                self.focused.focused = False
                self.focused._notify_dirty()
            element.focused = True
            self.focused = element
            element._notify_dirty()
            
    def change_focus(self, direction: int = 1):
        if not self.focusable_elements:
            print('No')
            return
        if not self.focused:
            self.set_focus(self.focusable_elements[0])
            return

        try:
            idx = self.focusable_elements.index(self.focused)
        except ValueError:
            idx = -1

        if direction == 1:
            new_idx = (idx + 1) % len(self.focusable_elements)
        elif direction == -1:
            new_idx = (idx - 1) % len(self.focusable_elements)
        else:
            return

        self.focused.handle_blur(self._game)
        self.set_focus(self.focusable_elements[new_idx])
        self.focused.handle_focus(self._game)

    def handle_input(self, game: 'Game'):
        if game.input.is_pressed('enter') or game.input.is_pressed('space'):
            if self.focused:
                self.focused.handle_action(game)
        
        if game.input.is_pressed('tab'):
            self.change_focus(1)
        elif game.input.is_pressed('shift+tab'):
            self.change_focus(-1)

    def update(self, _):
        self.clear()
        if self.root_screen.dirty:
            self._collect_focusable(self.root_screen)
        self.handle_input(self._game)

        if not self.root_screen.is_visible:
            return
        tex = self.root_screen.get_texture()
        for y in range(min(self.root_screen.h, self.h)):
            for x in range(min(self.root_screen.w, self.w)):
                char = tex[y][x]
                if char != self.root_screen.transparent_sym:
                    self.put_sym(x, y, char)
                    self.update_mask[y][x] = True
                else:
                    self.update_mask[y][x] = False
        
        self._compositor.merge(self.buffer, self.update_mask)

