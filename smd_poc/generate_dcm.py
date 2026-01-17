import urllib.request
import os
import ssl

def create_sample_dcm(filename):
    url = "https://raw.githubusercontent.com/rordenlab/dcm2niix/master/console/test_data/dcm/1.dcm"
    
    # Ignore SSL errors
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"Downloading sample DICOM from {url}...")
    try:
        if os.path.exists(filename):
            os.remove(filename)
            
        with urllib.request.urlopen(url, context=ctx) as response, open(filename, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        
        with open(filename, 'rb') as f:
            f.seek(128)
            magic = f.read(4)
            if magic == b"DICM":
                print(f"Success! Downloaded valid DICOM to {filename}")
            else:
                print(f"Warning: Downloaded file does not have DICM magic header.")
    except Exception as e:
        print(f"Failed to download: {e}")

if __name__ == "__main__":
    create_sample_dcm("sample.dcm")
