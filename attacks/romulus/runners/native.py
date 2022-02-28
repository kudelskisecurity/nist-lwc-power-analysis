from runners.native import NativeRunner

runner = NativeRunner("bin/romulusn.so")


def encrypt(key, plaintext, nonce=None, adata=''):
    return runner.encrypt(key, plaintext, nonce, adata)
