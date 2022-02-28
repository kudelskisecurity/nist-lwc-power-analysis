import string
from argparse import ArgumentParser

from runners.cw_basic import WrappedChipWhisperer
import chipwhisperer as cw


def init_subcommand(subparser: ArgumentParser):
    subparser.add_argument('--save', dest='save', metavar='project name', default=None,
                           help='save the generated data, traces, oracle response')
    subparser.add_argument('--load', dest='load', metavar='project name', default=None,
                           help='the name of a saved project to load (ignores source)')
    subparser.add_argument('-n', '--num-traces', dest='num_traces', type=int, default=50,
                           help='override the number of traces to capture')
    subparser.add_argument('--verify-key', dest='verify_key', action='store_const', const=True, default=False,
                           help='capture a known plaintext-ciphertext pair on the device to verify the key')


def init_wrap():
    input("Please connect the board and press enter.")
    return WrappedChipWhisperer(
        alg='elephant160v2-o3',
        platform='CWLITEARM',
        target_type=cw.targets.SimpleSerial,
        prog=cw.programmers.STM32FProgrammer)


def run(args):
    from .attack import attack
    attack(args.num_traces, args.load, args.save, args.verbosity, args.verify_key)


def run_benchmark(parameters: dict[string, any], wrap) -> tuple[string, dict[string, any]]:
    from .attack import attack
    num_traces = parameters['num_traces']
    status, it_count, initially_incorrect_bytes, unrecoverable_bytes = attack(num_traces, None, None, 0, verify_key=False, wrap=wrap)

    return status, {"exhaustive_search_iterations": it_count, "incorrect_bytes": initially_incorrect_bytes, "unrecoverable_bytes": unrecoverable_bytes}


benchmark_parameters = {
    "num_traces": [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
}
