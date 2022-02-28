#!/bin/bash

mkdir Candidates
cd Candidates
wget https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-submissions/elephant.zip
wget https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-submissions/gift-cofb.zip
wget https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-submissions/photon-beetle.zip
wget https://csrc.nist.gov/CSRC/media/Projects/lightweight-cryptography/documents/finalist-round/updated-submissions/romulus.zip

unzip elephant.zip
unzip gift-cofb.zip
unzip photon-beetle.zip
unzip romulus.zip

rm *.zip

cd .. 
