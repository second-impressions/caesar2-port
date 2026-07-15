#ifndef MMEDIA_H
#define MMEDIA_H

/* Page 0: the high-hash tail of the dword run plus the byte buffer. */
extern char media_line_buffer[200];
extern int tutorial_timer;
extern int media_left_image;
extern int tutorial_correct;
extern int linked_text_flag;

/* Page 1: the low-hash head, emitted before page 0 by Watcom. */
extern int greyed_out;
extern int tutorial_correct_timer;
extern int media_voc;
extern int media_right_image;
extern int this_spot;
extern int tutorial_level;
extern int last_tutorial_page;

#endif /* MMEDIA_H */
