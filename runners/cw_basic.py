import sys

from lascar import TraceBatchContainer
import chipwhisperer as cw
import numpy as np
from tqdm import tqdm
import time
import os.path
import re

from util import to_bytes


class WrappedChipWhisperer:
    def __init__(self, alg, platform='CWLITEARM', target_type=cw.targets.SimpleSerial, prog=None):
        if prog is None:
            if platform == 'CWLITEARM': prog = cw.programmers.STM32FProgrammer
            elif platform == 'CWLITEXMEGA': prog = cw.programmers.XMEGAProgrammer
            else: raise ValueError('unknown platform ' + platform + ". please provide the programmer manually")

        print(f"Initializing chip whisperer ({platform})...")
        try:
            self.scope = cw.scope()
            self.target = cw.target(self.scope, target_type)
        except:
            print("Cannot connect to ChipWhisperer.")
            sys.exit(0)

        print("Found ChipWhisperer!")

        time.sleep(0.5)
        try:
            self.scope.default_setup()
        except IOError as e:
            print(e)
            # Workaround, as CWLite doesn't work well
            pass

        file_path = "bin/{}-{}.hex".format(alg, platform)
        file_path = file_path if os.path.exists(file_path) else "../../" + file_path

        cw.program_target(self.scope, prog, file_path)

        time.sleep(0.05)
        print("CW buffer content:", self.target.read())

    def reset_target(self):
        self.scope.io.pdic = 'low'
        time.sleep(0.1)
        self.scope.io.pdic = 'high_z'
        time.sleep(0.1)

    def capture_traces(self, key, n_samples, cap_window_len=24000, cap_num_windows=5, cap_first_offset=0,
                       nonce_gen=(lambda: np.random.randint(0, 256, 16, np.uint8)), silent=False,
                       pt_gen=None, ad_gen=None, cap_total_len=None, operation='n'):
        """

        :param key:
        :param n_samples:
        :param cap_window_len:
        :param cap_num_windows:
        :param cap_first_offset:
        :param nonce_gen:
        :param silent:
        :param pt_gen:
        :param ad_gen:
        :param cap_total_len:
        :param values:
        :param operation: the targetted operation ; n for encryption, d for decryption
        :return:
        """
        cap_len = cap_window_len * cap_num_windows
        target, scope = self.target, self.scope

        # flush output
        target.read()

        scope.adc.timeout = 2
        scope.adc.samples = cap_window_len

        traces = []
        nonces = []

        target.set_key(key)

        _range = tqdm(range(n_samples), desc='Capturing traces') if not silent else range(n_samples)

        if pt_gen is not None:
            target.simpleserial_write('k', to_bytes(key, size=16))
            target.simpleserial_wait_ack()

        plaintext = None
        ad = None
        for _ in _range:
            nonce = nonce_gen()
            to_append = [nonce]
            # target.flush()
            trace = np.zeros(cap_len)

            # self.reset()

            if pt_gen is not None:
                # New plaintext and nonce, we need to set them
                plaintext = to_bytes(pt_gen())
                to_append.append(plaintext)
                self._set_pt(plaintext)

            if ad_gen is not None:
                # New plaintext and nonce, we need to set them
                ad = to_bytes(ad_gen())
                to_append.append(ad)
                self._set_ad(ad)

            for s in range(0, cap_len, cap_window_len):
                scope.adc.offset = s + cap_first_offset
                scope.arm()

                if pt_gen is None and ad_gen is None:
                    # No plaintext, use the quick method
                    target.simpleserial_write('e', key + to_bytes(nonce, 16))
                else:
                    # Send only the nonce
                    print("hello", operation, nonce)
                    target.simpleserial_write(operation, to_bytes(nonce, 16))

                ret = scope.capture()

                if ret:
                    raise IOError("Target timed out!")

                trace[s:s + cap_window_len] = scope.get_last_trace()

                # print(target.read())
                while scope.adc.state: time.sleep(0.005)

            traces.append(trace[:cap_total_len])
            if len(to_append) == 1:
                to_append = to_append[0]
            nonces.append(to_append)

        return TraceBatchContainer(np.array(traces), np.array(nonces), copy=0)

    def reset(self):
        self.target.simpleserial_write('r', bytes())
        self.target.simpleserial_wait_ack()

    def _set_pt(self, plaintext: bytes):
        target = self.target
        remaining = len(plaintext)
        for i in range(0, len(plaintext), 16):
            arr = [0 for _ in range(17)]
            arr[0] = remaining if remaining < 16 else 16
            remaining -= 16
            for idx, e in enumerate(plaintext[i:i+16]):
                arr[idx + 1] = e

            # print("write", bytes(arr).hex())
            target.simpleserial_write('p', bytes(arr))
            target.simpleserial_wait_ack()

    def _set_ad(self, ad: bytes):
        target = self.target
        remaining = len(ad)
        for i in range(0, len(ad), 16):
            arr = [0 for _ in range(17)]
            arr[0] = remaining if remaining < 16 else 16
            remaining -= 16
            for idx, e in enumerate(ad[i:i+16]):
                arr[idx + 1] = e
            target.simpleserial_write('a', bytes(arr))
            target.simpleserial_wait_ack()

    def encrypt(self, key, plaintext, nonce=None, ad=''):
        target, scope = self.target, self.scope

        # flush output
        target.read()
        time.sleep(0.1)

        if nonce is None:
            nonce = np.random.randint(0, 256, 16, np.uint8).tobytes()

        if plaintext != '' or ad != '':
            self.reset()

            if key is not None:
                self.set_key(key)

            if plaintext != '':
                self._set_pt(to_bytes(plaintext))

            if ad != '':
                self._set_ad(to_bytes(ad))

            target.simpleserial_write('n', nonce)
        else:
            target.simpleserial_write('e', key + nonce)

        while scope.adc.state: time.sleep(0.005)

        r = ''
        while len(r) < 6:  # r + 4 chars for the number of bytes to come + next r
            r += target.read()
            while len(r) > 0 and r[0] != 'r':
                r = r[1:]  # drop first char until its the desired "r"

            time.sleep(0.05)

        m = re.search('r([A-F0-9]{4})\nr', r)
        offset = 0

        if m is None:
            # Old version of the main file: we directly send the ct
            ct_len = 16
            offset = 1
        else:
            ct_len = int(m.group(1), 16)
            r = r[m.span()[1]:]  # drop the length and keep the rest

        while len(r) < (2 * ct_len + offset):
            r += target.read()
            time.sleep(0.05)

        # print(r)
        m = re.search('([A-F0-9]+)', r)
        # print(m)
        result = int(m.group(), 16).to_bytes(ct_len, 'big')

        return result

    def set_key(self, key):
        self.target.simpleserial_write('k', to_bytes(key, size=16))
        self.target.simpleserial_wait_ack()
        pass
