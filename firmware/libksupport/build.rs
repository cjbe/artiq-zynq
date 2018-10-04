extern crate cc;


fn main() {
    let glue_path = "glue.c";

    println!("cargo:rerun-if-changed={}", glue_path);

    cc::Build::new()
        .file(glue_path)
        .compile("glue");
}
