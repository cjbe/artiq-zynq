use core::ptr::{read_volatile, write_volatile};


pub const UART_BASE: *mut u32 = 0xE0001000 as *mut u32;
// pub const UART_BASE: *mut u32 = 0x101000 as *mut u32;


#[export_name="uart_write"]
pub extern fn write(c: u8) {
	unsafe {
	    while read_volatile(UART_BASE.offset(0x2c/4)) & 0x10 != 0 {}
	    write_volatile(UART_BASE.offset(0x30/4), c as u32);
	}
}