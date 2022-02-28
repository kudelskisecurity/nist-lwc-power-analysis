from abc import ABC, abstractmethod
from math import ceil
from typing import Union

from rainbow import rainbowBase

import util


class EmulatorWrapper(ABC):
    """
    Args:
        alg: the name of the algorithm to use (its runtime should be put in the `bin` directory)
    """

    def __init__(self, alg, key_length: int, nonce_length: int, nsec_length: int = 0, sca: bool = False):
        self.alg = alg
        self.key_length = key_length
        self.nonce_length = nonce_length
        self.nsec_length = nsec_length
        self.sca = sca

    def to_bytes(self, msg: Union[str, bytes, int], size=None) -> bytes:
        return util.to_bytes(msg, size)

    def set_trace(self, trace: bool):
        self.emulator().trace = trace

    def set_mem_trace(self, trace: bool):
        self.emulator().mem_trace = trace

    def set_trace_regs(self, trace: bool):
        self.emulator().trace_regs = trace

    @abstractmethod
    def encrypt(self, message: Union[str, bytes], associated_data: Union[str, bytes], key: Union[str, bytes, int],
                nonce: Union[str, bytes, int]) -> (int, bytes, [], []):
        pass

    @abstractmethod
    def emulator(self) -> rainbowBase:
        pass
