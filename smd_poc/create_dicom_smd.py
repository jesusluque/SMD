import os
import sys
import hashlib
import uuid
# Ensure we can import packager from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from packager import create_atom

def main():
    if len(sys.argv) < 3:
        print("Usage: python create_dicom_smd.py <input.dcm> <output.smd>")
        sys.exit(1)

    input_dcm = sys.argv[1]
    output_smd = sys.argv[2]
    
    # Path to the new WASM decoder
    wasm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wasm_dicom", "target", "wasm32-wasip1", "release", "smd_dicom_decoder.wasm")
    
    if not os.path.exists(wasm_path):
        print(f"Error: Wasm decoder not found at {wasm_path}")
        print("Please run 'wasm_dicom/build.sh' first.")
        sys.exit(1)

    # Extract Metadata using pydicom
    source_uuid = None
    origin_uuid = None
    duration = 0.0
    
    try:
        import pydicom
        ds = pydicom.dcmread(input_dcm, stop_before_pixels=True)
        
        # 1. Source UUID from SOPInstanceUID (Hash it to fit 16 bytes)
        sop_uid = ds.get("SOPInstanceUID", str(uuid.uuid4()))
        source_uuid = hashlib.md5(str(sop_uid).encode('utf-8')).digest()
        
        # 2. Origin UUID from StudyInstanceUID 
        study_uid = ds.get("StudyInstanceUID", str(uuid.uuid4()))
        origin_uuid = hashlib.md5(str(study_uid).encode('utf-8')).digest()
        
        print(f"Extracted Metadata from {input_dcm}:")
        print(f"  - SOPInstanceUID: {sop_uid}")
        print(f"  - StudyInstanceUID: {study_uid}")

    except ImportError:
        print("Warning: pydicom not found. Using random UUIDs.")
    except Exception as e:
        print(f"Warning: Failed to read DICOM metadata: {e}")

    print(f"Packaging {input_dcm} with DICOM decoder logic into {output_smd}...")
    create_atom(input_dcm, wasm_path, output_smd, media_type="dicom", source_uuid_bytes=source_uuid, origin_uuid_bytes=origin_uuid, duration=duration)
    print("Done!")

if __name__ == "__main__":
    main()
