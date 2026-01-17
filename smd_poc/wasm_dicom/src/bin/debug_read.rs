use std::fs::File;
use dicom_object::OpenFileOptions;

fn main() {
    let path = "../sample.dcm";
    println!("Reading {}", path);
    
    let f = File::open(path).expect("File not found");
    match OpenFileOptions::new().from_reader(f) {
        Ok(_) => println!("Success! Parsed DICOM object."),
        Err(e) => println!("Error parsing DICOM: {:?}", e),
    }
}
