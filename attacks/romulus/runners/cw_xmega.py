import chipwhisperer as cw
import numpy as np

from runners.cw_basic import WrappedChipWhisperer

wrap = WrappedChipWhisperer(
    alg='romulusn',
    platform='CWLITEXMEGA',
    target_type=cw.targets.SimpleSerial,
    prog=cw.programmers.XMEGAProgrammer)


def reset_target(scope):
    return wrap.reset_target()


def capture_traces(key, n_samples):
    return wrap.capture_traces(key, n_samples, cap_num_windows=2, cap_first_offset=25000)
                               # pt_gen=(lambda: np.random.randint(0, 256, 16, np.uint8)))


def encrypt(key, plaintext, nonce=None, ad=''):
    return wrap.encrypt(key, plaintext, nonce, ad)
