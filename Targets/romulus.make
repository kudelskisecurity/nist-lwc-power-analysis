ALG_NAME = romulus
ALG_VARIANT = romulusn

OPT = 3

ifeq ($(PLATFORM),CWLITEARM)
	ALG_PATH = $(CANDIDATES_BASEPATH)/$(ALG_NAME)/Implementations/crypto_aead/$(ALG_VARIANT)/arm_inline_asm
	SRC += $(ALG_PATH)/encrypt.c $(ALG_PATH)/skinny_key_schedule2.c $(ALG_PATH)/skinny_key_schedule3.c $(ALG_PATH)/skinny_main.c 
	O += -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16
else
	ALG_PATH = $(CANDIDATES_BASEPATH)/$(ALG_NAME)/Implementations/crypto_aead/$(ALG_VARIANT)/ref
	SRC += $(ALG_PATH)/encrypt.c $(ALG_PATH)/skinny_reference.c $(ALG_PATH)/romulus_n_reference.c
endif

