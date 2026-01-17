# SMD Proof of Concept (PoC)

This directory contains a Proof of Concept implementation of the **Self Media Decoder (SMD)** specification.
It demonstrates the core philosophy of **"Codecs-in-media"** by packaging a **WebAssembly (Wasm)** decoder alongside a media file (JPEG) into a single "Atom" file.

## Files

- `packager.py`: A utility to create SMD Atoms. It bundles a media file and a decoder (Wasm binary) into a binary container with SMD metadata.
- `player.py`: A reference player that reads SMD Atoms. It extracts the embedded Wasm decoder, executes it using **Wasmtime**, and passes the media data to it.
- `wasm_decoder/`: A Rust project that compiles to WebAssembly. It uses the `image` crate to decode JPEG data inside the Wasm sandbox.
- `sample.jpg`: A sample JPEG image used as the source media.
- `example..jpg`: The generated SMD Atom containing both the `sample.jpg` and the compiled Wasm decoder.

## Usage

### Prerequisites

1.  **Python Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install wasmtime matplotlib Pillow
    ```

2.  **Rust & Wasm Target** (to build the decoder):
    ```bash
    rustup target add wasm32-wasip1
    ```

### 1. Build the Wasm Decoder

```bash
cd wasm_decoder
cargo build --target wasm32-wasip1 --release
cd ..
```

### 2. Create an SMD Atom (Packaging)

Run the packager to bundle the image and the Wasm binary:

```bash
python3 packager.py sample.jpg wasm_decoder/target/wasm32-wasip1/release/smd_decoder.wasm example..jpg
```

### 3. Play the SMD Atom (Decoding)

Run the player to "play" the file:

```bash
python3 player.py example..jpg
```

The player will:
1.  Read the header and metadata.
2.  Extract the Wasm payload.
3.  **Hot-Swap/Load** the Wasm module using `wasmtime`.
4.  Allocate memory in the Wasm instance and copy the media data.
5.  Execute the `decode` function in Wasm.
6.  Retrieve the decoded pixel data (RGB8) from Wasm memory.
7.  Reconstruct the image using Python's `Pillow` library.
8.  Display the image in a window using `matplotlib`.

## How it works

This PoC implements the **Logic Hot-Swap** mechanism described in the SMD spec using **real WebAssembly**.
The player is generic and knows nothing about JPEGs. It relies entirely on the Wasm code provided *inside* the file to process the data.
The Wasm module performs the heavy lifting (JPEG decoding) and returns raw pixel data to the host player for rendering.

## DICOM Support

This PoC also supports encoding and decoding **DICOM** medical images.

### 1. Build the DICOM Decoder
Navigate to `wasm_dicom` and compile the Rust code to WebAssembly:

```bash
cd wasm_dicom
./build.sh
cd ..
```

### 2. Create a DICOM SMD
Use the helper script to package a valid `.dcm` file with the compiled decoder:

```bash
python3 create_dicom_smd.py path/to/scan.dcm output_scan.smd
```

### 3. Play/Decode
The player detects the media type and uses the embedded Wasm decoder automatically. Since the logic travels with the media, the player doesn't need to know it's DICOM beforehand!

```bash
python3 player.py output_scan.smd
```
