import numpy as np
from numba import njit

GIFT_SBOX = [0x1, 0xa, 0x4, 0xc, 0x6, 0xf, 0x3, 0x9, 0x2, 0xd, 0xb, 0x7, 0x5, 0x0, 0x8, 0xe]

GIFT_RC = np.array([
    0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3E, 0x3D, 0x3B, 0x37, 0x2F,
    0x1E, 0x3C, 0x39, 0x33, 0x27, 0x0E, 0x1D, 0x3A, 0x35, 0x2B,
    0x16, 0x2C, 0x18, 0x30, 0x21, 0x02, 0x05, 0x0B, 0x17, 0x2E,
    0x1C, 0x38, 0x31, 0x23, 0x06, 0x0D, 0x1B, 0x36, 0x2D, 0x1A
])


@njit
def rowperm(S: int, x0: int, x1: int, x2: int, x3: int) -> int:
    T = 0
    for b in range(0, 8):
        T |= ((S >> (4 * b + 0)) & 0x1) << (b + 8 * x0)
        T |= ((S >> (4 * b + 1)) & 0x1) << (b + 8 * x1)
        T |= ((S >> (4 * b + 2)) & 0x1) << (b + 8 * x2)
        T |= ((S >> (4 * b + 3)) & 0x1) << (b + 8 * x3)
    return T


@njit
def permbits(state: np.array) -> np.array:
    state[0] = rowperm(state[0], 0, 3, 2, 1)
    state[1] = rowperm(state[1], 1, 0, 3, 2)
    state[2] = rowperm(state[2], 2, 1, 0, 3)
    state[3] = rowperm(state[3], 3, 2, 1, 0)

    return state


def rowperm_inverse(S: int, x0: int, x1: int, x2: int, x3: int) -> int:
    T = 0
    for b in range(0, 8):
        T |= ((S >> (b + 8 * x0)) & 0x1) << (4 * b + 0)
        T |= ((S >> (b + 8 * x1)) & 0x1) << (4 * b + 1)
        T |= ((S >> (b + 8 * x2)) & 0x1) << (4 * b + 2)
        T |= ((S >> (b + 8 * x3)) & 0x1) << (4 * b + 3)
    return T


def permbits_inverse(state: np.array) -> np.array:
    state[0] = rowperm_inverse(state[0], 0, 3, 2, 1)
    state[1] = rowperm_inverse(state[1], 1, 0, 3, 2)
    state[2] = rowperm_inverse(state[2], 2, 1, 0, 3)
    state[3] = rowperm_inverse(state[3], 3, 2, 1, 0)

    return state


def sbox_bitslice(state):
    # state is a 4 * 32bits array
    state[1] ^= state[0] & state[2]
    state[0] ^= state[1] & state[3]
    state[2] ^= state[0] | state[1]
    state[3] ^= state[2]
    state[1] ^= state[3]
    state[3] ^= 0xffffffff
    state[2] ^= state[0] & state[1]
    state[0], state[3] = state[3], state[0]
    return state


def sbox_bitslice_inverse(state: np.array) -> np.array:
    # state is a 4 * 32bits array
    state[3], state[0] = state[0], state[3]
    state[2] ^= (state[0] & state[1])
    state[3] ^= 0xffffffff
    state[1] ^= state[3]
    state[3] ^= state[2]
    state[2] ^= state[0] | state[1]
    state[0] ^= state[1] & state[3]
    state[1] ^= state[0] & state[2]
    return state


def make_state(bt: bytes):
    state = np.zeros(4, np.uint32)
    state[0] = (bt[0] << 24) | (bt[1] << 16) | (bt[2] << 8) | bt[3]
    state[1] = (bt[4] << 24) | (bt[5] << 16) | (bt[6] << 8) | bt[7]
    state[2] = (bt[8] << 24) | (bt[9] << 16) | (bt[10] << 8) | bt[11]
    state[3] = (bt[12] << 24) | (bt[13] << 16) | (bt[14] << 8) | bt[15]
    return state


def unmake_state(state: np.array) -> bytes:
    bt = bytes()

    bt += bytes([(state[0] >> 24), (state[0] >> 16) & 0xff, (state[0] >> 8) & 0xff, (state[0]) & 0xff])
    bt += bytes([(state[1] >> 24), (state[1] >> 16) & 0xff, (state[1] >> 8) & 0xff, (state[1]) & 0xff])
    bt += bytes([(state[2] >> 24), (state[2] >> 16) & 0xff, (state[2] >> 8) & 0xff, (state[2]) & 0xff])
    bt += bytes([(state[3] >> 24), (state[3] >> 16) & 0xff, (state[3] >> 8) & 0xff, (state[3]) & 0xff])

    return bt


def nibble_from_state(state: np.array, bit: int):
    return ((state[3] >> bit & 0x1) << 3 | (state[2] >> bit & 0x1) << 2 | (state[1] >> bit & 0x1) << 1 |
            (state[0] >> bit & 0x1))


def sbox_differentials(key_bits):
    differentials = []
    for orig in range(16):
        tbl = []
        for in_diff in range(1, 16):
            tbl_diff = {}
            for key in range(2 ** key_bits):
                key = key << (4 - key_bits)
                orig_sbox = GIFT_SBOX[orig ^ key]
                new_sbox = GIFT_SBOX[orig ^ in_diff ^ key]
                diff = orig_sbox ^ new_sbox

                if diff not in tbl_diff:
                    tbl_diff[diff] = []

                tbl_diff[diff].append(key >> (4 - key_bits))
            tbl.append(tbl_diff)
        differentials.append(tbl)
    return differentials


def partial_rounds(state_bytes, rounds, key=None):
    """
    Given the state at round 0, compute the state at round [[rounds]] before the AddKey step
    :param state_bytes: the state at round 0
    :param rounds: the rounds to compute
    :param key:
    :return:
    """

    if rounds not in [1, 2]: raise ValueError("rounds should be 1 or 2")

    if rounds == 2 and key is None: raise ValueError("key needed for 2nd round")

    state = make_state(state_bytes)

    # round 1
    sbox_bitslice(state)
    permbits(state)

    if rounds == 2:
        state[2] ^= key[0]
        state[1] ^= key[1]
        state[3] ^= 0x80000000 ^ GIFT_RC[0]

        # round 2
        sbox_bitslice(state)
        permbits(state)

    return unmake_state(state), state


def partial_rounds_inverse(state_bytes, rounds, key=None):
    """
    Given the state at round [[rounds]], returns the nonce that generated that state.
    If you want to go back more than one round, you need to provide the key part as a tuple
    :param state_bytes: the state at round [[rounds]] before that round AddKey step
    :param rounds: the current round (either 1 or 2)
    :param key:
    :return:
    """

    if rounds not in [1, 2]: raise ValueError("rounds should be 1 or 2")

    if rounds == 2 and key is None: raise ValueError("key needed for 2nd round")

    state = make_state(state_bytes)

    # round 2
    if rounds == 2:
        permbits_inverse(state)
        sbox_bitslice_inverse(state)

        # round 1
        state[2] ^= key[0]
        state[1] ^= key[1]
        state[3] ^= 0x80000000 ^ GIFT_RC[0]

    # round 1
    permbits_inverse(state)
    sbox_bitslice_inverse(state)

    return unmake_state(state)

# This code comes from the C implementation of GIFT-COFB submitted to NIST.
# It is only useful for comparisons when the correct key is known

@njit
def add_round_key(round: int, state: np.array, key_schedule: np.array) -> (np.array, np.array):
    state[2] ^= (key_schedule[2] << 16) | key_schedule[3]
    state[1] ^= (key_schedule[6] << 16) | key_schedule[7]
    state[3] ^= 0x80000000 ^ GIFT_RC[round]

    # update key schedule
    t6 = (key_schedule[6] >> 2) | (key_schedule[6] << 14)
    t7 = (key_schedule[7] >> 12) | (key_schedule[7] << 4)
    key_schedule[7] = key_schedule[5]
    key_schedule[6] = key_schedule[4]
    key_schedule[5] = key_schedule[3]
    key_schedule[4] = key_schedule[2]
    key_schedule[3] = key_schedule[1]
    key_schedule[2] = key_schedule[0]
    key_schedule[1] = t7
    key_schedule[0] = t6

    return state, key_schedule

@njit
def simulate_round(round: int, state: np.array, key_schedule: np.array) -> (np.array, np.array):
    state = sbox(state)
    state = permbits(state)
    state, key_schedule = add_round_key(round, state, key_schedule)
    return state, key_schedule

@njit
def sbox(state: np.array) -> np.array:
    # state is a 4 * 32bits array
    state[1] ^= state[0] & state[2]
    state[0] ^= state[1] & state[3]
    state[2] ^= state[0] | state[1]
    state[3] ^= state[2]
    state[1] ^= state[3]
    state[3] ^= 0xffffffff
    state[2] ^= state[0] & state[1]
    state[0], state[3] = state[3], state[0]

    return state