import numpy as np
import time
from tqdm import tqdm
from util import to_bytes
from lascar import TraceBatchContainer


def capture_traces(wrap,
                   n_samples, cap_num_windows, cap_first_offset,
                   block_size): # TODO diff
    """
    A re-implementaton of wrap.capture_traces specifically designed for the elephant attack
    :param wrap:
    :param n_samples:
    :param cap_num_windows:
    :param cap_first_offset:
    :param nonce_gen:
    :param ad_gen:
    :return:
    """

    first_ad_block_size = block_size - 12
    nonce_gen = lambda: np.zeros(12, np.uint8)
    ad_gen = lambda: np.random.randint(0, 256, first_ad_block_size + block_size, np.uint8)

    cap_len = 24000 * cap_num_windows
    target, scope = wrap.target, wrap.scope

    # flush output
    target.read()

    scope.adc.timeout = 2
    scope.adc.samples = 24000

    traces = []
    values = []

    for _ in tqdm(range(n_samples), desc='Capturing traces'):
        target.flush()
        wrap.reset()

        trace = np.zeros(cap_len)
        nonce = nonce_gen()
        ad = ad_gen()
        wrap._set_ad(to_bytes(ad))

        for s in range(0, cap_len, 24000):
            scope.adc.offset = s + cap_first_offset
            scope.arm()

            target.simpleserial_write('n', to_bytes(nonce, 12) + b'\x00\x00\x00\x00')

            ret = scope.capture()

            if ret:
                raise IOError("Target timed out!")

            trace[s:s + 24000] = scope.get_last_trace()

            while scope.adc.state: time.sleep(0.005)

        traces.append(trace)
        values.append(ad[first_ad_block_size:first_ad_block_size + block_size]) # TODO diff

    return TraceBatchContainer(np.array(traces), np.array(values), copy=0)
