#![no_std]
#![feature(panic_implementation, lang_items, asm)]
#[allow(unused_imports)]

#[macro_use]
extern crate board_misoc;
extern crate ksupport;

extern {
    // Statically linked python module entry point
    fn __modinit__();
}


#[inline(never)]
pub fn get_cycle_counter() -> u32 {
    let n: u32;
    unsafe{asm!("mrc p15, 0, $0, c9, c13, 0": "=r"(n) ::: "volatile");}
    n
}


use board_misoc::csr;
unsafe fn crg_init() {
    csr::rtio_crg::pll_reset_write(1);
    csr::rtio_crg::pll_reset_write(0);

    println!("Waiting on PLL lock ... ");
    while csr::rtio_crg::pll_locked_read() == 0 {}
    println!("PLL locked.\n");
}


#[no_mangle]
pub extern "C" fn main() -> ! {
    println!("");
    println!("");
    println!("-----------------");
    println!("Artiq-Zynq lashup");

    unsafe{
        csr::dma::addr_base_write(0x200000 as u32);
        csr::cri_con::selected_write(1);
        crg_init();
    }


    println!("Starting kernel...");
    println!("--");
    unsafe{ __modinit__() }
    println!("--");
    println!("Kernel finished");

    loop {}
}



#[no_mangle]
pub extern "C" fn data_abort_handler(abort_addr: u32, access_addr: u32, data_fault_status: u32) -> ! {
    println!("!!! Data abort");
    println!("PC = {:08x}", abort_addr-0x8);
    println!("Access addr = {:08x}", access_addr);
    println!("DFSR = {:08x}", data_fault_status);
    loop {}
}

#[no_mangle]
pub extern "C" fn undefined_instruction_handler(abort_addr: u32) -> ! {
    println!("!!! Undefined instruction");
    println!("PC = {:08x}", abort_addr-0x4);
    loop {}
}

#[no_mangle]
pub extern "C" fn irq_handler() -> ! {
    println!("!!! IRQ");
    loop {}
}

#[no_mangle]
#[lang = "eh_personality"] pub extern fn eh_personality() {}

use core::panic::PanicInfo;

// This function is called on panic (including failed assertions, ...).
#[panic_implementation]
#[no_mangle]
pub fn panic(info: &PanicInfo) -> ! {
    println!("kernel {}", info);
    loop {}
}
