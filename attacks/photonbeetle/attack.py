import itertools
import random
from concurrent.futures import Executor, ThreadPoolExecutor, ProcessPoolExecutor

import numpy as np
from scipy.stats import multivariate_normal
from tqdm import tqdm

from runners.cw_basic import WrappedChipWhisperer
from runners.native import NativeRunner
from . import TPL_PATH
from .classifier import select_column, compute_round_1, reorder
import pickle
import os.path
import chipwhisperer as cw
import multiprocessing
from util import constants

def attack(args, wrap=None):
    tpl_name = args.template
    tpl_name = TPL_PATH + tpl_name + ".tpl"
    num_traces = args.num_traces
    threads = args.threads if args.threads is not None else multiprocessing.cpu_count()

    print("Using", threads, "threads.")

    if not os.path.exists(TPL_PATH):
        print("No such model file:", tpl_name)
        exit(1)

    with open(tpl_name, 'rb') as model_file:
        template_data = pickle.load(model_file)

    return _do_attack(num_traces, template_data, threads, wrap)


def _exhaustive_search(pt, nonce, ct, key_options):
    runner = NativeRunner("bin/photon-beetle.so")
    num_it = 0  # for benchmarking

    print("[-] Running exhaustive search with pt=" + pt.hex() + ", nonce=" + nonce.hex() + ", expected ct=" + ct.hex())
    for n_errors in range(len(key_options)):
        # which byte will we check
        print("[-] Trying with", n_errors, "wrong columns...")
        wrong_bytes_combinations = itertools.combinations(range(len(key_options)), n_errors)

        for wrong_bytes in wrong_bytes_combinations:
            possible_values = itertools.product(*[k if i in wrong_bytes else [k[0]] for i, k in enumerate(key_options)])

            for value in possible_values:
                key = reorder(value)
                res = runner.encrypt(key, pt, nonce)
                print("\r  hypothesis", key.hex(), "  eq?", res == ct, end='')
                num_it += 1
                # print("\t", value.hex(), res.hex(), ct.hex(), res==ct)
                if res == ct:
                    print()
                    return key, num_it

        print()
    return None, num_it


def _do_attack(num_traces, template_data, threads, wrap=None):
    params = template_data['params']
    all_models = template_data['templates']

    platform = params['platform']
    executable = params['executable']
    win_size = params['num_windows']
    start = params['array_start']
    end = params['array_end']

    print("Loaded template for binary", executable, "on platform", platform)
    print("[1] Connecting to target platform")

    if wrap is None:
        wrap = WrappedChipWhisperer(alg=executable, platform=platform, target_type=cw.targets.SimpleSerial,
                                prog=cw.programmers.XMEGAProgrammer if platform == 'CWLITEXMEGA' else cw.programmers.STM32FProgrammer)

    print("[2] Recording traces")
    print("[-] Generating a random key to attack")
    key = random.randbytes(16)
    int_key = int.from_bytes(key, 'big')
    print("[-] Generated key", key.hex(' ', 8))
    data = wrap.capture_traces(key, num_traces, cap_num_windows=win_size, cap_first_offset=0)

    print("[3] Get a known pt->ct pair")
    pt = random.randbytes(16)
    nonce = random.randbytes(16)
    print("\tEncrypting plaintext", pt.hex(), "on board...")
    ct = wrap.encrypt(key=key, plaintext=pt, nonce=nonce)
    print("\tGave ciphertext", ct.hex())

    print("[4] Finding key bytes...")
    col_results = []
    col_num_iter = []
    nonces = [int.from_bytes(x.tobytes(), 'big') for x in data.values]

    exec = ProcessPoolExecutor(max_workers=threads)

    futures = []
    for i in range(8):
        future = exec.submit(_predict, nonces.copy(), data.leakages[:,start:end].copy(), all_models.copy(), i)
        futures.append(future)

    print()

    for i in range(8):
        # Wait for all features in order
        res, it = futures[i].result()
        col_results.append(res)
        col_num_iter.append(it)

    print("[5] Searching for correct key")
    # Remove constant
    col_results[0] = [x ^ 2 for x in col_results[0]]


    print("[-] Intermediate results")
    initially_incorrect_bytes = 0
    unrecoverable_bytes = 0
    for i in range(8):
        exp = hex(select_column(int_key, i, False))
        print("Column", i, "expected", exp)
        print("Got", [hex(x) for x in col_results[i]])
        if hex(col_results[i][0]) != exp:
            initially_incorrect_bytes += 1
        if exp not in [hex(x) for x in col_results[i]]:
            unrecoverable_bytes += 1
    print("[-]", initially_incorrect_bytes, "bytes are incorrect, among which", unrecoverable_bytes, "are unrecoverable")

    print("[-] Starting exhaustive search")

    found_key, num_it = _exhaustive_search(pt, nonce, ct, col_results)

    if found_key is None:
        print("Correct key not found, sorry.")
        return constants.STATUS_NOT_FOUND, col_num_iter, num_it, initially_incorrect_bytes, unrecoverable_bytes
    else:
        print("Found key:", found_key.hex())
        print("Expected :", key.hex())

        if key.hex() == found_key.hex():
            return constants.STATUS_FOUND, col_num_iter, num_it, initially_incorrect_bytes, unrecoverable_bytes
        return constants.STATUS_WRONG_KEY, col_num_iter, num_it, initially_incorrect_bytes, unrecoverable_bytes


def _predict(nonces, traces, models, col):
    # Select the 2 bytes of the nonce that are used for this column
    nonces_selected = [select_column(n, col, nonce=True) for n in nonces]

    # Get models and POI for this column
    models = models[col]
    POIs = [p for p, m, c in models]

    # Precompute the multivariate normal distribution for all rows in the column
    rv = [[multivariate_normal(means[HW], covs[HW]) for HW in range(5)] for _, means, covs in models]

    key_candidates_scores = np.zeros(2 ** 16)
    last_top = None
    identical_for = 0

    for j, trace in tqdm(enumerate(traces), desc=f"Evaluating column {col}...", position=col, total=len(traces)):
        a = [trace[POI] for POI in POIs]
        nonce = nonces_selected[j]

        # Compute the distribution for all hamming weights once (it's the longest operation, and doing it only once
        # saves a lot of time)
        estimates = [[np.log(rv[row][HW].pdf(a[row])) for HW in range(5)] for row in range(8)]

        # Test each key candidate
        for key in range(2 ** 16):
            round1_model = compute_round_1(col, nonce, key)

            for row, HW in enumerate(round1_model):
                key_candidates_scores[key] += estimates[row][HW]


        # Print our top 5 results so far
        argsorted = key_candidates_scores.argsort()[::-1][:16]
        current_top = argsorted[:4]

        # print("Round", j, "Top 4:", [hex(x) for x in current_top], end='')
        if last_top is not None and current_top[0] == last_top:
            identical_for += 1
        #    print(" identical for", identical_for, "rounds")
        else:
            last_top = current_top[0]
            identical_for = 0
        #    print(" different from last")

        if identical_for >= 25:
            # Fast exit if we have a stable candidate
            break

    return key_candidates_scores.argsort()[::-1][:4], j

