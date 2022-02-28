import ctypes
import os.path
import numpy as np
import util


class NativeRunner:

    def __init__(self, lib_path):
        file_path = lib_path if os.path.exists(lib_path) else "../../" + lib_path
        self.lib = ctypes.CDLL(file_path)

    def encrypt(self, key, plaintext, nonce=None, adata=''):
        ct = ctypes.create_string_buffer(256)
        ct_len = ctypes.c_ulonglong(0)
        ct_len_ptr = ctypes.pointer(ct_len) # ctypes.create_string_buffer(16) # ulonglong
        pt = ctypes.c_char_p(util.to_bytes(plaintext))
        ad = ctypes.c_char_p(util.to_bytes(adata))
        k = ctypes.c_char_p(util.to_bytes(key))
        if nonce is None:
            nonce = np.random.randint(0, 256, 16, np.uint8).tobytes()
        nonce = ctypes.c_char_p(util.to_bytes(nonce))
        self.lib.crypto_aead_encrypt(ct, ct_len_ptr,
                                pt, ctypes.c_ulonglong(len(plaintext)),
                                ad, ctypes.c_ulonglong(len(adata)),
                                ctypes.c_void_p(),
                                nonce,
                                key
                                )

        return ct.raw[:ct_len.value]

    def decrypt(self, key, ciphertext, nonce, adata=''):
        m = ctypes.create_string_buffer(256)
        m_len = ctypes.c_ulonglong(0)
        m_len_ptr = ctypes.pointer(m_len) # ctypes.create_string_buffer(16) # ulonglong
        ct = ctypes.c_char_p(util.to_bytes(ciphertext))
        ad = ctypes.c_char_p(util.to_bytes(adata))
        k = ctypes.c_char_p(util.to_bytes(key))
        if nonce is None:
            nonce = np.random.randint(0, 256, 16, np.uint8).tobytes()
        nonce = ctypes.c_char_p(util.to_bytes(nonce))
        self.lib.crypto_aead_decrypt(m, m_len_ptr,
                                     ctypes.c_void_p(),
                                ct, ctypes.c_ulonglong(len(ciphertext)),
                                ad, ctypes.c_ulonglong(len(adata)),
                                nonce,
                                key)

        return m.raw[:m_len.value]
