#ifndef C2_SAVE_COMPAT_H
#define C2_SAVE_COMPAT_H

#include <stddef.h>

#include "c2_types.h"

#define C2_SAVE_FIGURE_COUNT 201
#define C2_SAVE_FIGURE_SIZE 88
#define C2_SAVE_FIGURES_SIZE (C2_SAVE_FIGURE_COUNT * C2_SAVE_FIGURE_SIZE)

#define C2_SAVE_ARROW_COUNT 201
#define C2_SAVE_ARROW_SIZE 45
#define C2_SAVE_ARROWS_SIZE (C2_SAVE_ARROW_COUNT * C2_SAVE_ARROW_SIZE)

#define C2_SAVE_STATE_SIZE 221745
#define C2_SAVE_HISTORY_SIZE 4000
#define C2_SAVE_FILE_SIZE (C2_SAVE_STATE_SIZE + C2_SAVE_HISTORY_SIZE)
#define C2_SAVE_FIGURES_OFFSET 20202
#define C2_SAVE_ARROWS_OFFSET \
    (C2_SAVE_FIGURES_OFFSET + C2_SAVE_FIGURES_SIZE)

void c2_save_pack_figures(unsigned char *destination,
                          const struct figure_rec *source);
void c2_save_unpack_figures(struct figure_rec *destination,
                            const unsigned char *source);
void c2_save_pack_arrows(unsigned char *destination,
                         const struct arrow_rec *source);
void c2_save_unpack_arrows(struct arrow_rec *destination,
                           const unsigned char *source);

#endif /* C2_SAVE_COMPAT_H */
