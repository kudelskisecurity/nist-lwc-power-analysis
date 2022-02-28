# Power Analysis of some NIST Lightweight Candidates

This repository contains multiple power analysis attacks against some of the finalists of [NIST lightweight cryptography contest](https://csrc.nist.gov/Projects/lightweight-cryptography/finalists), implemented in Python on the ChipWhisperer framework.

Running the attacks requires a ChipWhisperer Lite ARM board. One attack (on Romulus) can also work on an emulated environment.

## Setup

Some of these attacks can only be run on linux, because the binaries used to confirm encryption are compiled for linux. 

In general, these attacks have been tested only under ArchLinux with recent versions of Python3 (Python 3.9+). They should
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

Then, go to `Tools/lascar` and run `python setup.py install --user` to install LASCAR:

> **Warning**: until a PR is accepted, you may need to update the `numpy` dependency in the `Tools/lascar/setup.py` file (line 39) to remove the upper bound. Update it to `"numpy>=1.17",`.

```bash
cd Tools/lascar
python setup.py install
cd ../..
```

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
 - `--num-traces=<number>`: sets the number of power traces to capture when running the attack (defaults to 50)
 - `--verify-key`: if specified, the guessed key will be verified by capturing a known plaintext, ciphertext combination and executing the Elephant algorithm locally to verify that the guessed key yields the correct ciphertext.

To use these attacks, you need to specify the following `<attack name>` parameter:

 - `elephant160` for the attack on Dumbo (Elephant-160)
 - `elephant176` for the attack on Jumbo (Elephant-176)
 - `elephant` for a generic code that can attack both candidates
   - The additional parameter `--block-size` (set to 176 or 160) specifies the variant of the candidate to attack

### GIFT-COFB

An attack on [GIFT-COFB](https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-spec-doc/gift-cofb-spec-final.pdf) based on [an attack by Breier et al.](https://ieeexplore.ieee.org/document/8782640/).

This is a differential plaintext attack assisted by side channel analysis (SCA-DPA). Our implementation has a very low success rate and is only here for completeness.

It is used by using the `gift-cofb` attack name, without additional arguments.

### Photon-BEETLE

A template attack on [Photon-BEETLE](https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-spec-doc/photon-beetle-spec-final.pdf).

As this is a template attack, it takes place in two different steps:

  1. The attacker creates a template of the attacked device (using a copy of the device)
  2. The attacker uses that template to perform the attack

The first step typically requires around 30k to 40k power-traces in our case, while the second step only requires 150 power traces.

We observed in our experiments that templates tend to depend on the USB plug used to make them.

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
 - `--num-traces=<num>` (default 20'000) changes the number of traces to capture to create the templates. Higher numbers require more memory but lead to more accurate templates.
 - `--windows=<num>` (default 1) changes the number of windows to capture in the power trace. A window is a set of 24'000 power samples, so increasing the number of windows to capture increases the length of the powertraces.
 - `--array-start=<num>` (default 0) and `--array-end=<num>` (default 24000) allow to select a subset of the captured power-traces to use when making the templates. This is usually not needed as point of interest are already selected in the traces.

The program will capture the defined amount of traces then categorize them and build the model. The built model is then stored in the `attacks/photonbeetle/models` directory.

#### Use a template

To attack using a previosuly built template, you need to use the `attack` mode as follows:

```bash
python main.py photon-beetle <template name> attack [optional args]
```

The `template name` is the name of the template you previously built. The optional arguments are the following:

 - `--num-traces=<num>` (default 100) changes the number of traces to capture to run the attack
 - `--num-threads=<num>` (defaults to the number of CPU cores) changes the number of parallel tasks that will be executed to search the key. A maximum of 8 threads can be used.

## RomulusN

A correlation power analysis attack on the [Romulus](https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-spec-doc/romulus-spec-final.pdf) cipher (more precisely, on the Romulus-N variant).

The attack name is `romulusn` and the optional parameters are:

 - `--save=<name>`: save the captured traces to the `projects/<name>` project files
 - `--load=<name>`: instead of capturing traces from the ChipWhisperer, use saved traces from `projects/<name>`
 - `--num-traces=<number>` (default 2000 for STM32 platform): sets the number of power traces to capture when running the attack

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