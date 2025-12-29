use std::io::Cursor;
use image::io::Reader as ImageReader;
use std::mem;

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
    let params = if params_len > 0 {
        unsafe { std::slice::from_raw_parts(params_ptr, params_len) }
    } else {
        &[]
    };
    
    println!("[Wasm Decoder] *** HELLO FROM INSIDE THE WASM SANDBOX! ***");
    println!("[Wasm Decoder] I am the one decoding this JPEG.");
    println!("[Wasm Decoder] Received {} bytes of media.", len);

    if !params.is_empty() {
        if let Ok(param_str) = std::str::from_utf8(params) {
            println!("[Wasm Decoder] Received parameters: {}", param_str);
            // TODO: Implement conditional decoding based on param_str
            // e.g., if param_str == "view=left", crop left half
        }
    }

    // Try to decode the image from memory
    let cursor = Cursor::new(data);
    let reader = match ImageReader::new(cursor).with_guessed_format() {
        Ok(r) => r,
        Err(_) => {
            println!("[Wasm Decoder] Failed to guess format.");
            return -1;
        }
    };

    let format = reader.format();
    println!("[Wasm Decoder] Detected format: {:?}", format);

    match reader.decode() {
        Ok(img) => {
            println!("[Wasm Decoder] Successfully decoded image!");
            println!("[Wasm Decoder] Dimensions: {}x{}", img.width(), img.height());
            println!("[Wasm Decoder] Color Type: {:?}", img.color());
            
            // Convert to RGB8 to have a standard format for the host
            let rgb = img.to_rgb8();
            unsafe {
                WIDTH = rgb.width();
                HEIGHT = rgb.height();
                DECODED_PIXELS = Some(rgb.into_raw());
            }
            
            return 0; // Success
        }
        Err(e) => {
            println!("[Wasm Decoder] Error decoding: {:?}", e);
            return -1; // Error
        }
    }
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
