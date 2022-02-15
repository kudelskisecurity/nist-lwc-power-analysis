ALG_NAME = photon-beetle
ALG_VARIANT = photonbeetleaead128rate128v1




ifeq ($(PLATFORM),CWLITEARM)
	ALG_PATH = $(CANDIDATES_BASEPATH)/$(ALG_NAME)/Implementations/crypto_aead/$(ALG_VARIANT)/bitslice_sb32
	SRC += $(ALG_PATH)/encrypt.c $(ALG_PATH)/photon.c
else
	ALG_PATH = $(CANDIDATES_BASEPATH)/$(ALG_NAME)/Implementations/crypto_aead/$(ALG_VARIANT)/avr8_speed
	SRC += $(ALG_PATH)/encrypt.c
	ASRC += $(ALG_PATH)/encrypt_core.S
endif

