/*
 * Storage for the shared scratch slots that src/library.asm defined in its
 * _DATA segment.  The recovered assembly exported lib_ret1..lib_ret4 and
 * lib_para1..lib_para4; this file defines the subset that surviving code
 * still touches, so every reference resolves on every target.
 *
 * lib_para1/lib_para2 carry the diamond-pointer arguments from pm_map0 into
 * the translated routine in c2_asm_diamond_ptr.c.
 *
 * lib_ret4 is written by pump.c but read by nobody: the LZSS encoder's
 * result slot was consumed by the assembly compressor that the portable
 * build no longer uses.  It is retained as storage rather than deleted from
 * the recovered write site, so pump.c stays structurally comparable with the
 * reconstruction.  Native ELF links tolerated its absence only because
 * --gc-sections discarded the referring section before symbol resolution;
 * PE/COFF does not, and the Windows target reported it as an undefined
 * reference.
 */
int lib_para1;
int lib_para2;
int lib_ret4;
