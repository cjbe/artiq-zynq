include ../include/generated/variables.mak
include $(MISOC_DIRECTORY)/software/common.mak
 

LDFLAGS += --eh-frame-hdr \
	-L../libm \
	-L../libprintf \
	-L../libunwind \
	--start-group

RUSTFLAGS += -Cpanic=unwind


all:: runtime.bin

.PHONY: $(RUSTOUT)/libruntime.a 
$(RUSTOUT)/libruntime.a:
	$(cargo) --manifest-path $(RUNTIME_DIRECTORY)/Cargo.toml

runtime.elf: $(RUSTOUT)/libruntime.a $(RUNTIME_DIRECTORY)/exp.a ../libunwind/libunwind-bare.a
	$(link) -T $(RUNTIME_DIRECTORY)/lscript.ld -lprintf-float -lm $(BUILDINC_DIRECTORY)/../libbase/libbase.a -lunwind-bare --target2=abs

%.bin: %.elf
	$(objcopy) -O binary -R .uncachable

%.o: $(RUNTIME_DIRECTORY)/%.c
	$(compile)
