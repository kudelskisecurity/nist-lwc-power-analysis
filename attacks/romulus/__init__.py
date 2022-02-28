import string
from argparse import ArgumentParser
from util import select

from runners.cw_basic import WrappedChipWhisperer
import chipwhisperer as cw

sources = ['xmega', 'stm32', 'emulator']
verifiers = ['xmega', 'stm32', 'emulator', 'native']

def init_subcommand(subparser: ArgumentParser):
    subparser.add_argument('-s', '--source', dest='source', choices=sources, default="stm32", help='source of the traces')
    subparser.add_argument('-t', '--threshold', dest='threshold', type=float, default=None, help='override the threshold defined by the source')
    subparser.add_argument('-v', '--verifier', dest='verifier', choices=verifiers, default='native', help='function used to encrypt arbitrary plaintext and nonces using possible key guesses')
    subparser.add_argument('--save', dest='save', metavar='project name', default=None, help='save the generated data, traces, oracle response')
    subparser.add_argument('--load', dest='load', metavar='project name', default=None, help='the name of a saved project to load (ignores source)')
    subparser.add_argument('-n', '--num-traces', dest='num_traces', type=int, default=None, help='override the number of traces to capture')

def run(args):
    source = select('What is the source of the traces?', sources) if args.interactive or args.source is None else args.source
    verifier = select('What is the encryption verifier?', verifiers) if args.interactive or args.verifier is None else args.verifier

    from .attack import attack
    attack(source, verifier, args.load, args.save, args)

def init_wrap():
    # TODO - this works for benchmarks but not anything else
    return WrappedChipWhisperer(
        alg='romulusn',
        platform='CWLITEARM',
        target_type=cw.targets.SimpleSerial,
        prog=cw.programmers.STM32FProgrammer)


class dotdict(dict):
    __getattr__ = dict.get


def run_benchmark(parameters: dict[string, any], wrap) -> tuple[string, dict[string, any]]:
    obj = {
        "threshold": parameters["threshold"],
        "num_traces": parameters["num_traces"],
    }

    from .attack import attack
    status, num_iterations = attack("stm32", "native", None, None, dotdict(obj), wrap)

    return status, {"round_2_iterations": num_iterations}


benchmark_parameters = {
    "num_traces": [1800, 1900, 2000, 2100, 2200, 2300, 2400],
    "threshold": [None],
}

