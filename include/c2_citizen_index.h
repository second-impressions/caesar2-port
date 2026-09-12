#ifndef C2_CITIZEN_INDEX_H
#define C2_CITIZEN_INDEX_H

#include "c2_target.h"

/*
 * Citizen (walker) slot indices and where they are stored.
 *
 * The recovered engine keeps every citizen index in a single byte: two per
 * city cell (`citizen_a`, `citizen_b`: who stands on the tile), one per
 * market or business cell (`industrial`: the walker it last sent out) and
 * one per citizen (`target_kind`: the walker a fighter is chasing). The
 * 20-byte city cell is addressed by raw byte offset throughout the engine
 * and is a raw image in the original save, so those bytes cannot be
 * widened in place. They cap the walker pool at 254.
 *
 * PORT_FEAT_WIDE_CITIZEN_INDEX moves the three references into side
 * tables owned by the portable layer and raises the pool to
 * PORT_CITIZEN_POOL. Every recovered access goes through the macros below,
 * which expand to the original cell and record bytes when the feature is
 * off, so the shipped DOS and Windows targets and the recovered behaviour
 * are unchanged.
 */

#ifndef PORT_FEAT_WIDE_CITIZEN_INDEX
#define PORT_FEAT_WIDE_CITIZEN_INDEX PORT_PLATFORM
#endif

#if PORT_FEAT_WIDE_CITIZEN_INDEX != 0 && PORT_FEAT_WIDE_CITIZEN_INDEX != 1
#error "PORT_FEAT_WIDE_CITIZEN_INDEX must be 0 or 1"
#endif

#if !PORT_PLATFORM && PORT_FEAT_WIDE_CITIZEN_INDEX
#error "PORT_FEAT_WIDE_CITIZEN_INDEX requires the portable target"
#endif

#if PORT_FEAT_WIDE_CITIZEN_INDEX
#  ifndef PORT_CITIZEN_POOL
#    define PORT_CITIZEN_POOL 1000
#  endif
#  if PORT_CITIZEN_POOL < 200 || PORT_CITIZEN_POOL > 65534
#    error "PORT_CITIZEN_POOL must be between 200 and 65534"
#  endif
#else
#  undef PORT_CITIZEN_POOL
#  define PORT_CITIZEN_POOL 200
#endif

/* Slot 0 is the "no citizen" sentinel and is never allocated. */
#define PORT_CITIZEN_SLOTS (PORT_CITIZEN_POOL + 1)

#define PORT_CITY_CELLS 6400

#if PORT_FEAT_WIDE_CITIZEN_INDEX

extern unsigned short c2_cell_citizen_a[PORT_CITY_CELLS];
extern unsigned short c2_cell_citizen_b[PORT_CITY_CELLS];
extern unsigned short c2_cell_envoy[PORT_CITY_CELLS];
extern unsigned short c2_citizen_target[PORT_CITIZEN_SLOTS];

/* `off` is a byte offset into city_map (cell index * 20). */
#define PORT_CELL_CITIZEN_A(off) (c2_cell_citizen_a[(off) / 20])
#define PORT_CELL_CITIZEN_B(off) (c2_cell_citizen_b[(off) / 20])
#define PORT_CELL_ENVOY(off)     (c2_cell_envoy[(off) / 20])
#define PORT_CITIZEN_TARGET(i)   (c2_citizen_target[(i)])
/* The recovered code narrows every index it reads to a byte; a wide index
 * must not be. */
#define PORT_CITIZEN_CAST(x)     (x)
/* The query panel's list of people on the queried tile is a byte array in
 * the recovered data image; this is its wide twin. */
extern unsigned short c2_q_people_wide[10];
#define PORT_Q_PEOPLE(i)         (c2_q_people_wide[(i)])

void c2_citizen_index_clear(void);

#else

#define PORT_CELL_CITIZEN_A(off) \
    ((*(struct city_cell *)((unsigned char *)city_map + (off))).citizen_a)
#define PORT_CELL_CITIZEN_B(off) \
    ((*(struct city_cell *)((unsigned char *)city_map + (off))).citizen_b)
#define PORT_CELL_ENVOY(off) \
    ((*(struct city_cell *)((unsigned char *)city_map + (off))).industrial)
#define PORT_CITIZEN_TARGET(i)   (citizen_list[(i)].target_kind)
#define PORT_CITIZEN_CAST(x)     ((unsigned char)(x))
#define PORT_Q_PEOPLE(i)         (q_people_list[(i)])

#endif

#endif /* C2_CITIZEN_INDEX_H */
