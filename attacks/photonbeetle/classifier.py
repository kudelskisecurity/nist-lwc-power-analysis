import numpy as np
from lascar.tools.leakage_model import _hw as hw

RC = np.array([
    [1, 3, 7, 14, 13, 11, 6, 12, 9, 2, 5, 10],
    [0, 2, 6, 15, 12, 10, 7, 13, 8, 3, 4, 11],
    [2, 0, 4, 13, 14, 8, 5, 15, 10, 1, 6, 9],
    [6, 4, 0, 9, 10, 12, 1, 11, 14, 5, 2, 13],
    [14, 12, 8, 1, 2, 4, 9, 3, 6, 13, 10, 5],
    [15, 13, 9, 0, 3, 5, 8, 2, 7, 12, 11, 4],
    [13, 15, 11, 2, 1, 7, 10, 0, 5, 14, 9, 6],
    [9, 11, 15, 6, 5, 3, 14, 4, 1, 10, 13, 2]
])

MixColMatrix = np.array([
    [2, 4, 2, 11, 2, 8, 5, 6],
    [12, 9, 8, 13, 7, 7, 5, 2],
    [4, 4, 13, 13, 9, 4, 13, 9],
    [1, 6, 5, 1, 12, 13, 15, 14],
    [15, 12, 9, 13, 14, 5, 14, 13],
    [9, 14, 5, 15, 4, 12, 9, 6],
    [12, 2, 2, 10, 3, 1, 1, 14],
    [15, 1, 13, 10, 5, 10, 2, 3]
])

sbox = np.array([12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2])
reverse_sbox = np.array([5, 14, 15, 8, 12, 1, 2, 13, 11, 4, 6, 3, 0, 7, 9, 10])
S = 4
D = 8
ReductionPoly = 0x3
WordFilter = 0xf

field_mult_arr = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    [0, 2, 4, 6, 8, 10, 12, 14, 3, 1, 7, 5, 11, 9, 15, 13],
    [0, 3, 6, 5, 12, 15, 10, 9, 11, 8, 13, 14, 7, 4, 1, 2],
    [0, 4, 8, 12, 3, 7, 11, 15, 6, 2, 14, 10, 5, 1, 13, 9],
    [0, 5, 10, 15, 7, 2, 13, 8, 14, 11, 4, 1, 9, 12, 3, 6],
    [0, 6, 12, 10, 11, 13, 7, 1, 5, 3, 9, 15, 14, 8, 2, 4],
    [0, 7, 14, 9, 15, 8, 1, 6, 13, 10, 3, 4, 2, 5, 12, 11],
    [0, 8, 3, 11, 6, 14, 5, 13, 12, 4, 15, 7, 10, 2, 9, 1],
    [0, 9, 1, 8, 2, 11, 3, 10, 4, 13, 5, 12, 6, 15, 7, 14],
    [0, 10, 7, 13, 14, 4, 9, 3, 15, 5, 8, 2, 1, 11, 6, 12],
    [0, 11, 5, 14, 10, 1, 15, 4, 7, 12, 2, 9, 13, 6, 8, 3],
    [0, 12, 11, 7, 5, 9, 14, 2, 10, 6, 1, 13, 15, 3, 4, 8],
    [0, 13, 9, 4, 1, 12, 8, 5, 2, 15, 11, 6, 3, 14, 10, 7],
    [0, 14, 15, 1, 13, 3, 2, 12, 9, 7, 6, 8, 4, 10, 11, 5],
    [0, 15, 13, 2, 9, 6, 4, 11, 1, 14, 12, 3, 8, 7, 5, 10]]


def field_mult(a, b):
    c = field_mult_arr[a][b]
    # print(a, b, c)
    return c


def compute_round_1(col, nonce, key):
    state = []

    for i in range(4):
        state.append((nonce >> 4 * (3 - i)) & 0xf)
    for i in range(4):
        state.append((key >> 4 * (3 - i)) & 0xf)

    # AddConstants // AddKey
    # We add the constant only to the row s.t. row == col (because of the later shiftrow)
    state[(8 - col) % D] ^= RC[(8 - col) % D][0]

    # SubCell
    for i in range(D):
        state[i] = sbox[state[i]]

    # ShiftRow already done in AddConstants
    # MixColumn
    tmp = [0 for _ in range(D)]

    for i in range(D):
        xor_sum = 0
        for k in range(D):
            xor_sum ^= field_mult(MixColMatrix[i][k], state[k])
        tmp[i] = xor_sum

    for i in range(D):
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
    elems = [4 + 4 * (((rs + x) % D) ^ 1) for x in elems]
    return (elem >> (128 - elems[0]) & 0xf) << 12 | \
           (elem >> ( 96 - elems[1]) & 0xf) << 8 | \
           (elem >> ( 64 - elems[2]) & 0xf) << 4 | \
           (elem >> ( 32 - elems[3]) & 0xf)
