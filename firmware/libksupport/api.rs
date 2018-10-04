macro_rules! api {
    ($i:ident) => ({
        extern { static $i: u8; }
        api!($i = &$i as *const _)
    });
    ($i:ident, $d:item) => ({
        $d
        api!($i = $i)
    });
    ($i:ident = $e:expr) => {
        (stringify!($i), unsafe { $e as *const () })
    }
}


#[allow(unused_unsafe)]
static mut API: &'static [(&'static str, *const ())] = &[
    api!(__divsi3),
    api!(__modsi3),
    api!(__ledf2),
    api!(__gedf2),
    api!(__unorddf2),
    api!(__eqdf2),
    api!(__ltdf2),
    api!(__nedf2),
    api!(__gtdf2),
    api!(__addsf3),
    api!(__subsf3),
    api!(__mulsf3),
    api!(__divsf3),
    api!(__lshrdi3),
    api!(__muldi3),
    api!(__divdi3),
    api!(__ashldi3),
    api!(__ashrdi3),
    api!(__udivmoddi4),
    api!(__floatsisf),
    api!(__floatunsisf),
    api!(__fixsfsi),
    api!(__fixunssfsi),
    api!(__adddf3),
    api!(__subdf3),
    api!(__muldf3),
    api!(__divdf3),
    api!(__floatsidf),
    api!(__floatunsidf),
    api!(__floatdidf),
    api!(__fixdfsi),
    api!(__fixdfdi),
    api!(__fixunsdfsi),
    api!(__udivdi3),
    api!(__umoddi3),
    api!(__moddi3),
    api!(__powidf2),

    /* libc */
    // api!(abort = ::abort),
    api!(memcmp, extern { fn memcmp(a: *const u8, b: *mut u8, size: usize); }),

    /* libm */
    api!(sqrt),
    api!(round),
    api!(floor),

    /* exceptions */
    api!(_Unwind_Resume = ::unwind::_Unwind_Resume),
    api!(__artiq_personality = ::eh::personality),
    api!(__artiq_raise = ::eh::raise),
    api!(__artiq_reraise = ::eh::reraise),

    /* proxified syscalls */
    api!(core_log),

    api!(now = &::NOW as *const _),


    /* direct syscalls */
    api!(rtio_init = ::rtio::init),
    api!(rtio_get_counter = ::rtio::get_counter),
    api!(rtio_log),
    api!(rtio_output = ::rtio::output),
    api!(rtio_output_wide = ::rtio::output_wide),
    api!(rtio_input_timestamp = ::rtio::input_timestamp),
    api!(rtio_input_data = ::rtio::input_data),
    api!(rtio_input_data_timeout = ::rtio::input_data_timeout),
    api!(rtio_input_timestamp_data = ::rtio::input_timestamp_data),

];

