#ifndef PM_MAP1_H
#define PM_MAP1_H

/* Page 0: two BSS tail values plus the three plain-int city-map tables. */
extern int overlay0_empty_mode;
extern int cmu_count[5];
extern int plague_offs[4];
extern int aquaduct_tops[10];
extern int aquaduct_tops2[10];

/* Page 1: the ascending animation-counter run emitted first by Watcom. */
extern int city_anim64;
extern int city_anim128;
extern int city_anim32;
extern int city_anim8;
extern int city_anim16;

#endif /* PM_MAP1_H */
