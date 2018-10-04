#!/usr/bin/env python

import subprocess
import argparse

def build_experiment(exp, dev_db=None):
    output = "firmware/runtime/exp.a"
    if not dev_db:
        dev_db = "experiments/device_db.py"
    subprocess.run(["artiq_compile", "--target", "zynq", "--static", "-o", output, "--device-db", dev_db, exp])

def build_firmware():
    subprocess.run(["python", "zedboard.py", "--no-compile-gateware"])

def load():
    subprocess.run(["./load.py", "firmware", "run"])

parser = argparse.ArgumentParser()
parser.add_argument("path")
args = parser.parse_args()

build_experiment(args.path)
build_firmware()
load()
