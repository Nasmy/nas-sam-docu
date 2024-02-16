#!/usr/bin/env bash

apt-get update
apt-get install -y g++ # or clang++ (presumably)
apt-get install -y autoconf automake libtool
apt-get install -y pkg-config
apt-get install -y libpng-dev
apt-get install -y libjpeg8-dev
apt-get install -y libtiff5-dev
apt-get install -y zlib1g-dev
apt-get install -y libwebpdemux2 libwebp-dev
apt-get install -y libopenjp2-7-dev
apt-get install -y libgif-dev
apt-get install -y libarchive-dev libcurl4-openssl-dev
apt-get install -y wget unzip
apt-get install -y libleptonica-dev libomp-dev

rm -rf /var/lib/apt/lists/*

wget https://github.com/tesseract-ocr/tesseract/archive/refs/tags/4.1.1.zip
unzip 4.1.1.zip
rm 4.1.1.zip

cd tesseract-4.1.1 || exit 1
./autogen.sh
./configure CXXFLAGS="-fopenmp"

make -j$(nproc)
make install
ldconfig
cd ..
rm -rf tesseract-4.1.1
tesseract -v

# Final version of tesseract
# ---------------------------------------
#tesseract 4.1.1
# leptonica-1.79.0
#  libgif 5.1.9 : libjpeg 6b (libjpeg-turbo 2.0.6) : libpng 1.6.37 : libtiff 4.2.0 : zlib 1.2.11 : libwebp 0.6.1 : libopenjp2 2.4.0
# Found AVX2
# Found AVX
# Found FMA
# Found SSE
# Found OpenMP 201511
# Found libarchive 3.4.3 zlib/1.2.11 liblzma/5.2.5 bz2lib/1.0.8 liblz4/1.9.3 libzstd/1.4.8
# ---------------------------------------