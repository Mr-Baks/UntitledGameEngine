class Colors:
    """Collection of predefined ANSI colors and RGB to ANSI converter."""
    WHITE   = "38;2;255;255;255"
    BLACK   = "38;2;0;0;0"
    RED     = "38;2;255;70;70"
    GREEN   = "38;2;70;255;70"
    BLUE    = "38;2;70;140;255"
    YELLOW  = "38;2;255;220;60"
    CYAN    = "38;2;60;255;220"
    MAGENTA = "38;2;255;80;220"
    ORANGE  = "38;2;255;140;20"
    PINK    = "38;2;255;100;180"
    GRAY    = "38;2;170;170;170"

    _cache: dict[tuple[int, int, int], str] = {}

    @staticmethod
    def rgb_to_ansi(r: int, g: int, b: int) -> str:
        """Convert RGB values to ANSI 24-bit color code."""
        color = (r, g, b)

        if color not in Colors._cache: 
            Colors._cache[color] = f'38;2;{r};{g};{b}'

        return Colors._cache[color]