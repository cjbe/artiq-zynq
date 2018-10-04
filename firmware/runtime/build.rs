extern crate cc;


fn main() {
    let startup_path = "startup.S";
    let table_path = "translation_table.S";

    println!("cargo:rerun-if-changed={}", startup_path);
    println!("cargo:rerun-if-changed={}", table_path);

    cc::Build::new()
        .file(startup_path)
        .compile("startup");
    cc::Build::new()
        .file(table_path)
        .compile("translation_table");
}
