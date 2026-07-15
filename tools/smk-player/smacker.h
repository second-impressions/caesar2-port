#ifndef SMACKER_H
#define SMACKER_H
/* Minimal RAD Smacker API for the delink playback test (mirrors
 * decomp/include/smacker.h; __pascal = uppercased callee-pop symbols). */
struct smk_handle {
    unsigned char _pad00[0x08];
    int           Height;              /* +0x08 */
    unsigned int  Frames;             /* +0x0C */
    unsigned char _pad10[0x68 - 0x10];
    int           NewPalette;         /* +0x68 */
    int           PalType;            /* +0x6C */
    unsigned char Palette[772];       /* +0x70 */
    unsigned char Palette2[772];      /* +0x374 */
};

extern void *__pascal radmalloc(unsigned int size);
extern void  __pascal radfree (void *ptr);

extern struct smk_handle *__pascal SmackOpen(char *fname, unsigned flags, unsigned extrabuf);
extern void     __pascal SmackClose    (struct smk_handle *smk);
extern unsigned __pascal SmackWait     (struct smk_handle *smk);
extern unsigned __pascal SmackDoFrame  (struct smk_handle *smk);
extern void     __pascal SmackNextFrame(struct smk_handle *smk);
extern void     __pascal SmackToBuffer (struct smk_handle *smk, unsigned left, unsigned top,
                                        unsigned pitch, unsigned destheight,
                                        const void *buf, unsigned flags);
#endif
