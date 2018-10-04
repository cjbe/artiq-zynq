#include <stdarg.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <stdint.h>

struct slice {
    void   *ptr;
    size_t  len;
};

void send_to_core_log(struct slice str);

#define KERNELCPU_EXEC_ADDRESS    0x40800000
#define KERNELCPU_PAYLOAD_ADDRESS 0x40840000
#define KERNELCPU_LAST_ADDRESS    0x4fffffff
#define KSUPPORT_HEADER_SIZE      0x80


/* called by kernel */
double round(double x);
double round(double x)
{
    union {double f; uint64_t i;} u = {x};
    int e = u.i >> 52 & 0x7ff;
    double y;

    if (e >= 0x3ff+52)
        return x;
    if (u.i >> 63)
        x = -x;
    if (e < 0x3ff-1) {
        /* we don't do it in ARTIQ */
        /* raise inexact if x!=0 */
        // FORCE_EVAL(x + 0x1p52);
        return 0*u.f;
    }
    y = (double)(x + 0x1p52) - 0x1p52 - x;
    if (y > 0.5)
        y = y + x - 1;
    else if (y <= -0.5)
        y = y + x + 1;
    else
        y = y + x;
    if (u.i >> 63)
        y = -y;
    return y;
}

/* called by kernel */
int core_log(const char *fmt, ...);
int core_log(const char *fmt, ...)
{
    va_list args;

    va_start(args, fmt);
    size_t size = vsnprintf(NULL, 0, fmt, args);
    char *buf = __builtin_alloca(size + 1);
    va_end(args);

    va_start(args, fmt);
    vsnprintf(buf, size + 1, fmt, args);
    va_end(args);

    struct slice str = { buf, size };
    send_to_core_log(str);
    return 0;
}
