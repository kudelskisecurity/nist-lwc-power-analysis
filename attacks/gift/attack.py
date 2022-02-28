import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

from attacks.gift.classifier import *
from attacks.gift.common import *
from runners.cw_basic import WrappedChipWhisperer
from runners.native import NativeRunner
import random
import chipwhisperer as cw
import time
from util import constants
import pywt

from util import to_bytes

DIFFERENTIALS = sbox_differentials(3)

def _recover_nibble(nibble, initial_nonce, capture_lambda, verbosity, round, guessed_roundkey=None, known_bit=None, real_key_schedule=None):
    if round not in [1, 2]:
        raise ValueError("round should be 1 or 2")

    if round == 2 and guessed_roundkey is None:
        raise ValueError("key needed for 2nd round")

    key_space = 8

    print("Looking for nibble", nibble)
    key_chances = {i: 3 for i in range(key_space)}

    sbox_unbitsliced, sbox_bitsliced = partial_rounds(initial_nonce, round, guessed_roundkey)
    sbox_bitsliced_nibble = nibble_from_state(sbox_bitsliced, nibble)

    diffs_list = list(range(1, 16)) * 3
    random.shuffle(diffs_list)

    def capture_fn(n, r):
        while True:
            try:
                return capture_lambda(n, r)
            except IOError:
                print(f"[!!] IOError encountered, retrying in ten seconds")
                time.sleep(10)

    # previous_nonce = initial_nonce
    # previous_trace = capture(initial_nonce)

    # idea: don't retry wrong keys immediately
    # instead, try to finish the loop with the current remaining keys
    # if it fails, reshuffle all the keys and do it again
    # (max 3 times)
    # retrying immediately on a failure is probably useless, some nonces tend to give bigger fail rates than others?
    total_nb_attempts = 0
    while len(key_chances) > 1 and len(diffs_list) > 1:
        diff = diffs_list.pop()
        total_nb_attempts += 1

        # Compute the required state before mixcolumns and the associated nonce
        target_state = change_bits_in_bytes(sbox_unbitsliced, diff, nibble)
        new_nonce = partial_rounds_inverse(target_state, round, guessed_roundkey)

        # Capture the difference traces between the original nonce and the new one
        diffs_intermediate = [] 
        for i in range(10): 
            orig = capture_fn(initial_nonce, round)
            changed = capture_fn(new_nonce, round)
            diffs_intermediate.append(orig - changed)

        # Average them to get a single absolute differences table
        diffs_intermediate = np.mean(diffs_intermediate, axis=0)
        diffs_intermediate = np.abs(diffs_intermediate)[0]

        if verbosity >= 2:
            # Compute debug information
            _, new_sbox_bitsliced = partial_rounds(new_nonce, round, guessed_roundkey)
            new_nibble = nibble_from_state(new_sbox_bitsliced, nibble)


            print("\tinitial nonce:", initial_nonce.hex())
            print("\tnew nonce    :", new_nonce.hex())
            print("\tnibble=", sbox_bitsliced_nibble, "diff=", diff, "differentials:", DIFFERENTIALS[sbox_bitsliced_nibble][diff - 1])
            print("\ttargetted diff:", bin(diff), "actual diff:", bin(sbox_bitsliced_nibble ^ new_nibble))
            print("\tsbbs2 nibble:", bin(new_nibble), "expected:", bin(sbox_bitsliced_nibble ^ diff))

            for i in range(4):
                print("\tstate", i, sbox_bitsliced[i].tobytes().hex(), new_sbox_bitsliced[i].tobytes().hex(), hex(sbox_bitsliced[i] ^ new_sbox_bitsliced[i]))

        if real_key_schedule is not None:
            real_diff = determine_diff_with_key(initial_nonce, new_nonce, real_key_schedule, round)
        else: real_diff = None


        out_diff = determine_diff(diffs_intermediate, round)
        diffs = DIFFERENTIALS[sbox_bitsliced_nibble][diff - 1]


        if real_diff is not None and real_diff != out_diff:
            if verbosity >= 1: print("Whisperer got wrong diff. Expected", real_diff, "; got", out_diff)

        if out_diff in diffs:
            possible_keys = diffs[out_diff]
        else:
            if verbosity >= 1: print("\tweird... no possible keys")
            continue

        if known_bit is not None:
            # we know the value of the 3rd bit, check it
            first_bits = [known_bit == (nib & 0x4) >> 2 for nib in possible_keys]

            if first_bits.count(True) == 0:
                if verbosity >= 1: print("\tweird... known bit", known_bit, "is not in possible keys", possible_keys)
                continue

        if verbosity >= 1: print("\tin diff:", diff, "out diff:", out_diff, "-- possible keys", possible_keys)
        for i in range(key_space):
            if i not in possible_keys:
                if i in key_chances:
                    if key_chances[i] == 0:
                        key_chances.pop(i)
                    else:
                        key_chances[i] -= 1

        if verbosity >= 1: print("\tkey chances:", key_chances)

    if len(key_chances) == 1:
        if verbosity >= 1: print("\tfound key:", key_chances)
        return list(key_chances.keys())[0], total_nb_attempts
    else:
        if verbosity >= 1: print("\tNo key :(")
        return None, total_nb_attempts


def attack(verbosity: int, num_cap: int = 1, wrap = None):
    print("[1] Connecting to target platform")

    if wrap is None:
        wrap = WrappedChipWhisperer(
            alg='giftcofb128v1',
            platform='CWLITEARM',
            target_type=cw.targets.SimpleSerial,
            prog=cw.programmers.STM32FProgrammer)

    print("[2] Generating a random key to attack")
    key = random.randbytes(16)
    print("\tThe key is", key.hex())
    capture_fn = lambda nonce, round: wrap.capture_traces(key, num_cap, cap_num_windows=1, cap_first_offset=93250 if round == 1 else 160100, nonce_gen=lambda: nonce, silent=verbosity < 2)\
        .leakages

    # Build the key schedule (for debug)
    key_schedule = np.zeros(8, np.uint32)
    key_schedule[0] = (key[0] << 8) |  key[1]
    key_schedule[1] = (key[2] << 8) |  key[3]
    key_schedule[2] = (key[4] << 8) |  key[5]
    key_schedule[3] = (key[6] << 8) |  key[7]
    key_schedule[4] = (key[8] << 8) |  key[9]
    key_schedule[5] = (key[10] << 8) | key[11]
    key_schedule[6] = (key[12] << 8) | key[13]
    key_schedule[7] = (key[14] << 8) | key[15]

    round_1_key_1 = (key_schedule[2] << 16) | key_schedule[3]
    round_1_key_2 = (key_schedule[6] << 16) | key_schedule[7]
    round_2_key_1 = (key_schedule[0] << 16) | key_schedule[1]
    round_2_key_2 = (key_schedule[4] << 16) | key_schedule[5]

    initial_nonce = random.randbytes(16)

    print("[3] Attacking first roundkey")
    k_1 = 0
    k_2 = 0
    attempts_numbers = []

    incorrect_nibs = 0

    rng = lambda r: tqdm(range(32), desc=f'Attacking roundkey {r}') if verbosity == 0 else range(32)
    for i in rng(1):
        nib = None
        tries = 0
        num_tries = 0
        known_bit = 1 if i == 31 or i == 0 else 0

        while nib is None:
            tries += 1
            if tries > 10:
                print("ERR!! Cannot find a suitable candidate for nibble", i)
                return constants.STATUS_NOT_FOUND, 1, i, incorrect_nibs

            nib, num_tries = _recover_nibble(i, initial_nonce, capture_fn, verbosity, round=1, known_bit=known_bit, real_key_schedule=key_schedule)
        nib = nib & 0b11
        k_2 |= (nib & 0x1) << i
        k_1 |= ((nib & 0x2) >> 1) << i

        attempts_numbers.append(num_tries + (tries - 1) * 15)

        expected = (((round_1_key_1 >> i) & 1) << 1) | ((round_1_key_2 >> i) & 1)

        print("[--] Expected: ", bin(expected), "got:", bin(nib))
        if nib == expected:
            print("[--] Correct nibble found in", num_tries + (tries - 1) * 15, "attempts.")
        else:
            print("[!!] Incorrect nibble found in", num_tries + (tries - 1) * 15, "attempts.")
            incorrect_nibs += 1

    print("Number of attempts:", attempts_numbers)
    print("[-] Found first roundkey:")
    print("[-]", hex(k_1), "expected", hex(round_1_key_1), "diff", bin(k_1 ^ round_1_key_1))
    print("[-]", hex(k_2), "expected", hex(round_1_key_2), "diff", bin(k_2 ^ round_1_key_2))

    print("[4] Attacking second roundkey")
    k_3 = 0
    k_4 = 0
    for i in rng(2):
        nib = None
        tries = 0
        known_bit = 1 if i == 31 or i == 0 or i == 1 else 0

        while nib is None:
            tries += 1
            if tries > 10:
                print("ERR!! Cannot find a suitable candidate for nibble", i, "at round 2")
                return constants.STATUS_NOT_FOUND, 2, i, incorrect_nibs

            nib, _ = _recover_nibble(i, initial_nonce, capture_fn, verbosity, round=2, known_bit=known_bit, guessed_roundkey=(k_1, k_2), real_key_schedule=key_schedule)
        nib = nib & 0b11
        k_4 |= (nib & 0x1) << i
        k_3 |= ((nib & 0x2) >> 1) << i

        expected = (((round_2_key_1 >> i) & 1) << 1) | ((round_2_key_2 >> i) & 1)
        print("[--] Expected: ", bin(expected), "got:", bin(nib))
        if nib == expected:
            print("[--] Correct nibble found in", num_tries + (tries - 1) * 15, "attempts.")
        else:
            print("[!!] Incorrect nibble found in", num_tries + (tries - 1) * 15, "attempts.")
            incorrect_nibs += 1

    print("[-] Found second roundkey:")
    print("[-]", hex(k_3), "expected", hex(round_2_key_1), "diff", bin(k_3 ^ round_2_key_1))
    print("[-]", hex(k_4), "expected", hex(round_2_key_2), "diff", bin(k_4 ^ round_2_key_2))

    print("[5] Done!")
    FOUND_KEY = (k_3 << 96) | (k_1 << 64) | (k_4 << 32) | k_2
    FOUND_KEY = FOUND_KEY.to_bytes(16, 'big')
    print("[-] Found key :", FOUND_KEY.hex(sep=' ', bytes_per_sep=4))
    print("[-] Actual key:", key.hex(sep=' ', bytes_per_sep=4))

    if FOUND_KEY.hex() != key.hex():
        return constants.STATUS_WRONG_KEY, None, None, incorrect_nibs
    return constants.STATUS_FOUND, None, None, incorrect_nibs
