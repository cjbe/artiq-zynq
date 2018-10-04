

use core::ptr::{read_volatile, write_volatile};
use cslice::CSlice;
use board_misoc::csr;

use volatile_cell::VolatileCell;

pub const RTIO_O_STATUS_WAIT:           u8 = 1;
pub const RTIO_O_STATUS_UNDERFLOW:      u8 = 2;
pub const RTIO_O_STATUS_LINK_ERROR:     u8 = 4;
pub const RTIO_I_STATUS_WAIT_EVENT:     u8 = 1;
pub const RTIO_I_STATUS_OVERFLOW:       u8 = 2;
pub const RTIO_I_STATUS_WAIT_STATUS:    u8 = 4;
pub const RTIO_I_STATUS_LINK_ERROR:     u8 = 8;

#[repr(C)]
struct RtioCmd {
    cmd_channel: i32,
    address: i32,
    timestamp: i64,
    data: i64
}

#[repr(C)]
struct RtioResponse {
    status: VolatileCell<i32>,
    data: VolatileCell<i32>,
    timestamp: VolatileCell<u64>
}

pub const DMA_BASE: isize = 0x200000;



#[no_mangle]
pub extern fn rtio_init() {
    unsafe {
        csr::rtio_core::reset_write(1);
        csr::rtio_core::reset_phy_write(1);
    }
}

#[no_mangle]
pub extern fn rtio_get_counter() -> i64 {
    unsafe {
        csr::rtio::counter_update_write(1);
        csr::rtio::counter_read() as i64
    }
}

#[inline(always)]
pub unsafe fn rtio_o_data_write(offset: usize, data: u32) {
    write_volatile(
        csr::rtio::O_DATA_ADDR.offset((csr::rtio::O_DATA_SIZE - 1 - offset) as isize),
        data);
}

#[inline(always)]
pub unsafe fn rtio_i_data_read(offset: usize) -> u32 {
    read_volatile(
        csr::rtio::I_DATA_ADDR.offset((csr::rtio::I_DATA_SIZE - 1 - offset) as isize))
}

#[inline(never)]
unsafe fn process_exceptional_status(timestamp: i64, channel: i32, status: u8) {
    if status & RTIO_O_STATUS_WAIT != 0 {
        while csr::rtio::o_status_read() & RTIO_O_STATUS_WAIT != 0 {}
    }
    if status & RTIO_O_STATUS_UNDERFLOW != 0 {
        raise!("RTIOUnderflow",
            "RTIO underflow at {0} mu, channel {1}, slack {2} mu",
            timestamp, channel as i64, timestamp - rtio_get_counter());
    }
    if status & RTIO_O_STATUS_LINK_ERROR != 0 {
        raise!("RTIOLinkError",
            "RTIO output link error at {0} mu, channel {1}",
            timestamp, channel as i64, 0);
    }
}

#[no_mangle]
pub extern fn rtio_output_csr(timestamp: i64, channel: i32, addr: i32, data: i32) {
    unsafe {
        csr::rtio::chan_sel_write(channel as _);
        // writing timestamp clears o_data
        csr::rtio::timestamp_write(timestamp as u64);
        csr::rtio::o_address_write(addr as _);
        rtio_o_data_write(0, data as _);
        csr::rtio::o_we_write(1);
        let status = csr::rtio::o_status_read();
        if status != 0 {
            process_exceptional_status(timestamp, channel, status);
        }
    }
}

#[no_mangle]
pub extern fn rtio_output(timestamp: i64, channel: i32, address: i32, data: i32) {
    unsafe {
        let rtio_cmd: *mut RtioCmd = DMA_BASE as *mut _;
        let rtio_response: *mut RtioResponse = (DMA_BASE+0x20) as *mut _;

        // Clear status so we can observe response
        (*rtio_response).status.set(0);

        (*rtio_cmd).cmd_channel = (0<<24) | channel;
        (*rtio_cmd).address = address;
        (*rtio_cmd).timestamp = timestamp;
        (*rtio_cmd).data = data as i64;

        asm!("dmb");
        asm!("sev");

        let mut status;
        loop {
            status = (*rtio_response).status.get();
            if status != 0 {break}
        }
        
        let status = status & !0x10000;
        if status != 0 {process_exceptional_status(timestamp, channel, status as u8)}
    }
}

#[no_mangle]
pub extern fn rtio_input_timestamp(timestamp: i64, channel: i32) -> u64 {
    unsafe {
        let rtio_cmd: *mut RtioCmd = DMA_BASE as *mut _;
        let rtio_response: *mut RtioResponse = (DMA_BASE+0x20) as *mut _;

        // Clear status so we can observe response
        (*rtio_response).status.set(0);

        (*rtio_cmd).cmd_channel = (1<<24) | channel;
        (*rtio_cmd).timestamp = timestamp;

        asm!("dmb");
        asm!("sev");

        let mut status;
        loop {
            status = (*rtio_response).status.get();
            if status != 0 {break}
        }
        
        let status = status & !0x10000;
        let status = status as u8;

        if status & RTIO_I_STATUS_OVERFLOW != 0 {
            csr::cri_con::selected_write(0);
            csr::rtio::i_overflow_reset_write(1);
            csr::cri_con::selected_write(1);
            raise!("RTIOOverflow",
                "RTIO input overflow on channel {0}",
                channel as i64, 0, 0);
        }
        if status & RTIO_I_STATUS_WAIT_EVENT != 0 {
            return !0
        }
        if status & RTIO_I_STATUS_LINK_ERROR != 0 {
            raise!("RTIOLinkError",
                "RTIO input link error on channel {0}",
                channel as i64, 0, 0);
        }

        (*rtio_response).timestamp.get()
    }
}




#[no_mangle]
pub extern fn output_wide(timestamp: i64, channel: i32, addr: i32, data: CSlice<i32>) {
    unsafe {
        csr::rtio::chan_sel_write(channel as _);
        // writing timestamp clears o_data
        csr::rtio::timestamp_write(timestamp as u64);
        csr::rtio::o_address_write(addr as _);
        for i in 0..data.len() {
            rtio_o_data_write(i, data[i] as _)
        }
        csr::rtio::o_we_write(1);
        let status = csr::rtio::o_status_read();
        if status != 0 {
            process_exceptional_status(timestamp, channel, status);
        }
    }
}

#[no_mangle]
pub extern fn rtio_input_timestamp_csr(timeout: i64, channel: i32) -> u64 {
    unsafe {
        csr::rtio::chan_sel_write(channel as _);
        csr::rtio::timestamp_write(timeout as u64);
        csr::rtio::i_request_write(1);

        let mut status = RTIO_I_STATUS_WAIT_STATUS;
        while status & RTIO_I_STATUS_WAIT_STATUS != 0 {
            status = csr::rtio::i_status_read();
        }

        if status & RTIO_I_STATUS_OVERFLOW != 0 {
            csr::rtio::i_overflow_reset_write(1);
            raise!("RTIOOverflow",
                "RTIO input overflow on channel {0}",
                channel as i64, 0, 0);
        }
        if status & RTIO_I_STATUS_WAIT_EVENT != 0 {
            return !0
        }
        if status & RTIO_I_STATUS_LINK_ERROR != 0 {
            raise!("RTIOLinkError",
                "RTIO input link error on channel {0}",
                channel as i64, 0, 0);
        }

        csr::rtio::i_timestamp_read()
    }
}

#[no_mangle]
pub extern fn rtio_input_data(channel: i32) -> i32 {
    unsafe {
        csr::rtio::chan_sel_write(channel as _);
        csr::rtio::timestamp_write(0xffffffff_ffffffff);
        csr::rtio::i_request_write(1);

        let mut status = RTIO_I_STATUS_WAIT_STATUS;
        while status & RTIO_I_STATUS_WAIT_STATUS != 0 {
            status = csr::rtio::i_status_read();
        }

        if status & RTIO_I_STATUS_OVERFLOW != 0 {
            csr::rtio::i_overflow_reset_write(1);
            raise!("RTIOOverflow",
                "RTIO input overflow on channel {0}",
                channel as i64, 0, 0);
        }
        if status & RTIO_I_STATUS_LINK_ERROR != 0 {
            raise!("RTIOLinkError",
                "RTIO input link error on channel {0}",
                channel as i64, 0, 0);
        }

        rtio_i_data_read(0) as i32
    }
}

#[no_mangle]
pub extern fn rtio_input_data_timeout(timeout: i64, channel: i32) -> i32 {
    unsafe {
        csr::rtio::chan_sel_write(channel as _);
        csr::rtio::timestamp_write(timeout as u64);
        csr::rtio::i_request_write(1);

        let mut status = RTIO_I_STATUS_WAIT_STATUS;
        while status & RTIO_I_STATUS_WAIT_STATUS != 0 {
            status = csr::rtio::i_status_read();
        }

        if status & RTIO_I_STATUS_OVERFLOW != 0 {
            csr::rtio::i_overflow_reset_write(1);
            raise!("RTIOOverflow",
                "RTIO input overflow on channel {0}",
                channel as i64, 0, 0);
        }

        if status & RTIO_I_STATUS_WAIT_EVENT != 0 {
            return !0
        }

        rtio_i_data_read(0) as i32
    }
}


#[repr(C)]
pub struct TimestampData {
    timestamp: u64,
    data:  i32,
}

pub extern fn input_timestamp_data(channel: i32) -> TimestampData {
    unsafe {
        csr::rtio::chan_sel_write(channel as _);
        csr::rtio::timestamp_write(0xffffffff_ffffffff);
        csr::rtio::i_request_write(1);

        let mut status = RTIO_I_STATUS_WAIT_STATUS;
        while status & RTIO_I_STATUS_WAIT_STATUS != 0 {
            status = csr::rtio::i_status_read();
        }

        if status & RTIO_I_STATUS_OVERFLOW != 0 {
            csr::rtio::i_overflow_reset_write(1);
            println!("RTIO input overflow on channel {0}",channel as i64);
        }


        TimestampData {
            timestamp:  csr::rtio::i_timestamp_read(),
            data: rtio_i_data_read(0) as i32
        }
    }
}


#[cfg(has_rtio_log)]
pub fn log(timestamp: i64, data: &[u8]) {
    unsafe {
        csr::rtio::chan_sel_write(csr::CONFIG_RTIO_LOG_CHANNEL);
        csr::rtio::timestamp_write(timestamp as u64);

        let mut word: u32 = 0;
        for i in 0..data.len() {
            word <<= 8;
            word |= data[i] as u32;
            if i % 4 == 3 {
                rtio_o_data_write(0, word);
                csr::rtio::o_we_write(1);
                word = 0;
            }
        }

        if word != 0 {
            rtio_o_data_write(0, word);
            csr::rtio::o_we_write(1);
        }
    }
}

#[cfg(not(has_rtio_log))]
pub fn log(_timestamp: i64, _data: &[u8]) {
    unimplemented!("not(has_rtio_log)")
}
