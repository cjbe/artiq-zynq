
ENTRY(_boot)

MEMORY {
    runtime (RWX) : ORIGIN = 0x100000, LENGTH = 0x1FF00000
}

SECTIONS
{
    .text :
    {
        *(.vectors)
        *(.text .text.*)
    } > runtime

    .ARM.extab : {
        *(.ARM.extab*)
        *(.gnu.linkonce.armextab.*)
    } > runtime

    .ARM.exidx : {
       __exidx_start = .;
       *(.ARM.exidx*)
       *(.gnu.linkonce.armexidix.*.*)
       __exidx_end = .;
    } > runtime

    /* https://sourceware.org/bugzilla/show_bug.cgi?id=20475 */
    .got :
    {
        _GLOBAL_OFFSET_TABLE_ = .;
        *(.got)
    } > runtime

    .got.plt :
    {
        *(.got.plt)
    } > runtime

    .rodata ALIGN(4):
    {
        *(.rodata .rodata.*)
    } > runtime

    .data ALIGN(4):
    {
        *(.data .data.*)
    } > runtime

    .bss ALIGN(4) :
    {
        _fbss = .;
        *(.bss .bss.*)
        _ebss = .;
    } > runtime

    .stack ALIGN(0x1000) :
    {
        . += 0x4000;
        _fstack = . - 4;
    } > runtime

    .stack2 ALIGN(0x1000) :
    {
        . += 0x4000;
        _fstack2 = . - 4;
    } > runtime

    .mmu_tbl (ALIGN(16384)) :
    {
        __mmu_tbl_start = .;
        *(.mmu_tbl)
        __mmu_tbl_end = .;
    } > runtime


    .uncachable ALIGN(0x100000) :
    {
        __uncachable_start = .;
        *(.uncachable)
        __uncachable_end = .;
    } > runtime
}
