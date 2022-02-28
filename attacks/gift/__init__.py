import string
from argparse import ArgumentParser

import util.constants

from runners.cw_basic import WrappedChipWhisperer
import chipwhisperer as cw

def init_subcommand(subparser: ArgumentParser):
    return

def run(args):
    verbosity = args.verbosity
    from .attack import attack
    attack(verbosity)

def init_wrap():
    return WrappedChipWhisperer(
        alg='giftcofb128v1',
        platform='CWLITEARM',
        target_type=cw.targets.SimpleSerial,
        prog=cw.programmers.STM32FProgrammer)



def run_benchmark(parameters: dict[string, any], wrap) -> tuple[string, dict[string, any]]:
    from .attack import attack
    num_traces = parameters['num_traces']
    status, err_step, err_nibble, incorrect_nibs = attack(1, num_traces, wrap)

    return status, {"incorrect_nibs": incorrect_nibs, "error_step": err_step, "error_nibble": err_nibble} if status == util.constants.STATUS_NOT_FOUND else {}


benchmark_parameters = {
    "num_traces": [1, 3, 5, 7, 10]
}

