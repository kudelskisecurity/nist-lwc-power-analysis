from lascar.tools.leakage_model import hamming
from numba import njit
from .constants import *


def init_lfsr() -> []:
    """Return a new instance of the counter LFSR"""
    return [1, 0, 0, 0, 0, 0, 0]


def lfsr(cnt: []):
    """Increment the provided counter LFSR"""
    fb0 = cnt[6] >> 7

    cnt[6] = (cnt[6] << 1) | (cnt[5] >> 7)
    cnt[5] = (cnt[5] << 1) | (cnt[4] >> 7)
    cnt[4] = (cnt[4] << 1) | (cnt[3] >> 7)
    cnt[3] = (cnt[3] << 1) | (cnt[2] >> 7)
    cnt[2] = (cnt[2] << 1) | (cnt[1] >> 7)
    cnt[1] = (cnt[1] << 1) | (cnt[0] >> 7)
    if fb0 == 1:
        cnt[0] = (cnt[0] << 1) ^ 0x95
    else:
        cnt[0] = (cnt[0] << 1)


def xor(a, b):
    """Computes the exclusive or between two blocks of 16 bytes"""
    s = []
    for i in range(0, 16):
        s.append(a[i] ^ b[i])
    return s


def compute_initial_state(ad0, ad1):
    """Computes the initial state just before adding tweakeys in the first round"""
    cnt = init_lfsr()
    lfsr(cnt)

    ad = xor(ad0, ad1)
    initial = [sbox_8[a] for a in ad]
    initial[0] ^= (RC[0] & 0xf) ^ cnt[0]
    initial[7] ^= 0x1a  # value of the 8th byte of the first Tweakey table
    initial[8] ^= 0x2   # addconstant

    return np.array(initial)



@njit
def round_1_model(pair, guess, index) -> int:
    """Classifies by the output of round 1's sbox"""
    nonce, initial = pair
    # print(nonce)
    round0 = initial[index] ^ guess ^ nonce[index]
    if index >= 4:
        # second row is affected by round0's mixColumn before going to round1
        round0 ^= initial[(index - 1) % 4 + 8]

    return hamming(sbox[round0])


@njit
def round_2_model(pair, guess, index, key_four) -> int:
    """
        Classifies by the output of round 2's SBox.

        This requires knowing the first half of the key.
    """
    nonce, initial = pair
    # the first row in round 2 is xor (row0, row2, row3)
    # the second row happens to be exactly row0 :D
    # compute the value of row0 at the end of round_1
    round_0_index = index % 4
    round_0_result = initial[round_0_index] ^ key_four[round_0_index] ^ nonce[round_0_index]

    if index == 2:
        # MixColumns: row0 is xored wit row2 and row3
        # But row2 xor row3 = 0x00.00.02.00
        # This is because these rows are not touched by the key and are almost only 0
        # The only different byte is 0x2, initially in position 0 and shifted in position 2 by ShiftRows
        # So only index 2 is affected by the MixColumns in round 1
        round_0_result ^= 0x2

    # at the beginning of round 2, we pass everything into a sbox
    round_1_begin = sbox[round_0_result]

    # we then add the round constant (only touches first column)
    if index == 0:
        round_1_begin ^= (RC[1] & 0xf)

    # we now add the tweakkey
    # the key bytes have been "shuffled" in the previous addkey, so we need to find where was the key byte in
    # the previous round
    position_in_previous_round = NP_TWEAKEY_P[index]  # where was the key-byte we're looking for previously?
    nonce_byte = nonce[position_in_previous_round]

    nonce_byte = \
        ((nonce_byte << 1) & 0xFE) ^ \
        ((nonce_byte >> 7) & 0x01) ^ \
        ((nonce_byte >> 5) & 0x01)
    guess = \
        ((guess >> 1) & 0x7F) ^ \
        ((guess << 7) & 0x80) ^ \
        ((guess << 1) & 0x80)

    # at this round, first row of TK1 is entirely 0, so we can skip it
    add_key = round_1_begin ^ nonce_byte
    add_key ^= guess

    if index >= 4:
        # row1 is affected by mixcolumns before going to round2's sbox
        # it is xored with row2
        # at the begining of round1, row2 = sbox(row1 >> 1 xor row2 >> 2)
        # reminder: rows start at 0 (row_1 is the second row in human language)
        index -= 1
        round_0_row_1_index = (index - 1) % 4 + 4  # row1 is shifted by 1
        round_0_row_2_index = (index - 2) % 4 + 8  # row2 is shifted by 2
        round_0_row_1 = initial[round_0_row_1_index] ^ key_four[round_0_row_1_index] ^ nonce[round_0_row_1_index]
        round_0_row_2 = initial[round_0_row_2_index]
        round_0_row_2 ^= round_0_row_1
        round_1_row_2 = sbox[round_0_row_2]

        # There is NO AddConstants in this step and there should NOT be.
        # AddConstants and Add TK1 are cancelling each other in row[2][0]
        # This is because TK1 is all-zero except in TK1[2][0] (where it is 0x2) and TK1[3][3] (which we don't use)
        # AddConstants adds 0x2 to row[2][0], so it cancels out

        add_key ^= round_1_row_2

    res = sbox[add_key]
    return hamming(res)
