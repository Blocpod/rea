#ifndef C80_LUT_H
#define C80_LUT_H
#include <stddef.h>
#include <stdint.h>

/* Borrowed caller-owned table: do not free or change it while applying. */
typedef struct {
    uint16_t size;
    int32_t domain_min[3], domain_max[3];
    const uint16_t *rgb;
} C80Lut;

/* Validate a v1 blob and decode into caller storage. No allocation or I/O.
 * Returns NULL on success, otherwise a constant error string. On error the
 * destination is not usable. Required storage: 3 * size^3 uint16_t entries. */
const char *c80_lut_init(C80Lut *lut, const uint8_t *blob, size_t bytes,
                       uint16_t *storage, size_t entries);

/* Input/output are normalized unsigned 16-bit RGB. In-place use is supported.
 * Init must have succeeded. Output is trilinear, with integer-only hot paths. */
void c80_lut_apply(const C80Lut *lut, const uint16_t input[3], uint16_t output[3]);

#endif
