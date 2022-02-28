from lascar import TraceBatchContainer
from rainbow.utils import hw

from runners.emu_wrappers.x86 import x86
import numpy as np
from tqdm import tqdm

print("Initializing emulator...")
rt = x86("romulusn", 16, 16, sca=True)


def capture_traces(key, n_samples=200, instr_count=15000, start_at=0):
    print("Acquiring", n_samples, "traces...")
    traces = []
    nonces = []
    rt.emu.trace = True
    rt.emu.mem_trace = True
    rt.emu.trace_regs = True

    for i in tqdm(range(n_samples)):
        nonce = np.random.randint(0, 256, 16, np.uint8)
        _, _, _, r = rt.encrypt('', '', key, nonce.tobytes(), cnt=instr_count)
        r = r[start_at:]
        leakage = np.array([hw(i) for i in r]) + np.random.normal(0, 1.0, (len(r)))

        traces.append(leakage)
        nonces.append(nonce)

    return TraceBatchContainer(np.array(traces), np.array(nonces))

def encrypt(key, plaintext, nonce=None, ad=''):
    if nonce is None:
        nonce = np.random.randint(0, 256, 16, np.uint8).tobytes()

    ct_len, ct = rt.encrypt(plaintext, ad, key, nonce)

    return ct_len, ct
