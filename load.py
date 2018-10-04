#!/usr/bin/env python

import argparse
import tempfile
import os
import subprocess


header_template = \
"""
source [find interface/ftdi/digilent_jtag_smt2.cfg]
adapter_khz 10000

set PL_TAPID 0x03727093
set SMP 1

source {cfg_dir}/zynq-7000.cfg
source {cfg_dir}/xilinx-tcl.cfg
source {cfg_dir}/ps7_init.tcl

reset_config srst_only srst_push_pull

set XC7_JSHUTDOWN 0x0d
set XC7_JPROGRAM 0x0b
set XC7_JSTART 0x0c
set XC7_BYPASS 0x3f

proc xc7_program {{tap}} {{
    global XC7_JSHUTDOWN XC7_JPROGRAM XC7_JSTART XC7_BYPASS
    irscan $tap $XC7_JSHUTDOWN
    irscan $tap $XC7_JPROGRAM
    runtest 60000
    #JSTART prevents this from working...
    #irscan $tap $XC7_JSTART
    runtest 2000
    irscan $tap $XC7_BYPASS
    runtest 2000
}}

pld device virtex2 zynq.tap 1
init
xc7_program zynq.tap

xilinx_ps7_init

# Disable MMU
targets $_TARGETNAME_1
arm mcr 15 0 1 0 0 [expr [arm mrc 15 0 1 0 0] & ~0xd]
targets $_TARGETNAME_0
arm mcr 15 0 1 0 0 [expr [arm mrc 15 0 1 0 0] & ~0xd]
"""


def get_argparser():
    parser = argparse.ArgumentParser()

    parser.add_argument("action", nargs="*",
                        default="gateware firmware run stop".split())
    return parser


def main():
    args = get_argparser().parse_args()

    with tempfile.NamedTemporaryFile(delete=False) as f:
        cfg_file = f.name

        cfg_dir = os.path.dirname(os.path.realpath(__file__))
        header = header_template.format(cfg_dir=cfg_dir)
        f.write(header.encode())

        if "firmware" in args.action:
            f.write(b"load_image misoc_zedboard_zedboard/software/runtime/runtime.bin 0x100000 bin\n")
        if "gateware" in args.action:
            f.write(b"pld load 0 misoc_zedboard_zedboard/gateware/top.bit\n")
        if "run" in args.action:
            f.write(b"targets $_TARGETNAME_1\nreg pc 0x100000\n")
            f.write(b"targets $_TARGETNAME_0\nresume 0x100000\n")
        if "stop" in args.action:
            f.write(b"sleep 2000\n")
            f.write(b"targets $_TARGETNAME_0\nhalt\nreg\n")
#            f.write(b"targets $_TARGETNAME_1\nhalt\nreg\n")

        if not ("noexit" in args.action):
            f.write(b"exit\n")

    subprocess.run(["openocd", "-f", cfg_file])

if __name__=="__main__":
    main()
