use std::io::Cursor;
use std::mem;
use dicom_object::OpenFileOptions;
use dicom_pixeldata::PixelDecoder;
use std::str;

// Global state to hold the decoded image data so the host can retrieve it
static mut DECODED_PIXELS: Option<Vec<u8>> = None;
static mut WIDTH: u32 = 0;
static mut HEIGHT: u32 = 0;

#[no_mangle]
pub extern "C" fn alloc(size: usize) -> *mut u8 {
    let mut buf = Vec::with_capacity(size);
    let ptr = buf.as_mut_ptr();
    mem::forget(buf);
    ptr
}

#[no_mangle]
pub extern "C" fn dealloc(ptr: *mut u8, size: usize) {
    unsafe {
        let _ = Vec::from_raw_parts(ptr, size, size);
    }
}

#[no_mangle]
pub extern "C" fn decode(ptr: *const u8, len: usize, params_ptr: *const u8, params_len: usize) -> i32 {
    // Safety: We assume the host passes a valid pointer and length
    let data = unsafe { std::slice::from_raw_parts(ptr, len) };
    let params_slice = unsafe { std::slice::from_raw_parts(params_ptr, params_len) };
    let params_str = str::from_utf8(params_slice).unwrap_or("");
    
    println!("[Wasm Dicom Decoder] Starting decoding with params: \"{}\"", params_str);

    // Try to decode the DICOM from memory
    let cursor = Cursor::new(data);
    
    // Parse DICOM object from the reader (cursor)
    let obj = match OpenFileOptions::new().from_reader(cursor) {
        Ok(obj) => obj,
        Err(e) => {
            println!("[Wasm Dicom Decoder] Failed to parse DICOM: {:?}", e);
            return 1;
        }
    };

    println!("[Wasm Dicom Decoder] DICOM object parsed successfully.");
    
    let mut dynamic_image = match obj.decode_pixel_data() {
        Ok(d) => match d.to_dynamic_image(0) {
            Ok(img) => img,
            Err(e) => {
                 println!("[Wasm Dicom Decoder] Failed to convert to DynamicImage: {:?}", e);
                 return 2;
            }
        },
        Err(e) => {
            println!("[Wasm Dicom Decoder] Failed to decode pixel data: {:?}", e);
            return 3;
        }
    };

    // Apply parameters if requested
    if params_str.contains("invert=true") {
        println!("[Wasm Dicom Decoder] Processing: Inverting image colors...");
        dynamic_image.invert();
    }

    println!("[Wasm Dicom Decoder] Converted to DynamicImage.");

    // Convert to RGB8 for the host
    let rgb = dynamic_image.to_rgb8();
    
    unsafe {
        WIDTH = rgb.width();
        HEIGHT = rgb.height();
        println!("[Wasm Dicom Decoder] Dimensions: {}x{}", WIDTH, HEIGHT);
        DECODED_PIXELS = Some(rgb.into_raw());
    }

    0
}

#[no_mangle]
pub extern "C" fn get_width() -> u32 {
    unsafe { WIDTH }
}

#[no_mangle]
pub extern "C" fn get_height() -> u32 {
    unsafe { HEIGHT }
}

#[no_mangle]
pub extern "C" fn get_output_ptr() -> *const u8 {
    unsafe {
        match &DECODED_PIXELS {
            Some(vec) => vec.as_ptr(),
            None => std::ptr::null(),
        }
    }
}

#[no_mangle]
pub extern "C" fn get_output_len() -> usize {
    unsafe {
        match &DECODED_PIXELS {
            Some(vec) => vec.len(),
            None => 0,
        }
    }
}
