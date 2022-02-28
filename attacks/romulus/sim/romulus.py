"""
    Encodes a key into a usable 384b tweakey.
    cnt: the 56bit counter
    B: the 8 bit domain separation byte
    tweak: the 128b tweak
    key: the 128b key
"""
def encode_key(cnt: bytes, B: bytes, tweak: bytes, key: bytes):
    return cnt + B + b'\x00' * 8 + tweak + key


def init_lfsr() -> []:
    return [1, 0, 0, 0, 0, 0, 0]


def lfsr(cnt: []):
    fb0 = cnt[6] >> 7

    cnt[6] = (cnt[6] << 1) | (cnt[5] >> 7)
    cnt[5] = (cnt[5] << 1) | (cnt[4] >> 7)
    cnt[4] = (cnt[4] << 1) | (cnt[3] >> 7)
    cnt[3] = (cnt[3] << 1) | (cnt[2] >> 7)
    cnt[2] = (cnt[2] << 1) | (cnt[1] >> 7)
    cnt[1] = (cnt[1] << 1) | (cnt[0] >> 7)
    if fb0 == 1:
        cnt[0] = (cnt[0] << 1) ^ 0x95
    else:
        cnt[0] = (cnt[0] << 1)


def get_first_tweakey(nonce, key):
    # taken from the first steps of romulus_encrypt
    # \x1a is the hardcoded parameter here
    cnt = init_lfsr()
    lfsr(cnt)
    # nonce encryption
    return encode_key(b''.join([c.to_bytes(1, 'big') for c in cnt]), b'\x1a', nonce, key)

