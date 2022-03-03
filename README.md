# Power Analysis of some NIST Lightweight Candidates

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://docs.python.org/3.7/whatsnew/) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](http://www.gnu.org/licenses/gpl-3.0)

This repository contains multiple power analysis attacks against some of the finalists of the [NIST lightweight cryptography contest](https://csrc.nist.gov/Projects/lightweight-cryptography/finalists), implemented in Python on the ChipWhisperer framework.

Running the attacks requires a ChipWhisperer Lite ARM board. One attack (on Romulus) can also work on an emulated environment.

Presentation of these attacks will follow as conference papers and/or articles on our blog.

**Quick access**:

 - [Setup guide](#setup)
 - [How to run the attacks](#running-the-attacks)
   - [Attack on Elephant](#elephant)
   - [Attack on GIFT-COFB](#gift-cofb)
   - [Attack on Photon-BEETLE](#photon-beetle)
   - [Attack on RomulusN](#romulusn)
 - [Source structure](#source-code)

## Setup

Some of these attacks can only be run on linux, because the binaries used to confirm encryption are compiled for linux. 

In general, these attacks have been tested only under ArchLinux with recent versions of Python3 (Python 3.9 and Python 3.10). They should
work correctly with all versions of Python higher than 3.5.

### Prepare ChipWhisperer

Make sure to install the ChipWhisperer pre-requisites for your system according to ChipWhisperer's documentation: https://chipwhisperer.readthedocs.io/en/latest/prerequisites.html#prerequisites-linux

### Create a virtual environment

For example on Linux with the `virtualenv` tool (if not available, install it using `pip install --global virtualenv`):

```bash
virtualenv venv
````

Then, activate it:

```bash
source venv/bin/activate
```

The activation script depends on the shell you used. For example, the script for _Fish_ is `venv/bin/activate.fish`.

All the rest of the instructions suppose the virtual environment has been activated in the current shell.

### Install python requirements

First, install the packages that are available on PyPi:

```bash
pip install wheel
pip install -r requirements.txt
```

The attacks in this repository rely on LASCAR, a side channel analysis tool from Ledger Dungeon. It is not available on PyPi, so it must be compiled locally before installing requirements.

If not already done, initialize submodules `git submodule init` and update them `git submodule update`.

Then, go to `Tools/lascar` and run `python setup.py install` to install LASCAR:

### Optional: compile the desired targets

The compiled targets for the ChipWhisperer Lite ARM board are already provided in the `bin/` folder.

You can recompile them yourself from the source of the candidates, by following instructions in [Targets](Targets/README.md).

## Running the attacks

All the attacks can be executed from a single tool

```bash
python main.py [general args] <attack name> [attack args]
```

The general arguments are the following:

 - `--seed=<number>`: provides a seed to initialize the random generator (that generates the keys to attack), to make an attack reproducible
 - `-v` and `-vv` control the verbosity of the output (their effect depends on the attack)

The following attacks are available:

### Elephant

Attacks on the [Elephant](https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-spec-doc/elephant-spec-final.pdf) cipher. There are three variants of the Elephant attacks. They all take the following optional parameters:

 - `--save=<name>`: save the captured traces to the `projects/<name>` project files
 - `--load=<name>`: instead of capturing traces from the ChipWhisperer, use saved traces from `projects/<name>`
 - `--num-traces=<number>` (default 50): set the number of power traces to capture when running the attack
 - `--verify-key`: if specified, the guessed key will be verified by capturing a known plaintext, ciphertext combination and executing the Elephant algorithm locally to verify that the guessed key yields the correct ciphertext.

To use these attacks, you need to specify the following `<attack name>` parameter:

 - `elephant160` for the attack on Dumbo (Elephant-160)
 - `elephant176` for the attack on Jumbo (Elephant-176)
 - `elephant` for a generic code that can attack both candidates
   - The additional parameter `--block-size` (set to 176 or 160) specifies the variant of the candidate to attack

### GIFT-COFB

An attack on [GIFT-COFB](https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-spec-doc/gift-cofb-spec-final.pdf) based on [an attack by Breier et al.](https://ieeexplore.ieee.org/document/8782640/).

This is a differential plaintext attack assisted by side channel analysis (SCA-DPA). Our implementation of this attack has a very low success rate.

It is used by using the `gift-cofb` attack name, without additional arguments.

### Photon-BEETLE

A template attack on [Photon-BEETLE](https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-spec-doc/photon-beetle-spec-final.pdf).

As this is a template attack, it takes place in two different steps:

  1. The attacker creates a template of the attacked device (using a copy of the device)
  2. The attacker uses that template to perform the attack

The first step typically requires around 30k to 40k power-traces in our case, while the second step only requires 150 power traces.

We observed in our experiments that templates tend to depend on the USB port used to make them.

The attack name is `photon-beetle`. The general usage is `python main.py photon-beetle <template name> <attack|template> ...`.

#### Create a template

To create a template, you need to use the `template` mode as follows:

```bash
python main.py photon-beetle <template name> template <platform> <binary file> [optional args]
```

The mandatory arguments are:
 - `template name` is a name of your choice that designates this template
 - `platform` is either `stm32` or `xmega`, it's the target device (`stm32` for ChipWhisperer Lite ARM, `xmega` for ChipWhisperer Lite XMEGA) 
 - `binary file` is the prefix of the binary file to run. The file must be in the `bin/` folder. Using the given prefix `<binary file>`, the board is flashed with `bin/<binary file>-{CWLITEARM|CWLITEXMEGA}.bin`, depending on the target platform.
  
The optional parameters are:
 - `--num-traces=<num>` (default 20'000): set the number of traces to capture to create the templates. Higher numbers require more memory but lead to more accurate templates.
 - `--windows=<num>` (default 1): set the number of windows to capture in the power trace. A window is a set of 24'000 power samples, so increasing the number of windows to capture increases the length of the powertraces.
 - `--array-start=<num>` (default 0) and `--array-end=<num>` (default 24000): select a subset of the captured power-traces to use when making the templates. This is usually not needed as point of interest are already selected in the traces.

The program will capture the defined amount of traces then categorize them and build the model. The built model is then stored in the `attacks/photonbeetle/models` directory.

#### Use a template

To attack using a previosuly built template, you need to use the `attack` mode as follows:

```bash
python main.py photon-beetle <template name> attack [optional args]
```

The `template name` is the name of the template you previously built. The optional arguments are the following:

 - `--num-traces=<number>` (default 50): set the number of power traces to capture when running the attack
 - `--num-threads=<num>` (defaults to the number of CPU cores): set the number of parallel tasks that will be executed to search the key. A maximum of 8 threads can be used.
 - `--num-identical=<num>` (default 25): control the confidence of the prediction method by defining how many consecutive rounds a key prediction has to have the highest score to be returned as the correct key
 - `--keep=<num>` (default 4): control the number of predictions to return for each column. A higher number of predictions increases the likelihood that the exhaustive search step will recover the key, but extends the runtime of this step.

### RomulusN

A correlation power analysis attack on the [Romulus](https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-spec-doc/romulus-spec-final.pdf) cipher (more precisely, on the Romulus-N variant).

The attack name is `romulusn` and the optional parameters are:

 - `--save=<name>`: save the captured traces to the `projects/<name>` project files
 - `--load=<name>`: instead of capturing traces from the ChipWhisperer, use saved traces from `projects/<name>`
 - `--num-traces=<number>` (default 2000 for STM32 platform): set the number of power traces to capture when running the attack

Other arguments allow you to change the target platform type. This is not recommended.
 - `--source=<source>` (default `stm32`): choose between `xmega`, `stm32` and `emulator`. The `emulator` source is based on the Rainbow emulator, which you must install.
 - `--verifier=<verif>` (default `native`): choose between `xmega`, `stm32`, `emulator` and `native`. This arguments controls how key candidates are verified. The chosen platform must enable encrypting an arbitrary plaintext with an arbitrary key and returning the ciphertext. Using anything else than `native` is not recommended and very slow.
 - `--threshold=<num>` (absent by default): override the thresholds used in the attack to detect wrong bytes in the first half of the key with a single value

## Source code

The implementation of the attacks can be found in the `attacks` folder. Each attack has its own sub-folder and python
package. Each of them is structured as follows:

 - `__init__.py` contains some boilerplate to integrate the attacks to the tool: command line parameters specification, attack entrypoint for the command line tool, and benchmarking hooks
 - `attack.py` contains the general code of the attack
 - additional files contains the code of the model used in the attack

The `Targets` folder contains the toolchain to build the targets, together with some documentation on how to build them.

The `benchmark_analysis` folder contains a few scripts based on Matplotlib that generate plot for the results of the benchmarks that can be found in the `benchmarks` folder. 

## Benchmarking

A tool to benchmark the attacks is available in `benchmark.py`. The variables that are benchmarked can be configured in the `__init__.py` file of the attack you want to benchmark.

The benchmarking tool is run with `python benchmark.py <attack name> <project name> [-n number of attempts per perameter combination]`. Benchmark results are stored in `benchmarks/<attack name>-<project name>.benchmark.proj`.