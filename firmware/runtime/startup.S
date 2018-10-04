.global _boot
.global _start
.global data_abort_handler

.global _vector_table
.global MMUTable

.set vector_base, _vector_table

.set TblBase, MMUTable
.set UncachableStart, __uncachable_start
.set UncachableEnd, __uncachable_end
.set CRValMmuCac,   0b01000000000101    /* Enable IDC, and MMU */

.set PSS_SLCR_BASE_ADDR, 0xF8000000
.set PSS_L2CC_BASE_ADDR, 0xF8F02000

.set L2CCWay,       (PSS_L2CC_BASE_ADDR + 0x077C)   /*(PSS_L2CC_BASE_ADDR + PSS_L2CC_CACHE_INVLD_WAY_OFFSET)*/
.set L2CCSync,      (PSS_L2CC_BASE_ADDR + 0x0730)   /*(PSS_L2CC_BASE_ADDR + PSS_L2CC_CACHE_SYNC_OFFSET)*/
.set L2CCCrtl,      (PSS_L2CC_BASE_ADDR + 0x0100)   /*(PSS_L2CC_BASE_ADDR + PSS_L2CC_CNTRL_OFFSET)*/
.set L2CCAuxCrtl,   (PSS_L2CC_BASE_ADDR + 0x0104)   /*(PSS_L2CC_BASE_ADDR + XPSS_L2CC_AUX_CNTRL_OFFSET)*/
.set L2CCTAGLatReg, (PSS_L2CC_BASE_ADDR + 0x0108)   /*(PSS_L2CC_BASE_ADDR + XPSS_L2CC_TAG_RAM_CNTRL_OFFSET)*/
.set L2CCDataLatReg,    (PSS_L2CC_BASE_ADDR + 0x010C)   /*(PSS_L2CC_BASE_ADDR + XPSS_L2CC_DATA_RAM_CNTRL_OFFSET)*/
.set L2CCIntClear,  (PSS_L2CC_BASE_ADDR + 0x0220)   /*(PSS_L2CC_BASE_ADDR + XPSS_L2CC_IAR_OFFSET)*/
.set L2CCIntRaw,    (PSS_L2CC_BASE_ADDR + 0x021C)   /*(PSS_L2CC_BASE_ADDR + XPSS_L2CC_ISR_OFFSET)*/
.set L2CCAuxControl,    0x72360000      /* Enable all prefetching, Cache replacement policy, Parity enable,
                                        Event monitor bus enable and Way Size (64 KB) */
.set L2CCControl,   0x01            /* Enable L2CC */
.set L2CCTAGLatency,    0x0111          /* latency for TAG RAM */
.set L2CCDataLatency,   0x0121          /* latency for DATA RAM */
.set SLCRlockReg,       (PSS_SLCR_BASE_ADDR + 0x04) /*(PSS_SLCR_BASE_ADDR + XPSS_SLCR_LOCK_OFFSET)*/
.set SLCRUnlockReg,     (PSS_SLCR_BASE_ADDR + 0x08) /*(PSS_SLCR_BASE_ADDR + XPSS_SLCR_UNLOCK_OFFSET)*/
.set SLCRL2cRamReg,     (PSS_SLCR_BASE_ADDR + 0xA1C) /*(PSS_SLCR_BASE_ADDR + XPSS_SLCR_L2C_RAM_OFFSET)*/
.set SLCRlockKey,           0x767B          /* SLCR lock key */
.set SLCRUnlockKey,         0xDF0D          /* SLCR unlock key */
.set SLCRL2cRamConfig,      0x00020202      /* SLCR L2C ram configuration */


.org 0
.text

.globl _vector_table

.section .vectors
_vector_table:
    B   _boot
    B   Undefined
    B   SVCHandler
    B   PrefetchAbortHandler
    B   DataAbortHandler
    NOP /* Placeholder for address exception vector*/
    B   IRQHandler
    B   FIQHandler


.text

_boot:
    // Read MPIDR to determine processor id
    mrc p15,0,r0,c0,c0,5
    and r0, r0, 0x3
    cmp r0, 0
    // processor 0 -> p0_boot
    // processor 1 waits for interrupt, then goes via p1_boot
    beq p0_start
    ldr r13,.Lstack2     /* stack address */
p1_loop:
    wfi
    b p1_loop
p0_start:

    /* set VBAR to the _vector_table address in linker script */
    ldr r0, =vector_base
    mcr p15, 0, r0, c12, c0, 0

    /*invalidate scu*/
    ldr r7, =0xf8f0000c
    ldr r6, =0xffff
    str r6, [r7]

    /* Invalidate caches and TLBs */
    mov r0,#0               /* r0 = 0  */
    mcr p15, 0, r0, c8, c7, 0       /* invalidate TLBs */
    mcr p15, 0, r0, c7, c5, 0       /* invalidate icache */
    mcr p15, 0, r0, c7, c5, 6       /* Invalidate branch predictor array */
    bl  invalidate_dcache       /* invalidate dcache */

    /* Disable MMU, if enabled */
    mrc p15, 0, r0, c1, c0, 0       /* read CP15 register 1 */
    bic r0, r0, #0x1            /* clear bit 0 */
    mcr p15, 0, r0, c1, c0, 0       /* write value back */

    /* Mark the a section of DDR as uncacheable */
    ldr r3, =UncachableStart
    ldr r4, =UncachableEnd
    ldr r0, =TblBase            /* MMU Table address in memory */
    ldr r2, =0x11de2            /* S=b1 TEX=b001 AP=b11, Domain=b1111, C=b0, B=b0 */
    lsr r5, r3, #18     // Calculate table offset
    add r0, r0, r5      // Address of first table entry to modify
uncacheable_loop:
    add r5, r3, r2
    str r5, [r0]            // write the entry to MMU table
    add r0, r0, #0x4        // next entry in the table
    add r3, r3, #0x100000   // next section
    cmp r3, r4
    blt uncacheable_loop

    /*set scu enable bit in scu*/
    ldr r7, =0xf8f00000
    ldr r0, [r7]
    orr r0, r0, #0x1
    str r0, [r7]

    // enable MMU and cache
    ldr r0,=TblBase         /* Load MMU translation table base */
    orr r0, r0, #0x5B           /* Outer-cacheable, WB */
    mcr p15, 0, r0, c2, c0, 0        /* TTB0 */

    mvn r0,#0               /* Load MMU domains -- all ones=manager */
    mcr p15,0,r0,c3,c0,0

    // Enable mmu, icache and dcache
    ldr r0,=CRValMmuCac
    mcr p15,0,r0,c1,c0,0        /* Enable cache and MMU */
    dsb                 /* dsb  allow the MMU to start up */
    isb                 /* isb  flush prefetch buffer */

    /* Write to ACTLR */
    mrc p15, 0, r0, c1, c0, 1       /* Read ACTLR*/
    orr r0, r0, #(0x01 << 6)        /* set SMP bit */
    orr r0, r0, #(0x01 )        /* Cache/TLB maintenance broadcast */
    mcr p15, 0, r0, c1, c0, 1       /* Write ACTLR*/

/* Invalidate L2 Cache and enable L2 Cache*/
    ldr r0,=L2CCCrtl            /* Load L2CC base address base + control register */
    mov r1, #0              /* force the disable bit */
    str r1, [r0]            /* disable the L2 Caches */

    ldr r0,=L2CCAuxCrtl         /* Load L2CC base address base + Aux control register */
    ldr r1,[r0]             /* read the register */
    ldr r2,=L2CCAuxControl      /* set the default bits */
    orr r1,r1,r2
    str r1, [r0]            /* store the Aux Control Register */

    ldr r0,=L2CCTAGLatReg       /* Load L2CC base address base + TAG Latency address */
    ldr r1,=L2CCTAGLatency      /* set the latencies for the TAG*/
    str r1, [r0]            /* store the TAG Latency register Register */

    ldr r0,=L2CCDataLatReg      /* Load L2CC base address base + Data Latency address */
    ldr r1,=L2CCDataLatency     /* set the latencies for the Data*/
    str r1, [r0]            /* store the Data Latency register Register */

    ldr r0,=L2CCWay         /* Load L2CC base address base + way register*/
    ldr r2, =0xFFFF
    str r2, [r0]            /* force invalidate */

    ldr r0,=L2CCSync            /* need to poll 0x730, PSS_L2CC_CACHE_SYNC_OFFSET */
                        /* Load L2CC base address base + sync register*/
    /* poll for completion */
Sync:   ldr r1, [r0]
    cmp r1, #0
    bne Sync

    ldr r0,=L2CCIntRaw          /* clear pending interrupts */
    ldr r1,[r0]
    ldr r0,=L2CCIntClear
    str r1,[r0]

    ldr r0,=SLCRUnlockReg       /* Load SLCR base address base + unlock register */
    ldr r1,=SLCRUnlockKey           /* set unlock key */
    str r1, [r0]                /* Unlock SLCR */

    ldr r0,=SLCRL2cRamReg       /* Load SLCR base address base + l2c Ram Control register */
    ldr r1,=SLCRL2cRamConfig            /* set the configuration value */
    str r1, [r0]                /* store the L2c Ram Control Register */

    ldr r0,=SLCRlockReg             /* Load SLCR base address base + lock register */
    ldr r1,=SLCRlockKey             /* set lock key */
    str r1, [r0]                /* lock SLCR */

    ldr r0,=L2CCCrtl            /* Load L2CC base address base + control register */
    ldr r1,[r0]             /* read the register */
    mov r2, #L2CCControl        /* set the enable bit */
    orr r1,r1,r2
    str r1, [r0]            /* enable the L2 Caches */
    mov r0,r0

    // Enable CP11 and CP10 access from all processor modes
    mrc p15, 0, r0, c1, c0, 2 // Read CPACR
    orr r0, r0, (0b1111<<20)
    mcr p15, 0, r0, c1, c0, 2

    /* enable vfp */
    vmrs r1, fpexc
    orr r1,r1, (1<<30)
    vmsr fpexc, r1

    mrc p15,0,r0,c1,c0,0        /* flow prediction enable */
    orr r0, r0, #(0x01 << 11)       /* #0x8000 */
    mcr p15,0,r0,c1,c0,0

    mrc p15,0,r0,c1,c0,1        /* read Auxiliary Control Register */
    orr r0, r0, #(0x1 << 2)     /* enable Dside prefetch */
    orr r0, r0, #(0x1 << 1)     /* enable L2 Prefetch hint */
    mcr p15,0,r0,c1,c0,1        /* write Auxiliary Control Register */

    mrs r0, cpsr            /* get the current PSR */
    bic r0, r0, #0x100          /* enable asynchronous abort exception */
    msr cpsr_xsf, r0


    // Enable and reset cycle counter
    mov r0, 0b101
    mcr p15, 0, r0, c9, c12, 0


.Lenclsbss:
    /* clear bss */
    ldr r1,.Lbss_start      /* calculate beginning of the BSS */
    ldr r2,.Lbss_end        /* calculate end of the BSS */

.Lloop_bss:
    cmp r1,r2
    bge .Lenclbss       /* If no BSS, no clearing required */
    str r0, [r1], #4
    b   .Lloop_bss

.Lenclbss:
    /* set stack pointer */
    ldr r13,.Lstack     /* stack address */


    bl main
loop:
    b loop


Undefined:
    ldr r13, .Lstack
    mov r0, lr // address of undefined instruction +8
    b undefined_instruction_handler

SVCHandler:
    b SVCHandler

PrefetchAbortHandler:
    b PrefetchAbortHandler

DataAbortHandler:
    ldr r13, .Lstack
    mov r0, lr // address of aborted instruction +8
    mrc p15, 0, r1, c6, c0, 0 // Read DFAR
    mrc p15, 0, r2, c5, c0, 0 // Read DFSR
    b data_abort_handler

IRQHandler:
    ldr r13, .Lstack
    b irq_handler

FIQHandler:
    b FIQHandler

invalidate_dcache:
    mrc p15, 1, r0, c0, c0, 1       /* read CLIDR */
    ands    r3, r0, #0x7000000
    mov r3, r3, lsr #23         /* cache level value (naturally aligned) */
    beq finished
    mov r10, #0             /* start with level 0 */
loop1:
    add r2, r10, r10, lsr #1        /* work out 3xcachelevel */
    mov r1, r0, lsr r2          /* bottom 3 bits are the Cache type for this level */
    and r1, r1, #7          /* get those 3 bits alone */
    cmp r1, #2
    blt skip                /* no cache or only instruction cache at this level */
    mcr p15, 2, r10, c0, c0, 0      /* write the Cache Size selection register */
    isb                 /* isb to sync the change to the CacheSizeID reg */
    mrc p15, 1, r1, c0, c0, 0       /* reads current Cache Size ID register */
    and r2, r1, #7          /* extract the line length field */
    add r2, r2, #4          /* add 4 for the line length offset (log2 16 bytes) */
    ldr r4, =0x3ff
    ands    r4, r4, r1, lsr #3      /* r4 is the max number on the way size (right aligned) */
    clz r5, r4              /* r5 is the bit position of the way size increment */
    ldr r7, =0x7fff
    ands    r7, r7, r1, lsr #13     /* r7 is the max number of the index size (right aligned) */
loop2:
    mov r9, r4              /* r9 working copy of the max way size (right aligned) */
loop3:
    orr r11, r10, r9, lsl r5        /* factor in the way number and cache number into r11 */
    orr r11, r11, r7, lsl r2        /* factor in the index number */
    mcr p15, 0, r11, c7, c6, 2      /* invalidate by set/way */
    subs    r9, r9, #1          /* decrement the way number */
    bge loop3
    subs    r7, r7, #1          /* decrement the index */
    bge loop2
skip:
    add r10, r10, #2            /* increment the cache number */
    cmp r3, r10
    bgt loop1

finished:
    mov r10, #0             /* swith back to cache level 0 */
    mcr p15, 2, r10, c0, c0, 0      /* select current cache level in cssr */
    dsb
    isb

    bx  lr



.Lbss_start:
    .long   _fbss

.Lbss_end:
    .long   _ebss

.Lstack:
    .long   _fstack

.Lstack2:
    .long   _fstack2