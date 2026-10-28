#include "c80_lut.h"
#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void fail(const char *message) {
    fprintf(stderr,"c80-grade: %s\n",message);
    exit(2);
}
static int token(FILE *file, char *out, size_t capacity) {
    int c;
    size_t length=0;
    do {
        c=fgetc(file);
        if (c=='#') while (c!='\n' && c!=EOF) c=fgetc(file);
    } while (c!=EOF && isspace((unsigned char)c));
    if (c==EOF) return 0;
    while (c!=EOF && !isspace((unsigned char)c)) {
        if (length+1>=capacity) fail("oversized PPM header token");
        out[length++]=(char)c;
        c=fgetc(file);
    }
    if (c==EOF) fail("missing PPM header delimiter");
    /* Treat CRLF as one line ending, without discarding arbitrary pixel bytes. */
    if (c=='\r') {
        c=fgetc(file);
        if (c!='\n' && c!=EOF) ungetc(c,file);
    }
    out[length]='\0';
    return 1;
}
static unsigned long number(FILE *file) {
    char text[32], *end;
    unsigned long value;
    if (!token(file,text,sizeof(text)) || !isdigit((unsigned char)text[0]))
        fail("invalid PPM integer");
    errno=0;
    value=strtoul(text,&end,10);
    if (errno || *end || !value) fail("invalid PPM integer");
    return value;
}
int main(int argc, char **argv) {
    FILE *lutfile, *input, *output;
    long length;
    uint8_t *blob;
    uint16_t *table;
    C80Lut lut;
    const char *error;
    char magic[8];
    unsigned long width, height, maximum;
    size_t pixel, pixels;
    if (argc!=4) fail("usage: c80-grade LOOK.c80lut INPUT.ppm OUTPUT.ppm");
    if (!strcmp(argv[2],argv[3])) fail("input and output paths must differ");
    lutfile=fopen(argv[1],"rb");
    if (!lutfile) fail("cannot open LUT");
    if (fseek(lutfile,0,SEEK_END) || (length=ftell(lutfile))<0 ||
        length>1647798 || fseek(lutfile,0,SEEK_SET)) fail("invalid LUT length");
    blob=malloc((size_t)length);
    table=malloc(65U*65U*65U*3U*sizeof(uint16_t));
    if (!blob || !table) fail("allocation failed");
    if (fread(blob,1,(size_t)length,lutfile)!=(size_t)length) fail("LUT read failed");
    fclose(lutfile);
    error=c80_lut_init(&lut,blob,(size_t)length,table,65U*65U*65U*3U);
    if (error) fail(error);
    free(blob);
    input=fopen(argv[2],"rb");
    if (!input) fail("cannot open input");
    if (!token(input,magic,sizeof(magic)) || strcmp(magic,"P6")) fail("expected P6 PPM");
    width=number(input); height=number(input); maximum=number(input);
    if ((maximum!=255 && maximum!=65535) || width>SIZE_MAX/height)
        fail("unsupported PPM dimensions or maximum (use 255 or 65535)");
    pixels=(size_t)width*height;
    /* Exclusive creation protects an existing photograph, including aliases. */
    output=fopen(argv[3],"wbx");
    if (!output) fail("cannot create new output");
    if (fprintf(output,"P6\n%lu %lu\n%lu\n",width,height,maximum)<0) fail("output write failed");
    for (pixel=0; pixel<pixels; ++pixel) {
        uint16_t source[3], result[3];
        unsigned channel;
        for (channel=0; channel<3; ++channel) {
            int a=fgetc(input), b;
            if (a==EOF) fail("truncated PPM raster");
            if (maximum==65535) {
                b=fgetc(input);
                if (b==EOF) fail("truncated PPM raster");
                source[channel]=(uint16_t)(a*256+b);
            } else source[channel]=(uint16_t)(a*257);
        }
        c80_lut_apply(&lut,source,result);
        for (channel=0; channel<3; ++channel) {
            if (maximum==65535) {
                if (fputc(result[channel]>>8,output)==EOF ||
                    fputc(result[channel]&255,output)==EOF) fail("output write failed");
            } else if (fputc((result[channel]+128U)/257U,output)==EOF) fail("output write failed");
        }
    }
    if (fgetc(input)!=EOF) fail("unexpected data after PPM raster");
    if (ferror(input) || fclose(input)) fail("input read failed");
    if (fclose(output)) fail("output close failed");
    free(table);
    return 0;
}
