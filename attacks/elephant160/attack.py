import itertools
import random
import lascar
from lascar import TraceBatchContainer
from util import constants

from . import init_wrap
from ..elephant_generic.capture import capture_traces
from runners.native import NativeRunner
from util.file_utils import *
from .classifiers import *

BLOCK_SIZE = 20

def _get_top_keys(results, keep_N=1):
    possible_keys = []
    for index, r in enumerate(results):
        possible_keys.append(abs(r).max(1).argsort()[::-1][:keep_N])
    return possible_keys


def _run_cpa(captured):
    eng = [
        lascar.CpaEngine(f'cpa{byte}', lambda ad, guess, index=byte: classifier_ad(index, ad, guess), range(256))
        for byte in range(BLOCK_SIZE)
    ]

    lascar.Session(captured, engines=eng).run(batch_size="auto")
    results = [engine.finalize() for engine in eng]

    possible_keys = _get_top_keys(results, keep_N=8)
    return possible_keys


# For tests only
def _expected_mask(key):
    initial_mask = spongent(key + b'\x00' * (BLOCK_SIZE - 16))
    return mask_lfsr_step(initial_mask)
# End for tests only


def inverse_verify_key(mask, pt=None, nonce=None, ct=None):
    mask = mask_lfsr_goback(mask)
    key = spongent_inverse(mask)

    if key[16:] == ([0] * (BLOCK_SIZE - 16)): # TODO diff
        key = bytes(key[:16])

        if ct is not None:
            # pt-ct pair given, verify key
            print()
            print("[-] Found potential key", key.hex(), " -- verifying")
            patch_runner = NativeRunner("bin/elephant160-patch.so")
            res = patch_runner.encrypt(key, pt, nonce)

            if res != ct:
                print("[!] Key was wrong.")
                return None

        return key

    return None


def exhaustive_search(pt, nonce, ct, mask):
    it_count = 0  # for benchmarking purposes

    print("[-] Running exhaustive search...")

    for n_errors in range(4):
        # which byte will we check
        print("[-] Trying with", n_errors, "wrong bytes...")
        wrong_bytes_combinations = itertools.combinations(range(BLOCK_SIZE), n_errors)

        for wrong_bytes in wrong_bytes_combinations:
            possible_values = itertools.product(*[mask[i] if i in wrong_bytes else [mask[i][0]] for i in range(BLOCK_SIZE)])

            for value in possible_values:
                key = inverse_verify_key(bytes(value), pt, nonce, ct)
                it_count += 1

                if key is not None:
                    print()
                    return key, it_count

        print()
    # print("This exhaustive search of the key space will never terminate, don't worry.")
    # print("If you see this message, the universe has probably ended and the key way very wrong.")
    return None, it_count


def attack(num_traces, load_file, save_file, verbosity, verify_key=False, wrap=None):
    if wrap is None and (load_file is None or verify_key):
        wrap = init_wrap()

    if load_file is not None and exists(load_file):
        print("[1] Loading captured traces")
        proj = load(load_file)
        nonces, traces = proj["inputs"], proj["traces"]
        captured = TraceBatchContainer(traces, nonces, copy=0)
        key = proj["key"]
        if wrap is not None:
            wrap.set_key(key)
    else:
        print("[1] Capturing traces on device")
        key = random.randbytes(16)
        wrap.set_key(key)
        # win_size, offset, sample_num = 1, 1953000, num_traces  # Variant compiled with -O0 (or O2?)
        win_size, offset, sample_num = 1, 974000, num_traces  # Variant compiled with -O3
        captured = capture_traces(wrap, sample_num, win_size, offset, BLOCK_SIZE)

        if save_file is not None:
            save(save_file, key, captured.values, captured.leakages, bytes(), bytes())

    print("Key to attack:\t\t", key.hex(" ", 1).upper())

    if verify_key:
        print("[1b] Get a known pt->ct pair")
        pt = random.randbytes(16)
        nonce = random.randbytes(12) + b'\x00\x00\x00\x00'
        if verbosity >= 1:
            print("\tEncrypting plaintext", pt.hex(), "on board...")

        ct = wrap.encrypt(key=None, plaintext=pt, nonce=nonce)
        if verbosity >= 1:
            print("\tGave ciphertext", ct.hex())
    else:
        pt, nonce, ct = None, None, None

    print("[2] Run correlation analysis on captured traces")
    masks = _run_cpa(captured)

    initially_incorrect_bytes = 0
    unrecoverable_bytes = 0
    if verbosity >= 1 or wrap is not None:
        exp = _expected_mask(key)

        for i, options in enumerate(masks):
            if verbosity >= 1:
                print("\tOptions for byte", i, ":", ["{:0x}".format(o) for o in options])
                print("\t\tExpected {:0x}. Found?".format(exp[i]), exp[i] in options)

            if options[0] != exp[i]:
                initially_incorrect_bytes += 1
            if exp[i] not in options:
                unrecoverable_bytes += 1

        print(initially_incorrect_bytes, "bytes are incorrect before exhaustive search")

    print("[4] Find the correct result")
    res, it_count = exhaustive_search(pt, nonce, ct, masks)

    if res is not None:
        print("[=>] Got:\t\t\t\t", res.hex())
        print("[=>] Expected:\t\t\t\t", key.hex())

        if key != res:
            print("[!] Key is wrong, expected", key.hex())
            return constants.STATUS_WRONG_KEY, it_count, initially_incorrect_bytes, unrecoverable_bytes  # should never happen in theory (P < 2^-32)
        return constants.STATUS_FOUND, it_count, initially_incorrect_bytes, unrecoverable_bytes
    return constants.STATUS_NOT_FOUND, it_count, initially_incorrect_bytes, unrecoverable_bytes
