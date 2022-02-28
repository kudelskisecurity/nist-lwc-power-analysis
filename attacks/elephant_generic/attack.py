import itertools
import random
import lascar
from lascar import TraceBatchContainer
from util import constants

from .capture import capture_traces
from runners.native import NativeRunner
from util.file_utils import *
from .classifiers import classifier_ad


def _get_top_keys(results, keep_N=1):
    possible_keys = []
    for index, r in enumerate(results):
        possible_keys.append(abs(r).max(1).argsort()[::-1][:keep_N])
    return possible_keys


def _run_cpa(classifier, captured):
    lfsr_iv = classifier.lfsr_iv
    state_bytes = classifier.state_bytes
    eng = [
        lascar.CpaEngine(f'cpa{byte}', lambda ad, guess, index=byte: classifier_ad(lfsr_iv, state_bytes, index, ad, guess), range(256))
        for byte in range(classifier.state_bytes)
    ]

    lascar.Session(captured, engines=eng).run(batch_size="auto")
    results = [engine.finalize() for engine in eng]

    possible_keys = _get_top_keys(results, keep_N=8)
    return possible_keys


# For tests only
def _expected_mask(classifier, key):
    initial_mask = classifier.spongent(key + b'\x00' * (classifier.state_bytes - 16))
    return classifier.mask_lfsr_step(initial_mask)
# End for tests only


def inverse_verify_key(classifier, mask, pt=None, nonce=None, ct=None):
    mask = classifier.mask_lfsr_goback(mask)
    key = classifier.spongent_inverse(mask)

    if key[16:] == ([0] * (classifier.state_bytes - 16)):
        key = bytes(key[:16])

        if ct is not None:
            # pt-ct pair given, verify key
            print()
            print("[-] Found potential key", key.hex(), " -- verifying")
            patch_runner = NativeRunner(f"bin/elephant{classifier.state_bits}-patch.so")
            res = patch_runner.encrypt(key, pt, nonce)

            if res != ct:
                print("[!] Key was wrong.")
                return None

        return key

    return None


def exhaustive_search(classifier, pt, nonce, ct, mask):
    it_count = 0  # for benchmarking purposes

    print("[-] Running exhaustive search...")

    for n_errors in range(4):
        # which byte will we check
        print("[-] Trying with", n_errors, "wrong bytes...")
        wrong_bytes_combinations = itertools.combinations(range(classifier.state_bytes), n_errors)

        for wrong_bytes in wrong_bytes_combinations:
            possible_values = itertools.product(*[mask[i] if i in wrong_bytes else [mask[i][0]] for i in range(classifier.state_bytes)])

            for value in possible_values:
                key = inverse_verify_key(classifier, bytes(value), pt, nonce, ct)
                it_count += 1

                if key is not None:
                    print()
                    return key, it_count

        print()
    # print("This exhaustive search of the key space will never terminate, don't worry.")
    # print("If you see this message, the universe has probably ended and the key way very wrong.")
    return None, it_count


def attack(num_traces, load_file, save_file, verbosity, classifier, verify_key=False, wrap=None, init_wrap=None):
    if wrap is None:
        if init_wrap is None:
            raise ValueError("If wrap is none, init_wrap must be provided")
        wrap = init_wrap()

    if load_file is not None and exists(load_file):
        print("[1] Loading captured traces")
        proj = load(load_file)
        nonces, traces = proj["inputs"], proj["traces"]
        captured = TraceBatchContainer(traces, nonces, copy=0)
        key = proj["key"]
        wrap.set_key(key)
    else:
        print("[1] Capturing traces on device")
        key = random.randbytes(16)
        wrap.set_key(key)
        # win_size, offset, sample_num = 1, 1975000, num_traces
        win_size, offset, sample_num = 1, classifier.attack_point, num_traces
        captured = capture_traces(wrap, sample_num, win_size, offset, classifier.state_bytes)

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
    masks = _run_cpa(classifier, captured)

    initially_incorrect_bytes = 0
    unrecoverable_bytes = 0
    if verbosity >= 1 or wrap is not None:
        exp = _expected_mask(classifier, key)

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
    res, it_count = exhaustive_search(classifier, pt, nonce, ct, masks)

    if res is not None:
        print("[=>] Got:\t\t\t\t", res.hex())
        print("[=>] Expected:\t\t\t\t", key.hex())

        if key != res:
            print("[!] Key is wrong, expected", key.hex())
            return constants.STATUS_WRONG_KEY, it_count, initially_incorrect_bytes, unrecoverable_bytes  # should never happen in theory (P < 2^-32)
        return constants.STATUS_FOUND, it_count, initially_incorrect_bytes, unrecoverable_bytes
    return constants.STATUS_NOT_FOUND, it_count, initially_incorrect_bytes, unrecoverable_bytes
