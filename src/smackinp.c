
int  lowloaded;
int  sounds;
int  trackbuf;
int  simspeed;

/* Initializes a four-byte local buffer with two spaces. */
void __smackw32_text_pad1(void) { char x[4] = "  "; (void)x; }

/* Initializes a second four-byte local buffer with two spaces. */
void __smackw32_text_pad2(void) { char y[4] = "  "; (void)y; }
