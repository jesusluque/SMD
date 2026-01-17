#!/bin/bash
set -e

echo "Building DICOM Wasm Decoder..."
# Ensure the target is installed
rustup target add wasm32-unknown-unknown

# Build
cargo build --target wasm32-unknown-unknown --release

echo "Build complete. Wasm binary is at target/wasm32-unknown-unknown/release/smd_dicom_decoder.wasm"
