import chipwhisperer as cw
import numpy as np

from runners.cw_basic import WrappedChipWhisperer

wrap = WrappedChipWhisperer(
    alg='romulusn',
    platform='CWLITEARM',
    target_type=cw.targets.SimpleSerial,
    prog=cw.programmers.STM32FProgrammer)


def reset_target(scope):
    return wrap.reset_target()


def capture_traces(key, n_samples):
    return wrap.capture_traces(key, n_samples, cap_num_windows=1, cap_first_offset=0)


def encrypt(key, plaintext, nonce=None, ad=''):
    return wrap.encrypt(key, plaintext, nonce, ad)
