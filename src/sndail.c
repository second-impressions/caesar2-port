/* State used by the Smacker-to-Miles digital-audio bridge. */
int   fss;
int   didaninit;
int  *SmackAILDigDriver;
int   setbyprog;
int   count;
int   sndinit[5];     /* Scratch buffer shared with the DOS diamond renderers. */
#ifdef __WATCOMC__
/* DOS-only timer state for the sound bridge. */
int   timer;
#endif
