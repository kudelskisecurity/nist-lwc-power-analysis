CANDIDATES_BASEPATH = Candidates
CW_BASEPATH = ../Tools/chipwhisperer

ifeq ($(ALG),GIFT)
	include ./gift.make
else ifeq ($(ALG),ELEPHANT)
	include ./elephant.make
else ifeq ($(ALG),PHOTONBEETLE)
	include ./photon-beetle.make
else ifeq ($(ALG),ROMULUS)
	include ./romulus.make
endif


# Target file name (without extension).
# This is the name of the compiled .hex file.
TARGET = $(ALG_VARIANT)

# List C source files here.
# Header files (.h) are automatically pulled in.
SRC += main.c

# -----------------------------------------------------------------------------

CW_BUILD_PATH = $(CW_BASEPATH)/hardware/victims/firmware
MKDIR_LIST = $(ALG_PATH)

#Add simpleserial project to build
include $(CW_BUILD_PATH)/simpleserial/Makefile.simpleserial

FIRMWAREPATH = $(CW_BUILD_PATH)
include $(CW_BUILD_PATH)/Makefile.inc

 