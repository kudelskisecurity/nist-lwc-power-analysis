from typing import Union

from rainbow import rainbowBase

from runners.emu_wrappers.emulatorwrapper import EmulatorWrapper
from rainbow.generics.x64 import rainbow_x64


class x64(EmulatorWrapper):
    def __init__(self, alg, key_length: int, nonce_length: int, nsec_length: int = 0, sca: bool = False):
        super().__init__(alg, key_length, nonce_length, nsec_length, sca)
        self.emu = rainbow_x64(sca_mode=sca)
        self.emu.load("bin/" + alg + ".elf")
        self.emu.trace = False
        self.emu.mem_trace = False
        self.emu.trace_regs = False

    def encrypt(self, _message: Union[str, bytes], _associated_data: Union[str, bytes], _key: Union[str, bytes, int],
                _nonce: Union[str, bytes, int], cnt: int = 0) -> (int, bytes, [], []):
        e = self.emu
        e.reset()

        # Parse args
        message = self.to_bytes(_message)
        associated_data = self.to_bytes(_associated_data)
        key = self.to_bytes(_key, self.key_length)
        nonce = self.to_bytes(_nonce, self.nonce_length)

        # Set addresses
        message_addr = 0xE0002000
        ad_addr = 0xE0003000
        ct_addr = 0xE0004000
        ct_len_addr = 0xE0005000
        nsec_addr = 0xEA001000
        nonce_addr = nsec_addr + 0x10
        key_addr = nonce_addr + 0x10

        e[message_addr] = message
        e[ad_addr] = associated_data
        e[ct_addr] = b"\x00" * 0x1000
        e[ct_len_addr] = b"\x00" * 16
        e[nsec_addr] = b'\x00' * 16
        e[nonce_addr] = nonce
        e[key_addr] = key

        stack_address = e.STACK_ADDR

        e["rdi"] = ct_addr
        e["rsi"] = ct_len_addr
        e["rdx"] = message_addr
        e["rcx"] = len(message)
        e["r8"] = ad_addr
        e["r9"] = len(associated_data)

        e[stack_address + 0x08] = nsec_addr.to_bytes(8, 'little')
        e[stack_address + 0x10] = nonce_addr.to_bytes(8, 'little')
        e[stack_address + 0x18] = key_addr.to_bytes(8, 'little')

        e.start(e.functions['crypto_aead_encrypt'], 0, count=cnt)

        ct_len = int.from_bytes(e[ct_len_addr:ct_len_addr + 8], 'little')

        # print()
        # print("key:", e[key_addr:key_addr+key_length].hex())
        # print("nonce:", e[nonce_addr:nonce_addr+nonce_length].hex())
        # print("ct_area:", e[ct_addr:ct_addr + 16])
        # print("ct_len_area:", e[ct_len_addr:ct_len_addr + 16])
        # print("ct_len:", ct_len)

        ct = e[ct_addr:ct_addr+ct_len]

        return ct_len, ct, e.sca_address_trace, e.sca_values_trace


    def emulator(self) -> rainbowBase:
        return self.emu

