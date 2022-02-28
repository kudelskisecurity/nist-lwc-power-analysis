import time

import numpy as np

from attacks.romulus.attack import _attack


def benchmark():
    from attacks.romulus.runners.cw_arm import encrypt as enc
    from attacks.romulus.runners.cw_arm import capture_traces as capture

    enc_oracle_fn = lambda nonce, pt: enc(key, pt, nonce)

    threshold = 0.3
    thresholds = [0.20 if i == 5 else 0.35 for i in range(8)]
    from attacks.romulus.runners.native import encrypt as enc
    enc_fn = enc


    with open("benchmark_stm32.csv", "a") as log:
        log.write("num_attempt,key,num_samples,time,error\n")
        log.flush()
        for num_attempt in range(0, 100):
            key = np.random.randint(0, 256, 16, np.uint8).tobytes()
            for num_samples in [2000]:
                start = time.time()
                capture_fn = lambda: capture(key, n_samples=num_samples)

                print(f"Attempt {num_attempt + 1} with {num_samples}...")
                print("The key is:", key.hex())

                try:
                    result, _ = _attack(capture_fn, enc_oracle_fn, enc_fn, threshold, real_key=key, thresholds=thresholds)
                    error = bytes([key[i] ^ result[i] for i in range(16)])
                    end = time.time()
                    log.write(f"{num_attempt},{key.hex(sep=' ', bytes_per_sep=4)},{num_samples},{end-start}"
                              f",{error.hex(sep=' ', bytes_per_sep=4)}\n")
                    log.flush()
                except Exception as e:
                    end = time.time()
                    log.write(f"{num_attempt},{key.hex(sep=' ', bytes_per_sep=4)},{num_samples},{end-start},{e}!\n")
                    log.flush()

if __name__ == "__main__":
    print("WARNING: invoking this script directly is not supported. You should use the main script in benchmark mode.")
    benchmark()