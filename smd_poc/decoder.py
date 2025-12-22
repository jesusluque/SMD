# This represents the "LogicPayload" (Wasm) in the SMD spec.
# In a real implementation, this would be a compiled .wasm module.
# For this PoC, we use a Python script to demonstrate the "Codecs-in-media" concept.

import io
try:
    from PIL import Image
except ImportError:
    Image = None

def decode(data: bytes):
    print("[Decoder] Initializing embedded decoder...")
    print(f"[Decoder] Received {len(data)} bytes of media data.")
    
    if Image is None:
        print("[Decoder] Error: PIL (Pillow) library not found. Cannot decode.")
        return None

    try:
        # Create a BytesIO object to simulate a file
        image_stream = io.BytesIO(data)
        
        # Open the image using PIL
        img = Image.open(image_stream)
        
        # Force loading the image data
        img.load()
        
        print(f"[Decoder] Successfully decoded image.")
        print(f"[Decoder] Format: {img.format}, Size: {img.size}, Mode: {img.mode}")
        
        return img
    except Exception as e:
        print(f"[Decoder] Error decoding image: {e}")
        return None
