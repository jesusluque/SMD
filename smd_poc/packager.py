import struct
import uuid
import hashlib
import sys
import os

def create_atom(image_path, decoder_path, output_path, media_type="image", attributes=""):
    # 1. Read Media Data
    with open(image_path, 'rb') as f:
        media_data = f.read()
    
    # 2. Read Decoder Logic
    with open(decoder_path, 'rb') as f:
        logic_payload = f.read()
    
    # 3. Construct Metadata
    atom_uuid = uuid.uuid4().bytes
    source_uuid = uuid.uuid4().bytes # Dummy for PoC
    origin_uuid = uuid.uuid4().bytes # Dummy for PoC
    start_time = 0.0
    duration = 5.0 # 5 seconds dummy duration
    
    logic_version = 1
    logic_fingerprint = hashlib.sha256(logic_payload).digest()
    
    media_type_bytes = media_type.encode('utf-8')
    attributes_bytes = attributes.encode('utf-8')
    
    # 4. Build Binary Structure
    # Format:
    # [Sequence Header]
    #   AtomUUID (16s)
    #   SourceUUID (16s)
    #   OriginUUID (16s)
    #   StartTime (d)
    #   Duration (d)
    # [Media Descriptor]
    #   MediaTypeLength (I)
    #   MediaType (bytes)
    #   AttributesLength (I)
    #   Attributes (bytes)
    # [Logic Identity]
    #   Version (I)
    #   Fingerprint (32s)
    #   PayloadSize (I)
    #   Payload (bytes)
    # [Media Data]
    #   MediaSize (I)
    #   MediaData (bytes)
    
    # Note: struct.pack format strings
    
    with open(output_path, 'wb') as f:
        # Sequence Header
        f.write(atom_uuid)
        f.write(source_uuid)
        f.write(origin_uuid)
        f.write(struct.pack('>d', start_time))
        f.write(struct.pack('>d', duration))
        
        # Media Descriptor
        f.write(struct.pack('>I', len(media_type_bytes)))
        f.write(media_type_bytes)
        f.write(struct.pack('>I', len(attributes_bytes)))
        f.write(attributes_bytes)
        
        # Logic Identity
        f.write(struct.pack('>I', logic_version))
        f.write(logic_fingerprint)
        f.write(struct.pack('>I', len(logic_payload)))
        f.write(logic_payload)
        
        # Media Data
        f.write(struct.pack('>I', len(media_data)))
        f.write(media_data)
        
    print(f"Successfully created SMD Atom: {output_path}")
    print(f"  - Atom UUID: {uuid.UUID(bytes=atom_uuid)}")
    print(f"  - Media Type: {media_type}")
    print(f"  - Attributes: {attributes}")
    print(f"  - Logic Size: {len(logic_payload)} bytes")
    print(f"  - Media Size: {len(media_data)} bytes")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python packager.py <image.jpg> <decoder.py> <output.smd> [media_type] [attributes]")
        sys.exit(1)
    
    m_type = sys.argv[4] if len(sys.argv) > 4 else "image"
    attrs = sys.argv[5] if len(sys.argv) > 5 else ""
    
    create_atom(sys.argv[1], sys.argv[2], sys.argv[3], m_type, attrs)
