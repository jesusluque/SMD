import struct
import uuid
import sys
import os
from wasmtime import Store, Module, Instance, Engine, Linker, WasiConfig

def play_atom(atom_path):
    print(f"Opening SMD Atom: {atom_path}")
    
    with open(atom_path, 'rb') as f:
        # 1. Read Sequence Header
        atom_uuid = f.read(16)
        source_uuid = f.read(16)
        origin_uuid = f.read(16)
        start_time = struct.unpack('>d', f.read(8))[0]
        duration = struct.unpack('>d', f.read(8))[0]
        
        print(f"  - Atom UUID: {uuid.UUID(bytes=atom_uuid)}")
        print(f"  - Timestamp: {start_time}s")
        
        # 1.5 Read Media Descriptor
        media_type_len = struct.unpack('>I', f.read(4))[0]
        media_type = f.read(media_type_len).decode('utf-8')
        attributes_len = struct.unpack('>I', f.read(4))[0]
        attributes = f.read(attributes_len).decode('utf-8')
        
        print(f"  - Media Type: {media_type}")
        if attributes:
            print(f"  - Attributes: {attributes}")
        
        # 2. Read Logic Identity
        logic_version = struct.unpack('>I', f.read(4))[0]
        logic_fingerprint = f.read(32)
        logic_size = struct.unpack('>I', f.read(4))[0]
        
        print(f"  - Decoder Version: {logic_version}")
        print(f"  - Decoder Fingerprint: {logic_fingerprint.hex()[:8]}...")
        
        logic_payload = f.read(logic_size)
        
        # 3. Read Media Data
        media_size = struct.unpack('>I', f.read(4))[0]
        media_data = f.read(media_size)
        
        print(f"  - Media Data Size: {media_size} bytes")
        
        # 4. "Hot-Swap" / Load Decoder
        print("\n[Player] Loading embedded Wasm decoder...")
        
        try:
            # Initialize Wasmtime
            engine = Engine()
            store = Store(engine)
            
            # Configure WASI (connect stdout to python stdout)
            wasi_config = WasiConfig()
            wasi_config.inherit_stdout()
            wasi_config.inherit_stderr()
            store.set_wasi(wasi_config)
            
            linker = Linker(engine)
            linker.define_wasi()
            
            # Compile module
            module = Module(engine, logic_payload)
            instance = linker.instantiate(store, module)
            
            # 5. Execute Decode
            print("[Player] Executing Wasm decoder...")
            
            # Get exports
            alloc = instance.exports(store)["alloc"]
            # dealloc = instance.exports(store)["dealloc"] # Not strictly needed for one-shot
            decode = instance.exports(store)["decode"]
            memory = instance.exports(store)["memory"]
            
            # Allocate memory in Wasm
            ptr = alloc(store, len(media_data))
            
            # Write media data to Wasm memory
            # memory.write(store, ptr, media_data) # This might be the API, let's check or use bytearray
            # Wasmtime python API for memory writing:
            # memory.data_ptr(store) gives raw pointer? No.
            # memory.write(store, offset, data) is likely.
            # Actually, memory is a Memory object.
            # Let's try writing directly.
            
            # memory.write(store, ptr, media_data)
            # Wait, wasmtime-py memory access:
            # mem = instance.exports(store)["memory"]
            # mem.write(store, media_data, ptr) # (store, data, offset) ?
            # Let's check documentation or assume standard: write(store, data, offset) or similar.
            # Actually, it seems to be: memory.write(store, data, start)
            
            # Let's try a safer way if unsure:
            # memory_data = memory.data_ptr(store)
            # ctypes.memmove(...)
            # But let's try the high level API first.
            # Based on docs, it might be: memory.write(store, media_data, ptr)
            
            # Let's assume memory.write(store, bytes, offset)
            # Wait, the order might be offset, bytes.
            # Let's try to find the API.
            # "write(store, value, offset)"
            
            # Actually, let's use the bytearray view if possible.
            # mem_data = memory.data(store) # returns a memoryview/bytearray?
            # mem_data[ptr : ptr+len(media_data)] = media_data
            
            # Allocate memory for params
            params = b"view=left" # Example parameter
            params_ptr = alloc(store, len(params))

            mem_data = memory.data_ptr(store)
            import ctypes
            
            # Calculate destination address
            # mem_data is a POINTER(c_ubyte). We need the raw address.
            # Note: mem_data.contents accesses the first element, addressof gets its address.
            base_addr = ctypes.addressof(mem_data.contents)
            dst_addr = base_addr + ptr
            
            ctypes.memmove(dst_addr, media_data, len(media_data))
            
            # Write params
            params_dst_addr = base_addr + params_ptr
            ctypes.memmove(params_dst_addr, params, len(params))
            
            # Call decode
            result = decode(store, ptr, len(media_data), params_ptr, len(params))
            
            print(f"[Player] Wasm returned: {result}")
            
            if result == 0:
                print("[Player] Decode successful (according to Wasm).")
                
                # Retrieve image data from Wasm
                get_width = instance.exports(store)["get_width"]
                get_height = instance.exports(store)["get_height"]
                get_output_ptr = instance.exports(store)["get_output_ptr"]
                get_output_len = instance.exports(store)["get_output_len"]
                
                width = get_width(store)
                height = get_height(store)
                out_ptr = get_output_ptr(store)
                out_len = get_output_len(store)
                
                print(f"[Player] Retrieved dimensions: {width}x{height}")
                print(f"[Player] Output buffer: ptr={out_ptr}, len={out_len}")
                
                if out_len > 0 and out_ptr != 0:
                    # Read pixel data from Wasm memory
                    mem_data = memory.data_ptr(store)
                    base_addr = ctypes.addressof(mem_data.contents)
                    src_addr = base_addr + out_ptr
                    
                    # Create a buffer to hold the data
                    pixel_data = (ctypes.c_ubyte * out_len)()
                    ctypes.memmove(pixel_data, src_addr, out_len)
                    
                    # Convert to Python bytes
                    raw_bytes = bytes(pixel_data)
                    
                    # Create Image using Pillow
                    try:
                        from PIL import Image
                        import matplotlib.pyplot as plt
                        
                        # We know it's RGB8 from the Rust code
                        img = Image.frombytes("RGB", (width, height), raw_bytes)
                        print("[Player] Reconstructed image from Wasm pixel data.")
                        
                        # Display the image using Matplotlib
                        print("[Player] Displaying image in a window...")
                        plt.figure(figsize=(width/100, height/100), dpi=100) # Optional: try to match size
                        plt.imshow(img)
                        plt.axis('off') # Hide axes
                        plt.title("Decoded from SMD Atom (Wasm)")
                        plt.show()
                        
                    except ImportError as e:
                        print(f"[Player] Required library not found: {e}")
                        print("[Player] Ensure Pillow and matplotlib are installed.")
                else:
                    print("[Player] Error: Invalid output buffer from Wasm.")
            else:
                print("[Player] Decode failed.")
            
        except Exception as e:
            print(f"[Player] Error executing Wasm decoder: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python player.py <file.smd>")
        sys.exit(1)
        
    play_atom(sys.argv[1])
