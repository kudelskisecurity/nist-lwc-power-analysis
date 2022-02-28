import numpy as np


def ensure_native_gives_correct_result():
    from cw_xmega import encrypt as enc_xmega
    from native import encrypt as enc_native

    for i in range(32):
        key = np.random.randint(0, 256, 16, np.uint8).tobytes()
        nonce = np.random.randint(0, 256, 16, np.uint8).tobytes()

        left = enc_xmega(key, '', nonce)
        right = enc_native(key, '', nonce)

        print("xmega :", left.hex())
        print("native:", right.hex())
        print("eq    :", left == right)


ensure_native_gives_correct_result()