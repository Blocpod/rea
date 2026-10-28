#include "c80_lut.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* Synthetic host throughput measurement; not a Canon 80D benchmark. */
int main(void) {
    C80Lut lut;
    uint16_t *table=malloc(17U*17U*17U*3U*sizeof(uint16_t));
    unsigned r,g,b,i;
    unsigned long checksum=0;
    const unsigned count=1920U*1080U;
    clock_t start,finish;
    if (!table) return 2;
    lut.size=17; lut.rgb=table;
    for (i=0;i<3;++i) {lut.domain_min[i]=0;lut.domain_max[i]=65536;}
    for (b=0;b<17;++b) for (g=0;g<17;++g) for (r=0;r<17;++r) {
        size_t base=3U*(r+17U*(g+17U*b));
        table[base]=(uint16_t)(r*65535U/16U);
        table[base+1]=(uint16_t)(g*65535U/16U);
        table[base+2]=(uint16_t)(b*65535U/16U);
    }
    start=clock();
    for (i=0;i<count;++i) {
        uint16_t input[3]={(uint16_t)(i*13U),(uint16_t)(i*31U),(uint16_t)(i*79U)},output[3];
        c80_lut_apply(&lut,input,output);
        checksum+=output[0]+output[1]+output[2];
    }
    finish=clock();
    printf("{\"scope\":\"host_only\",\"pixels\":%u,\"cpu_seconds\":%.6f,\"checksum\":%lu}\n",
           count,(double)(finish-start)/CLOCKS_PER_SEC,checksum);
    free(table);
    return 0;
}
