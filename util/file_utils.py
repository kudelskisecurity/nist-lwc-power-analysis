import os.path
import numpy as np


def exists(name):
    return os.path.exists('./projects/' + name + ".proj")


def save(name, key: bytes, plaintexts, traces, oracle_pt: bytes, oracle_ct: bytes):
    print(f"Saving traces to project {name}")

    if not os.path.exists("./projects"):
        os.mkdir("./projects")

    with open(f"projects/{name}.proj", "wb") as f:
        f.write(b'\x01' if key is None else b'\x02')
        if key is not None:
            f.write(key)
        f.write(len(oracle_pt).to_bytes(4, 'big'))
        f.write(oracle_pt)
        f.write(len(oracle_ct).to_bytes(4, 'big'))
        f.write(oracle_ct)

    np.save(f"projects/{name}-pt.npy", plaintexts)
    np.save(f"projects/{name}-ct.npy", traces)


def load(name, load_traces=True):
    if not os.path.exists(f"./projects/{name}.proj"):
        return None

    pt = np.load(f"projects/{name}-pt.npy") if load_traces else []
    ct = np.load(f"projects/{name}-ct.npy") if load_traces else []
    key, oracle_pt, oracle_ct = None, None, None

    with open(f"projects/{name}.proj", "rb") as f:
        has_key = f.read(1) == b'\x02'
        key = f.read(16) if has_key else None

        len_bin: bytes = f.read(4)
        len_int = int.from_bytes(len_bin, 'big')
        oracle_pt = f.read(len_int)

        len_bin: bytes = f.read(4)
        len_int = int.from_bytes(len_bin, 'big')
        oracle_ct = f.read(len_int)

    return {"key": key, "inputs": pt, "traces": ct, "pt": oracle_pt, "ct": oracle_ct}

