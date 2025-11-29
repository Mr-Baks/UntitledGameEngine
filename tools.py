import numpy as np


class Tools:
    @staticmethod
    def to_float(array: tuple[float] | list[float]):
        return np.array(array, dtype=np.float32)
    
