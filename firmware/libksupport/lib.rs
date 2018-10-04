#![feature(lang_items, asm, libc, panic_unwind, unwind_attributes, global_allocator,
           needs_panic_runtime)]
#![no_std]

extern crate unwind;
extern crate libc;
extern crate cslice;
#[macro_use]
extern crate board_misoc;
extern crate volatile_cell;

use cslice::CSlice;
use core::str;

#[no_mangle]
pub static mut now: u64 = 0;

pub mod eh;

#[no_mangle]
pub extern fn send_to_core_log(text: CSlice<u8>) {
    match str::from_utf8(text.as_ref()) {
        Ok(s) => print!("{}", s),
        Err(_e) => println!("kernel send invalid utf8")
    }
}

fn terminate(exception: &eh::Exception, backtrace: &mut [usize]) -> ! {
    print!("Uncaught exception");
  //    at {}:{}: {}({})",
		// str::from_utf8(exception.file.as_ref()).unwrap(),
  //       exception.line,
  //       str::from_utf8(exception.name.as_ref()).unwrap(),
  //       str::from_utf8(exception.message.as_ref()).unwrap());
    loop {}
}

macro_rules! raise {
    ($name:expr, $message:expr, $param0:expr, $param1:expr, $param2:expr) => ({
        use cslice::AsCSlice;
        let exn = $crate::eh::Exception {
            name:     concat!("0:artiq.coredevice.exceptions.", $name).as_bytes().as_c_slice(),
            file:     file!().as_bytes().as_c_slice(),
            line:     line!(),
            column:   column!(),
            // https://github.com/rust-lang/rfcs/pull/1719
            function: "(Rust function)".as_bytes().as_c_slice(),
            message:  $message.as_bytes().as_c_slice(),
            param:    [$param0, $param1, $param2]
        };
        #[allow(unused_unsafe)]
        unsafe { $crate::eh::raise(&exn) }
    });
    ($name:expr, $message:expr) => ({
        raise!($name, $message, 0, 0, 0)
    });
}

pub mod rtio;
