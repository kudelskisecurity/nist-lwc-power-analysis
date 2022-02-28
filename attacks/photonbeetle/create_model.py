from tqdm import tqdm
import random

from attacks.photonbeetle import TPL_PATH
from .classifier import select_column, compute_round_1
import numpy as np
import chipwhisperer as cw

import itertools
import pickle
from runners.cw_basic import WrappedChipWhisperer
import os.path

NUM_POIS = 5
POI_MIN_SPACING = 5

def create_template(args):
    platform, prog, windows = ('CWLITEXMEGA', cw.programmers.XMEGAProgrammer, 1) if args.platform == 'xmega' else ('CWLITEARM', cw.programmers.STM32FProgrammer, 3)
    binary_file = args.binary_file
    tpl_name = args.template
    num_traces = args.num_traces

    # positions in the final array to keep
    array_start = args.array_start
    array_end = args.array_end
    windows = args.windows if args.windows is not None else windows

    capture_params = {'array_start': array_start, 'array_end': array_end, 'num_windows': windows, 'platform': platform,
                      'executable': binary_file}

    if not os.path.exists(TPL_PATH):
        os.mkdir(TPL_PATH)

    tpl_name = TPL_PATH + tpl_name + ".tpl"

    _do_create_template(platform, prog, capture_params, binary_file, num_traces, tpl_name)

def _fit(X, Y, col, row):
    X = X[:,col,row]  # select only the interesting column and row
    categories = [np.argwhere(X == i)[:,0] for i in range(5)]  # categorize the inputs
    arrays = [Y[k] for k in categories]
    averages = np.array([np.mean(k, axis=0) for k in arrays])

    diffs = [np.abs(a - b) for a, b in itertools.combinations(averages, 2)]
    sum_of_differences = np.sum(diffs, axis=0)

    POIs = []
    for i in range(NUM_POIS):
        # Find the biggest peak and add it to the list of POIs
        next_POI = sum_of_differences.argmax()
        POIs.append(next_POI)

        # Set nearby points to 0 to make sure we don't capture them too
        for j in range(max(0, next_POI - POI_MIN_SPACING), min(next_POI + POI_MIN_SPACING, len(sum_of_differences))):
            sum_of_differences[j] = 0

    mean_matrix = np.zeros((5, NUM_POIS))
    for HW in range(5):
        for i in range(NUM_POIS):
            mean_matrix[HW][i] = averages[HW][POIs[i]]

    covariance_matrix = np.zeros((5, NUM_POIS, NUM_POIS))
    for HW in range(5):
        for i in range(NUM_POIS):
            for j in range(NUM_POIS):
                x = arrays[HW][:, POIs[i]]
                y = arrays[HW][:, POIs[j]]
                covariance_matrix[HW, i, j] = np.cov(x, y)[0][1]

    print("\t[ok] Template fitted for ", col, row)
    return (POIs, mean_matrix, covariance_matrix)

def _do_create_template(platform, prog, capture_params, binary_file, num_traces, target_file):
    print(f"Creating a template for {platform} {binary_file}, using {num_traces}")
    print("[1] Connecting to target platform")

    wrap = WrappedChipWhisperer(alg=binary_file, platform=platform, target_type=cw.targets.SimpleSerial, prog=prog)

    print("[2] Recording traces")
    X = []
    Y = []
    for i in tqdm(range(num_traces), desc="Collecting data"):
        key = random.randbytes(16)
        nonce = random.randbytes(16)
        key_int = int.from_bytes(key, 'big')
        nonce_int = int.from_bytes(nonce, 'big')

        keys = [select_column(key_int ^ 0x20, c, False) for c in range(8)]
        nonces = [select_column(nonce_int, c, True) for c in range(8)]

        trace = wrap.capture_traces(key, n_samples=1, cap_num_windows=capture_params['num_windows'], cap_first_offset=0,
                                    nonce_gen=lambda: np.array(list(nonce), np.uint8), silent=True).leakages[0]

        Y.append(trace[capture_params['array_start']:capture_params['array_end']])
        X.append([compute_round_1(col, nonces[col], keys[col]) for col in range(8)])

    X = np.array(X)
    Y = np.array(Y)

    print("[3] Fitting templates")
    templates = [[_fit(X, Y, col, row) for row in range(8)] for col in range(8)]

    print("[4] Saving template")
    tpl_obj = {'params': capture_params, 'templates': templates}
    with open(target_file, 'wb') as model_file:
        pickle.dump(tpl_obj, model_file)

    print("[I] Done! Wrote template to", target_file)
    return

