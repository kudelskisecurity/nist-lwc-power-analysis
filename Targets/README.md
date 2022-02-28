# Building targets

This folder contains tools required to build the different targets for the ChipWhisperer attacks.

It contains multiple Makefiles that provide parameters to the ChipWhisperer building toolchain.

It also contains a `main.c` source file, that handles serial-communication with the Python attacks
code and runs the targeted algorithms.

## Prerequisites

Before building targets, you need to make sure that you installed the ChipWhisperer toolchain. You 
can use the submodules for this: `git submodule init` then `git submodule update`.

If you don't use the embeded ChipWhisperer installation, you will need to change the `CW_BASEPATH` variable
in the [Makefile](./Makefile).

You will also need to download and extract the codes of the candidates in the `Candidates` folder. 
If you have `wget` and `unzip` installed on your system, you can simply run the [download.sh](./download.sh) script.

## Building a target

The general command to build a target is:

```bash
make PLATFORM=CWLITEARM ALG=ROMULUS CRYPTO_TARGET=NONE SS_VER=SS_VER_1_1
```

In this example, we are building the ROMULUS algorithm for the CWLITEARM platform (the STM32 board). 
The target file will be `romulusn-<PLATFORM>.hex`. This file should be copied in the `bin` folder in the parent repository
to be used in the attacks.

The following values for `ALG` are available:

 - `ELEPHANT` builds the Elephant-160 target to `elephant160v2-<PLATFORM>.hex`
   - Adding `ALG_VARIANT=elephant176` builds the 176-bit variant of the algorithm as `elephant176v2-<PLATFORM>.hex`
 - `GIFT` builds the GIFT-COFB target to `giftcofb128v1-<PLATFORM>.hex`
 - `PHOTONBEETLE` builds the Photon-BEETLE target to `photonbeetleaead128rate128v1-<PLATFORM>.hex`
   - The implementation used depends on the platform.
   - STM32 (CWLITEARM) platform uses the `bitslice_sb32` implementation
   - AVR (CWLITEXMEGA) platform uses the `avr8_speed` implementation
 - `ROMULUS` builds the RomulusN target to `romulusn-<PLATFORM>.hex`
   - The STM32 (CWLITEARM) platform uses the `arm_inline_asm` implementation instead of the reference

Between builds, it is recommended to delete the `objdir-*` folders, otherwise build may fail and directories
may have to be created manually.
