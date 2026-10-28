#include "c80_lut.h"
#include <string.h>

static uint16_t u16le(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | (uint16_t)p[1] << 8);
}
static uint32_t u32le(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
/* Decode signed LE without relying on implementation-defined uint32 casts. */
static int32_t i32le(const uint8_t *p) {
    uint32_t value = u32le(p);
    return value <= INT32_MAX ? (int32_t)value : -1 - (int32_t)(UINT32_MAX-value);
}
static uint32_t crc32(const uint8_t *p, size_t len) {
    uint32_t crc = UINT32_MAX;
    size_t i;
    for (i=0; i<len; ++i) {
        unsigned bit;
        crc ^= p[i];
        for (bit=0; bit<8; ++bit)
            crc = (crc >> 1) ^ (UINT32_C(0xedb88320) & (0U-(crc & 1U)));
    }
    return ~crc;
}

const char *c80_lut_init(C80Lut *lut, const uint8_t *blob, size_t bytes,
                       uint16_t *storage, size_t entries) {
    size_t count, i;
    unsigned channel;
    uint16_t size;
    if (!lut || !blob || !storage) return "null argument";
    if (bytes < 48) return "truncated header";
    if (memcmp(blob,"C80LUT3\0",8)) return "invalid magic";
    if (u16le(blob+8) != 1) return "unsupported version";
    size = u16le(blob+10);
    if (size < 2 || size > 65) return "dimension must be 2..65";
    if (u32le(blob+12)) return "unsupported flags";
    count = (size_t)size * size * size * 3;
    if (u32le(blob+40) != count * 2 || bytes != 48 + count * 2)
        return "invalid payload length";
    if (entries < count) return "insufficient caller storage";
    for (channel=0; channel<3; ++channel) {
        int32_t lo = i32le(blob+16+channel*4);
        int32_t hi = i32le(blob+28+channel*4);
        if (lo >= hi) return "invalid input domain";
        lut->domain_min[channel] = lo;
        lut->domain_max[channel] = hi;
    }
    if (crc32(blob+48, count*2) != u32le(blob+44)) return "payload CRC mismatch";
    for (i=0; i<count; ++i) storage[i] = u16le(blob+48+i*2);
    lut->size = size;
    lut->rgb = storage;
    return NULL;
}

static uint16_t lerp(uint16_t a, uint16_t b, uint32_t fraction) {
    return (uint16_t)(((uint64_t)a*(65536U-fraction) +
                       (uint64_t)b*fraction + 32768U) >> 16);
}

void c80_lut_apply(const C80Lut *lut, const uint16_t input[3], uint16_t output[3]) {
    uint32_t index[3], fraction[3];
    unsigned channel, c;
    size_t n = lut->size;
    for (channel=0; channel<3; ++channel) {
        int64_t value = ((uint64_t)input[channel]*65536U+32767U)/65535U;
        int64_t lo = lut->domain_min[channel], hi = lut->domain_max[channel];
        uint64_t position;
        if (value <= lo) position = 0;
        else if (value >= hi) position = (n-1)*UINT64_C(65536);
        else position = (uint64_t)((value-lo)*(int64_t)(n-1)*65536/(hi-lo));
        index[channel] = (uint32_t)(position >> 16);
        fraction[channel] = (uint32_t)(position & 65535U);
        if (index[channel] == n-1) {
            index[channel] = (uint32_t)n-2;
            fraction[channel] = 65536U;
        }
    }
    for (c=0; c<3; ++c) {
        uint16_t z[2];
        unsigned dz, dy;
        for (dz=0; dz<2; ++dz) {
            uint16_t y[2];
            for (dy=0; dy<2; ++dy) {
                size_t base = 3*(index[0] + n*(index[1]+dy + n*(index[2]+dz)));
                y[dy] = lerp(lut->rgb[base+c],lut->rgb[base+3+c],fraction[0]);
            }
            z[dz] = lerp(y[0],y[1],fraction[1]);
        }
        output[c] = lerp(z[0],z[1],fraction[2]);
    }
}
