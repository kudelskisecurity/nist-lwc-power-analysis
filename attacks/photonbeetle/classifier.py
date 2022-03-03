from lascar.tools.leakage_model import _hw as hw
from .constants import *


def field_mult(a, b):
    c = field_mult_arr[a][b]
    return c


def compute_round_1(col, nonce, key):
    state = []

    for i in range(4):
        state.append((nonce >> 4 * (3 - i)) & 0xf)
    for i in range(4):
        state.append((key >> 4 * (3 - i)) & 0xf)

    # AddConstants // AddKey
    # We add the constant only to the row s.t. row == col (because of the later shiftrow)
    state[(8 - col) % StateSize] ^= RC[(8 - col) % StateSize][0]

    # SubCell
    for i in range(StateSize):
        state[i] = sbox[state[i]]

    # ShiftRow already done in AddConstants
    # MixColumn
    tmp = [0 for _ in range(StateSize)]

    for i in range(StateSize):
        xor_sum = 0
        for k in range(StateSize):
            xor_sum ^= field_mult(MixColMatrix[i][k], state[k])
        tmp[i] = xor_sum

    for i in range(StateSize):
        state[i] = tmp[i]

    return hw[state]



def reverse_round(key):
    """Reverses the first operations of the round (before mixcolumn)"""
    state = [(key[i // 2] >> (4 * (i % 2))) & 0xf for i in range(32)]

    # reverse shiftrows
    old_state = state.copy()
    for i in range(4):
        for j in range(8):
            # state[8 * i + j] = old_state[8 * i + (j + 4 + i) % 8]
            state[8 * i + ((j + 4 + i) % 8)] = old_state[8 * i + j]

    final_state = [state[2 * i] << 4 | state[2 * i + 1] for i in range(16)]

    return bytes(final_state)


def reorder(elems: list[int]):
    def get_pos(row, col):
        return ((elems[col] >> (3 - (row % 4)) * 4) & 0xf).item()

    key_int = 0
    for row in range(4):
        for col in range(8):
            nib = get_pos(row, col)
            # state[r][c] = old_state[r][(r + c) % 8] r,c in 0..7
            target_pos = (row * 8) + ((row + 4 + col) % 8) ^1
            nib = nib << (32 - target_pos - 1) * 4
            key_int = key_int | nib

    return key_int.to_bytes(16, 'big')


def select_column(elem: int, col: int, nonce: bool):
    """
    Selects 4 nibbles after shiftrow
    :param elem:
    :param col:
    :param nonce:
    :return:
    """
    rs = 0 if nonce else 4
    elems = [col, col + 1, col + 2, col + 3] # nibble positions in the element (0-31)
    elems = [4 + 4 * (((rs + x) % StateSize) ^ 1) for x in elems]
    return (elem >> (128 - elems[0]) & 0xf) << 12 | \
           (elem >> ( 96 - elems[1]) & 0xf) << 8 | \
           (elem >> ( 64 - elems[2]) & 0xf) << 4 | \
           (elem >> ( 32 - elems[3]) & 0xf)
