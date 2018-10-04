#![no_std]
#![feature(asm)]

include!(concat!(env!("BUILDINC_DIRECTORY"), "/generated/csr.rs"));

pub mod uart;
#[macro_use]
pub mod uart_console;

// Clean = expunge cache line with writeback
pub fn clean_data_cache(base: usize, len: usize) {
    const CACHE_SYNC_OFFSET: isize = 0x0730/4; // Cache Sync
    const CACHE_CLEAN_PA_OFFSET: isize = 0x7B0/4;
    const L2CC_BASE: *mut u32 = 0xF8F02000 as *mut u32;
    const CACHE_LINE_LENGTH: usize = 32;
    let mut addr = base & !(CACHE_LINE_LENGTH-1); 
    loop {
        if addr > base+len {break}
        unsafe {
            write_volatile(L2CC_BASE.offset(CACHE_CLEAN_PA_OFFSET), addr as u32);
            write_volatile(L2CC_BASE.offset(CACHE_SYNC_OFFSET), 0);

            // Clean data cache line by virtual address
            asm!("mcr p15, 0, $0, c7, c10, 1"::"r"(addr))
        }
        addr += CACHE_LINE_LENGTH;
    }
}


use core::ptr::write_volatile;

// Invalidate = expunge cache line without writeback
pub fn invalidate_data_cache(base: usize, len: usize) {
    const CACHE_SYNC_OFFSET: isize = 0x0730/4; // Cache Sync
    const CACHE_INVLD_PA_OFFSET: isize = 0x0770/4; // Cache Invalid by PA
    const L2CC_BASE: *mut u32 = 0xF8F02000 as *mut u32;
    const CACHE_LINE_LENGTH: usize = 32;

    let mut addr = base & !(CACHE_LINE_LENGTH-1); 
    loop {
        if addr > base+len {break}

        unsafe {
            write_volatile(L2CC_BASE.offset(CACHE_INVLD_PA_OFFSET), addr as u32);
            write_volatile(L2CC_BASE.offset(CACHE_SYNC_OFFSET), 0);

            // Invalidate data cache line by virtual address
            asm!("mcr p15, 0, $0, c7, c6, 1"::"r"(addr))
        }
        addr += CACHE_LINE_LENGTH;
    }
}



