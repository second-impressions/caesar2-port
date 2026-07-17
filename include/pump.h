#ifndef PUMP_H
#define PUMP_H

/* Page 0: high-hash tails of the dword, word, and byte runs. */
extern int pmp_mem_needed;
extern short *son;
extern unsigned short putbuf;
extern short match_position;
extern char getlen;

/* Page 1: low-hash heads, emitted before page 0 within each size class. */
extern short *dad;
extern unsigned char *pmp_inbuff;
extern int pmp_length;
extern unsigned short *freq;
extern int pmp_optr;
extern int pmp_iptr;
extern int textsize;
extern short *rson;
extern unsigned char *pmp_outbuff;
extern short *lson;
extern short *prnt;
extern unsigned char *text_buf;
extern int codesize;
extern short match_length;
extern unsigned short getbuf;
extern unsigned char putlen;

#endif /* PUMP_H */
