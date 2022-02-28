import math
from math import ceil
from typing import Union

from numpy import ndarray


def input_hex(msg) -> bytes:
    while True:
        i = input(msg + ": ")
        if len(i) == 0:
            return bytes()
        i = i.lower()
        if len(i) > 2 and i[:2] == "0x":
            i = i[2:]

        try:
            i_int = int(i, 16)
            return i_int.to_bytes(2 * math.ceil(math.log(i_int, 256)), 'big')
        except:
            print("Invalid input, please retry.")


def to_bytes(msg: Union[str, bytes, int, ndarray], size=None) -> bytes:
    if type(msg) is str:
        mlen = len(msg)
        return bytes(0) if mlen == 0 else int(msg, 16).to_bytes(ceil(mlen / 2), 'big')
    elif type(msg) is bytes:
        return msg
    elif type(msg) is int and size is not None:
        return msg.to_bytes(size, 'big')
    elif type(msg) is ndarray:
        return msg.tobytes()
    else:
        raise TypeError(f"unknown type {type(msg)}")

def select_if_none(question, choices, selected):
    return select(question, choices) if selected is None else selected

def select(question, choices):
    choice = len(choices) + 1

    while choice < 1 or choice > len(choices):
        print("[?]", question)
        for i, c in enumerate(choices):
            print("\t", i + 1, c)
        r = input(">")

        try:
            choice = int(r)
        except ValueError:
            print("Invalid input")
    return choices[choice - 1]