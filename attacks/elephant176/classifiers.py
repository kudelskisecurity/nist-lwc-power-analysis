import numba
import numpy as np
from numba import njit
from lascar import hamming

# Constants
state_bits = 176
state_bytes = state_bits // 8
n_rounds = 90
lfsr_iv: int = 0x45
debug = False

sbox_list = [
    0xee, 0xed, 0xeb, 0xe0, 0xe2, 0xe1, 0xe4, 0xef, 0xe7, 0xea, 0xe8, 0xe5, 0xe9, 0xec, 0xe3, 0xe6,
    0xde, 0xdd, 0xdb, 0xd0, 0xd2, 0xd1, 0xd4, 0xdf, 0xd7, 0xda, 0xd8, 0xd5, 0xd9, 0xdc, 0xd3, 0xd6,
    0xbe, 0xbd, 0xbb, 0xb0, 0xb2, 0xb1, 0xb4, 0xbf, 0xb7, 0xba, 0xb8, 0xb5, 0xb9, 0xbc, 0xb3, 0xb6,
    0x0e, 0x0d, 0x0b, 0x00, 0x02, 0x01, 0x04, 0x0f, 0x07, 0x0a, 0x08, 0x05, 0x09, 0x0c, 0x03, 0x06,
    0x2e, 0x2d, 0x2b, 0x20, 0x22, 0x21, 0x24, 0x2f, 0x27, 0x2a, 0x28, 0x25, 0x29, 0x2c, 0x23, 0x26,
    0x1e, 0x1d, 0x1b, 0x10, 0x12, 0x11, 0x14, 0x1f, 0x17, 0x1a, 0x18, 0x15, 0x19, 0x1c, 0x13, 0x16,
    0x4e, 0x4d, 0x4b, 0x40, 0x42, 0x41, 0x44, 0x4f, 0x47, 0x4a, 0x48, 0x45, 0x49, 0x4c, 0x43, 0x46,
    0xfe, 0xfd, 0xfb, 0xf0, 0xf2, 0xf1, 0xf4, 0xff, 0xf7, 0xfa, 0xf8, 0xf5, 0xf9, 0xfc, 0xf3, 0xf6,
    0x7e, 0x7d, 0x7b, 0x70, 0x72, 0x71, 0x74, 0x7f, 0x77, 0x7a, 0x78, 0x75, 0x79, 0x7c, 0x73, 0x76,
    0xae, 0xad, 0xab, 0xa0, 0xa2, 0xa1, 0xa4, 0xaf, 0xa7, 0xaa, 0xa8, 0xa5, 0xa9, 0xac, 0xa3, 0xa6,
    0x8e, 0x8d, 0x8b, 0x80, 0x82, 0x81, 0x84, 0x8f, 0x87, 0x8a, 0x88, 0x85, 0x89, 0x8c, 0x83, 0x86,
    0x5e, 0x5d, 0x5b, 0x50, 0x52, 0x51, 0x54, 0x5f, 0x57, 0x5a, 0x58, 0x55, 0x59, 0x5c, 0x53, 0x56,
    0x9e, 0x9d, 0x9b, 0x90, 0x92, 0x91, 0x94, 0x9f, 0x97, 0x9a, 0x98, 0x95, 0x99, 0x9c, 0x93, 0x96,
    0xce, 0xcd, 0xcb, 0xc0, 0xc2, 0xc1, 0xc4, 0xcf, 0xc7, 0xca, 0xc8, 0xc5, 0xc9, 0xcc, 0xc3, 0xc6,
    0x3e, 0x3d, 0x3b, 0x30, 0x32, 0x31, 0x34, 0x3f, 0x37, 0x3a, 0x38, 0x35, 0x39, 0x3c, 0x33, 0x36,
    0x6e, 0x6d, 0x6b, 0x60, 0x62, 0x61, 0x64, 0x6f, 0x67, 0x6a, 0x68, 0x65, 0x69, 0x6c, 0x63, 0x66
]
# njit requires numpy arrays to work
sbox_ndarray = np.array(sbox_list)
sbox_inverse = [sbox_list.index(i) for i in range(0xff + 1)]


#
# Spongent permutation and its inverse
#

@njit
def reverse_bits(counter) -> int:
    """
    Reverses the order of the bits in the given counter
    :param counter: a 7bit value
    :return:
    """
    # From Elephant reference code (elephant160v2 > spongent.c > retnuoCl)
    return ((counter & 0x01) << 7) | ((counter & 0x02) << 5) | ((counter & 0x04) << 3) \
           | ((counter & 0x08) << 1) | ((counter & 0x10) >> 1) | ((counter & 0x20) >> 3) \
           | ((counter & 0x40) >> 5) | ((counter & 0x80) >> 7)


def pi(i):
    return i if i == state_bits - 1 else (i * state_bits//4) % (state_bits - 1)


def counter(lfsr):
    """Iterates the counter for the permutation round"""
    lfsr = (lfsr << 1) | (((0x40 & lfsr) >> 6) ^ ((0x20 & lfsr) >> 5))
    lfsr &= 0x7f
    return lfsr



def spongent_inverse(state, rounds=n_rounds):
    def counter_inverse(lfsr):
        previous_zero = (((0x40 & lfsr) >> 6) ^ (lfsr & 1))
        lfsr = (lfsr >> 1) | (previous_zero << 6)
        lfsr &= 0x7f
        return lfsr

    def lfsr_n(c, n):
        for i in range(n):
            c = counter(c)
        return c

    def pLayer_inverse(state):
        tmp = [0 for _ in range(state_bytes)]
        for i in range(state_bytes):
            for j in range(8):
                # where was the bit sent
                target_bitno = pi(8 * i + j)
                # retrieve the bit
                bit = (state[target_bitno // 8] >> target_bitno % 8) & 1
                # set the bit back
                tmp[i] ^= bit << j

        return tmp


    c = lfsr_n(lfsr_iv, rounds)
    for i in range(rounds):
        c = counter_inverse(c)

        # Permutation
        state = pLayer_inverse(state)

        # SBox
        for i in range(state_bytes):
            state[i] = sbox_inverse[state[i]]

        # Add Counter
        state[0] ^= c
        inv_iv = reverse_bits(c)
        state[state_bytes - 1] ^= inv_iv

    return state


def spongent(state: bytes, rounds=None):
    def pLayer(state):
        tmp = [0 for _ in range(state_bytes)]

        for i in range(state_bytes):
            for j in range(8):
                bit = (state[i] >> j) & 1
                target_bitno = pi(8 * i + j)
                tmp[target_bitno // 8] ^= bit << (target_bitno % 8)

        return tmp


    def spongent_round(iv, state):
        # Add Counter
        state[0] ^= iv
        inv_iv = reverse_bits(iv)
        state[state_bytes - 1] ^= inv_iv
        iv = counter(iv)

        # SBox
        for i in range(state_bytes):
            state[i] = sbox_ndarray[state[i]]

        print_debug(" --", state)
        # Permutation
        state = pLayer(state)

        return iv, state


    state = list(state)
    iv = lfsr_iv

    if rounds is None:
        rounds = n_rounds

    for i in range(rounds):
        print_debug(i, state)
        iv, state = spongent_round(iv, state)

    print_debug("end", state)
    return bytes(state)


def print_debug(round, state):
    if debug:
        print(round, ' '.join(['{:02X}'.format(x) for x in state[::-1]]), sep='\t')



@njit
def classifier(state: int, position: int):
    iv = numba.u1(lfsr_iv)
    state = numba.u1(state)

    if position == 0:
        # print(" pos 0 ", state, iv)
        state ^= iv
        # print(" post pos 0 ", state, iv)
    elif position == state_bytes - 1:
        inv = numba.u1(reverse_bits(iv))
        # print("  inv", inv, state)
        state ^= inv

    return sbox_ndarray[state]


@njit
def classifier_ad(position, ad: np.ndarray, guess):
    ad_byte = numba.u1(ad[position])
    state = numba.u1(guess) ^ ad_byte
    result = classifier(state, position)

    return hamming(result)

@njit
def rotl(b):
    return (0xff & (b << 1)) | (b >> 7)

@njit
def rotr(b):
    return (0xff & (b << 7)) | (b >> 1)

def mask_lfsr_step(state):
    out = []
    temp = rotl(state[0]) ^ ((state[3] << 7) & 0xff) ^ (state[19] >> 7)

    for i in range(state_bytes - 1):
        out.append(state[i + 1])

    out.append(temp)

    return bytes(out)


def mask_lfsr_goback(state):
    out = []

    rotTemp = ((state[2] << 7) & 0xff) ^ (state[18] >> 7) ^ state[21]
    temp = rotr(rotTemp) # temp

    out.append(temp)
    for i in range(1, state_bytes):
        out.append(state[i - 1])

    return bytes(out)

