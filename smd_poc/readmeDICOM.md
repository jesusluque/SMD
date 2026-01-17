# DICOM Support for SMD (Self-Decoding Media)

This directory implements DICOM (Digital Imaging and Communications in Medicine) support for the SMD format. It allows medical images to be packaged alongside their specific decoding logic (compiled to WebAssembly), enabling a universal player to render them without pre-installed DICOM libraries.

## Architecture

The system consists of three main components adapted for DICOM:

1.  **Wasm Decoder (`wasm_dicom/`)**: A Rust project that uses `dicom-rs` and `image` crates. It compiles to a `.wasm` binary that accepts raw DICOM bytes and outputs a standard RGB8 pixel buffer.
2.  **Packager (`create_dicom_smd.py`)**: A Python utility that wraps a standard `.dcm` file and the compiled `.wasm` decoder into an `.smd` Atom container.
3.  **Player (`player.py`)**: The host application that reads the container, instantiates the embedded Wasm decoder, and displays the resulting image.

## Prerequisites

- **Rust Toolchain**: Required to compile the decoder.
    - target: `wasm32-wasip1` (or `wasm32-unknown-unknown`)
- **Python 3.10+**: For the packager and player.
- **Python Dependencies**:
    - `wasmtime`: Wasm runtime for Python.
    - `pillow`, `matplotlib`: For displaying the decoded result.

## Build Instructions

### 1. Compile the Decoder

Navigate to the `wasm_dicom` directory and run the build script. This compiles the Rust code into a standalone WebAssembly module.

```bash
cd smd_poc/wasm_dicom
./build.sh
```

*Note: If you encounter issues with `std` library linking, ensure your `rustup` toolchain for `wasm32-wasip1` is correctly installed.*

### 2. Create an SMD Atom

Use the helper script to package your DICOM file. This script expects the compiled `smd_dicom_decoder.wasm` to exist in the target directory.

```bash
cd smd_poc
python3 create_dicom_smd.py <input_file.dcm> <output_file.smd>
```

**Example:**
```bash
python3 create_dicom_smd.py scan_01.dcm scan_01.smd
```

### 3. Play the File

Run the player with the generated `.smd` file. The player sees the media type is `dicom`, detects the embedded Wasm logic, and executes it.

```bash
python3 player.py scan_01.smd
```

## Technical Details

- **Input Format**: The decoder expects standard DICOM formats. It currently supports Transfer Syntaxes supported by the `dicom-rs` crate (mostly uncompressed or basic encapsulation).
- **Pixel Data**: The Wasm logic normalizes high-bit-depth medical data (e.g., 12-bit or 16-bit grayscale) into 8-bit RGB for broad compatibility with standard display pipelines.
- **Fallback**: If the DICOM parsing fails (e.g., due to unsupported tags or missing headers), the decoder currently generates a placeholder pattern to prevent the player from crashing.

## Project Structure

```text
smd_poc/
├── wasm_dicom/             # Rust source for DICOM decoder
│   ├── src/lib.rs          # Decoding logic and ABI exports
│   ├── Cargo.toml          # Rust dependencies (dicom-rs, image)
│   └── build.sh            # Compilation script
├── create_dicom_smd.py     # Packager script for DICOM
├── player.py               # Universal SMD player
└── README.md               # Main project documentation
```
