from math import ceil
from .romulus import get_first_tweakey

BLOCK_SIZE = 128
TWEAKEY_SIZE = 384
N_RNDS = 40
DEBUG = True

sbox_8 = [0x65, 0x4c, 0x6a, 0x42, 0x4b, 0x63, 0x43, 0x6b, 0x55, 0x75, 0x5a, 0x7a, 0x53, 0x73, 0x5b, 0x7b, 0x35, 0x8c,
          0x3a, 0x81, 0x89, 0x33, 0x80, 0x3b, 0x95, 0x25, 0x98, 0x2a, 0x90, 0x23, 0x99, 0x2b, 0xe5, 0xcc, 0xe8, 0xc1,
          0xc9, 0xe0, 0xc0, 0xe9, 0xd5, 0xf5, 0xd8, 0xf8, 0xd0, 0xf0, 0xd9, 0xf9, 0xa5, 0x1c, 0xa8, 0x12, 0x1b, 0xa0,
          0x13, 0xa9, 0x05, 0xb5, 0x0a, 0xb8, 0x03, 0xb0, 0x0b, 0xb9, 0x32, 0x88, 0x3c, 0x85, 0x8d, 0x34, 0x84, 0x3d,
          0x91, 0x22, 0x9c, 0x2c, 0x94, 0x24, 0x9d, 0x2d, 0x62, 0x4a, 0x6c, 0x45, 0x4d, 0x64, 0x44, 0x6d, 0x52, 0x72,
          0x5c, 0x7c, 0x54, 0x74, 0x5d, 0x7d, 0xa1, 0x1a, 0xac, 0x15, 0x1d, 0xa4, 0x14, 0xad, 0x02, 0xb1, 0x0c, 0xbc,
          0x04, 0xb4, 0x0d, 0xbd, 0xe1, 0xc8, 0xec, 0xc5, 0xcd, 0xe4, 0xc4, 0xed, 0xd1, 0xf1, 0xdc, 0xfc, 0xd4, 0xf4,
          0xdd, 0xfd, 0x36, 0x8e, 0x38, 0x82, 0x8b, 0x30, 0x83, 0x39, 0x96, 0x26, 0x9a, 0x28, 0x93, 0x20, 0x9b, 0x29,
          0x66, 0x4e, 0x68, 0x41, 0x49, 0x60, 0x40, 0x69, 0x56, 0x76, 0x58, 0x78, 0x50, 0x70, 0x59, 0x79, 0xa6, 0x1e,
          0xaa, 0x11, 0x19, 0xa3, 0x10, 0xab, 0x06, 0xb6, 0x08, 0xba, 0x00, 0xb3, 0x09, 0xbb, 0xe6, 0xce, 0xea, 0xc2,
          0xcb, 0xe3, 0xc3, 0xeb, 0xd6, 0xf6, 0xda, 0xfa, 0xd3, 0xf3, 0xdb, 0xfb, 0x31, 0x8a, 0x3e, 0x86, 0x8f, 0x37,
          0x87, 0x3f, 0x92, 0x21, 0x9e, 0x2e, 0x97, 0x27, 0x9f, 0x2f, 0x61, 0x48, 0x6e, 0x46, 0x4f, 0x67, 0x47, 0x6f,
          0x51, 0x71, 0x5e, 0x7e, 0x57, 0x77, 0x5f, 0x7f, 0xa2, 0x18, 0xae, 0x16, 0x1f, 0xa7, 0x17, 0xaf, 0x01, 0xb2,
          0x0e, 0xbe, 0x07, 0xb7, 0x0f, 0xbf, 0xe2, 0xca, 0xee, 0xc6, 0xcf, 0xe7, 0xc7, 0xef, 0xd2, 0xf2, 0xde, 0xfe,
          0xd7, 0xf7, 0xdf, 0xff]
sbox_inverse = [sbox_8.index(i) for i in range(256)]

P = [0, 1, 2, 3, 7, 4, 5, 6, 10, 11, 8, 9, 13, 14, 15, 12]
TWEAKEY_P = [9, 15, 8, 13, 10, 14, 12, 11, 0, 1, 2, 3, 4, 5, 6, 7]
RC = [
    0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3E, 0x3D, 0x3B, 0x37, 0x2F,
    0x1E, 0x3C, 0x39, 0x33, 0x27, 0x0E, 0x1D, 0x3A, 0x35, 0x2B,
    0x16, 0x2C, 0x18, 0x30, 0x21, 0x02, 0x05, 0x0B, 0x17, 0x2E,
    0x1C, 0x38, 0x31, 0x23, 0x06, 0x0D, 0x1B, 0x36, 0x2D, 0x1A]


def add_key(state, keyCells):
    for i in range(0, 2):
        for j in range(0, 4):
            state[i][j] ^= keyCells[0][i][j] ^ keyCells[1][i][j] ^ keyCells[2][i][j]

    key_cells_temp = []
    # update subtweakey states
    for k in range(ceil(TWEAKEY_SIZE / BLOCK_SIZE)):
        key_cells_temp.append([])
        for i in range(4):
            key_cells_temp[k].append([])
            for j in range(4):
                pos = TWEAKEY_P[j + 4 * i]
                content = keyCells[k][pos >> 2][pos & 0x3]
                key_cells_temp[k][i].append(content)
    print("S = " + tohex(state) + " - TK1 = " + tohex(key_cells_temp[0]) + " - TK2 = " + tohex(key_cells_temp[1]) + " - TK3 = " + tohex(key_cells_temp[2]))

    # lfsr and final update
    for k in range(1, ceil(TWEAKEY_SIZE / BLOCK_SIZE)):
        for i in range(2):
            for j in range(4):
                if k == 1:
                    key_cells_temp[k][i][j] = \
                        ((key_cells_temp[k][i][j] << 1) & 0xFE) ^ \
                        ((key_cells_temp[k][i][j] >> 7) & 0x01) ^ \
                        ((key_cells_temp[k][i][j] >> 5) & 0x01)
                elif k == 2:
                    key_cells_temp[k][i][j] = \
                        ((key_cells_temp[k][i][j] >> 1) & 0x7F) ^ \
                        ((key_cells_temp[k][i][j] << 7) & 0x80) ^ \
                        ((key_cells_temp[k][i][j] << 1) & 0x80)

    for k in range(0, ceil(TWEAKEY_SIZE / BLOCK_SIZE)):
        for i in range(4):
            for j in range(4):
                keyCells[k][i][j] = key_cells_temp[k][i][j]


def add_constants(state, round):
    state[0][0] ^= (RC[round] & 0xf)
    state[1][0] ^= ((RC[round] >> 4) & 0x3)
    state[2][0] ^= 0x2


def sbox(state):
    for i in range(4):
        for j in range(4):
            state[i][j] = sbox_8[state[i][j]]


def shift_rows(state):
    tmp = state[1][3]
    state[1][3] = state[1][2]
    state[1][2] = state[1][1]
    state[1][1] = state[1][0]
    state[1][0] = tmp

    state[2][0], state[2][2] = state[2][2], state[2][0]
    state[2][1], state[2][3] = state[2][3], state[2][1]

    tmp = state[3][0]
    state[3][0] = state[3][1]
    state[3][1] = state[3][2]
    state[3][2] = state[3][3]
    state[3][3] = tmp


def mix_column(state):
    for j in range(4):
        state[1][j] ^= state[2][j]
        state[2][j] ^= state[0][j]
        state[3][j] ^= state[2][j]

        temp = state[3][j]
        state[3][j] = state[2][j]
        state[2][j] = state[1][j]
        state[1][j] = state[0][j]
        state[0][j] = temp

def tohex(arr):
    return b''.join([bytes(b) for b in arr]).hex()

def print_state(state, key):
    print("S = " + tohex(state) + " - TK1 = " + tohex(key[0]) + " - TK2 = " + tohex(key[1]) + " - TK3 = " + tohex(key[2]))

def round(state, key, round):
    sbox(state)

    if DEBUG:
        print('ENC - round {0:02d} - after SubCell:      '.format(round), end='')
        print_state(state, key)

    add_constants(state, round)

    if DEBUG:
        print('ENC - round {0:02d} - after AddConstants: '.format(round), end='')
        print_state(state, key)

    add_key(state, key)

    if DEBUG:
        print('ENC - round {0:02d} - after AddKey:       '.format(round), end='')
        print_state(state, key)

    shift_rows(state)

    if DEBUG:
        print('ENC - round {0:02d} - after ShiftRows:    '.format(round), end='')
        print_state(state, key)

    mix_column(state)

    if DEBUG:
        print('ENC - round {0:02d} - after MixColumn:    '.format(round), end='')
        print_state(state, key)


def prepare(block: bytes, tweakey: bytes):
    state = []
    key = [[], [], []]

    for i in range(4):
        state.append([])
        for k in range(3): key[k].append([])

        for j in range(4):
            state[i].append(block[i * 4 + j] & 0xFF)

            for k in range(3):
                key[k][i].append(tweakey[k * 16 + i * 4 + j] & 0xFF)

    return state, key

def enc(block, tweakey, rounds):
    state, key = prepare(block, tweakey)
    for i in range(rounds):
        round(state, key, i)
    return state, key

# this reverses the add_constants and s_box operation for a given plaintext
def revert_two_first_steps(state, round):
    add_constants(state, round) # add == sub here, since we use xor
    for i in range(4):
        for j in range(4):
            state[i][j] = sbox_inverse[state[i][j]]


# this reverses the addkeys step but only for the two first key tables (constants + nonce), leaving only the key in step 1
def revert_addkeys_known(state, keyCells):
    for i in range(0, 2):
        for j in range(0, 4):
            state[i][j] ^= keyCells[0][i][j] ^ keyCells[1][i][j]

"""
    Returns a plaintext that, when used in the algorithm, causes the state to be 0 before xoring the nonce
    
    ACTUALLY this is stupid because I don't have any control over which plaintext is passed to the algo
    (actually, it is 0...)
"""
def source_plaintext():
    key = get_first_tweakey(b'\x00' * 16, b'\x00' * 16)
    s, k = prepare(b'\x00' * 16, key)
    print("desired", s)
    for i in range(0, 2):
        for j in range(0, 4):
            s[i][j] ^= k[0][i][j]
    revert_two_first_steps(s, 0)
    print("initial", s)

    return b''.join([bytes(st) for st in s])


def skkinny_test():
    key = 0xdf889548cfc7ea52d296339301797449ab588a34a47f1ab2dfe9c8293fbea9a5ab1afac2611012cd8cef952618c3ebe8
    plaintext = 0xa3994b66ad85a3459f44e92b08f550cb
    ct = 0xff38d1d24c864c4352a853690fe36e5e

    ct2, _ = enc(plaintext.to_bytes(16, 'big'), key.to_bytes(48, 'big'), 40)

    print(hex(ct))
    print('0x' + b''.join([bytes(c) for c in ct2]).hex())



def test_stuff():
    key = get_first_tweakey(0x53e8d037e939f2bf9f9c74cb3139ce5d.to_bytes(16, 'big'), bytes(range(16)))
    # key = b'\x00' * 32 + bytes(range(16))
    s, k = prepare(b'\x00' * 16, key)
    print("initial          ", end='')
    print_state(s, k)
    # sbox(s)
    # print("done sbox.", s)
    # add_constants(s, 0)
    # print("added cons", s)
    sbox(s)
    print("done sbox1       ", end='')
    print_state(s, k)
    add_constants(s, 0)
    print("added cons       ", end='')
    print_state(s, k)
    add_key(s, k)
    print("added keys       ", end='')
    print_state(s, k)
    shift_rows(s)
    print("shifted ro       ", end='')
    print_state(s, k)
    mix_column(s)
    print("mixed colu       ", end='')
    print_state(s, k)

    sbox(s)
    print("done sbox2       ", end='')
    print_state(s, k)
    add_constants(s, 1)
    print("added cons       ", end='')
    print_state(s, k)
    add_key(s, k)
    print("added keys       ", end='')
    print_state(s, k)
    shift_rows(s)
    print("shifted ro       ", end='')
    print_state(s, k)
    mix_column(s)
    print("mixed colu       ", end='')
    print_state(s, k)

    sbox(s)
    print("done sbox3       ", end='')
    print_state(s, k)

# test_stuff()

# nonce = bytes(range(16))
# pt = source_plaintext()
# key = get_first_tweakey(nonce, bytes(range(16, 32)))
# s, k = prepare(pt, key)
# print(k)
# sbox(s)
# print("done sbox1", s)
# add_constants(s, 0)
# print("added cons", s)
# add_key(s, k)
# print("added key", s)