"""out_format_buffer — minimal Rule 28 swap testbed.

PS @ 0x26AF5, 37 bytes.  PS pushes ebx and edx, uses EDX for 'out'
(after mov edx,eax) and EAX for the index 'i'.  RC pushes the same
ebx and edx but uses EAX for 'out' (no move) and EDX for 'i'.

This is the smallest known Rule 28 case in lib32 — pure ECX/EBX swap
analogues, but with EAX/EDX.

Callers (check_file_exists) DO rely on EDX preservation: they stash
the filename pointer in EDX, call cd_path/out_format_buffer, then
push EDX as arg to open().  So PS source must declare the callee
with a modify-set that preserves EDX.

Run::

    uv run c2 cgex run out_format_buffer
"""

from c2.commands.cgex import Experiment


_PRELUDE = """
extern char format_buffer[];
"""

_DEFS = """
char format_buffer[256];
"""

exp = Experiment(
    name="out_format_buffer",
    ps_function="out_format_buffer",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


exp.add("baseline", """
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="baseline current")


# A: pragma aux modify exact [eax esi edi] -- preserves ebx, ecx, edx
exp.add("A_pragma_modify_exact", """
#pragma aux out_format_buffer modify exact [eax esi edi]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="A: pragma modify exact [eax esi edi]")


# B: pragma aux modify exact [eax ecx esi edi] -- preserves ebx, edx
exp.add("B_pragma_preserve_ebx_edx", """
#pragma aux out_format_buffer modify exact [eax ecx esi edi]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="B: pragma exact preserves ebx+edx only")


# C: char *p running pointer through format_buffer
exp.add("C_running_p", """
void out_format_buffer(char *out)
{
    char *p = format_buffer;
    char c;
    while ((c = *p) != 0) {
        *out++ = c;
        p++;
    }
    *out = c;
}
""", note="C: char *p instead of int i")


# D: swap i and out via comma; declare c first
exp.add("D_c_first", """
void out_format_buffer(char *out)
{
    char c;
    int i;
    i = 0;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="D: c decl first")


# E: separate statements (no compound while)
exp.add("E_separate", """
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    for (;;) {
        c = format_buffer[i];
        if (c == 0) break;
        *out = c;
        out++;
        i++;
    }
    *out = c;
}
""", note="E: for-loop, separate updates")


# F: pragma + named conv
exp.add("F_full_pragma", """
#pragma aux out_format_buffer parm caller [eax] modify exact [eax ecx esi edi]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="F: full pragma with parm caller [eax]")


# G: declare out as register-stored via expression that biases allocator
exp.add("G_local_p_alias", """
void out_format_buffer(char *out)
{
    char *p;
    int i;
    char c;
    p = out;
    i = 0;
    while ((c = format_buffer[i]) != 0) {
        *p++ = c;
        i++;
    }
    *p = c;
}
""", note="G: alias p = out")


# H: index-style with cached buf ptr
exp.add("H_buf_pointer", """
void out_format_buffer(char *out)
{
    char *src;
    int i;
    char c;
    src = format_buffer;
    i = 0;
    while ((c = src[i]) != 0) {
        out[i] = c;
        i++;
    }
    out[i] = c;
}
""", note="H: cached src ptr, out[i] indexing")


# I: use the addressing as out[i] (no increment)
exp.add("I_indexed_out", """
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        out[i] = c;
        i++;
    }
    out[i] = c;
}
""", note="I: out[i] = c (indexed, no inc)")


# J: char ** outptr (double-indirection forces register usage)
exp.add("J_assign_after_test", """
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    c = format_buffer[i];
    while (c != 0) {
        *out = c;
        out++;
        i++;
        c = format_buffer[i];
    }
    *out = c;
}
""", note="J: assignment after test in body")


# K: i as short
exp.add("K_short_i", """
void out_format_buffer(char *out)
{
    short i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="K: short i")


# L: i as unsigned char
exp.add("L_uchar_i", """
void out_format_buffer(char *out)
{
    unsigned char i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="L: unsigned char i")


# M: out via stack arg
exp.add("M_out_stack", """
#pragma aux out_format_buffer parm caller []
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="M: out as stack arg via pragma")


# N: explicit i++ at top of loop body
exp.add("N_i_inc_first", """
void out_format_buffer(char *out)
{
    int i = -1;
    char c;
    while (1) {
        i++;
        c = format_buffer[i];
        if (c == 0) break;
        *out++ = c;
    }
    *out = c;
}
""", note="N: i = -1; i++ at top")


# O: pragma aux default modify exact [eax esi edi]
exp.add("O_aux_default", """
#pragma aux default modify exact [eax esi edi]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="O: pragma aux default modify exact")


# P: pragma aux default parm caller [eax]
exp.add("P_aux_default_parm", """
#pragma aux default parm caller [eax edx ebx ecx] modify exact [eax esi edi]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="P: pragma aux default parm caller + modify")


# Q: include strings, register pressure: declare a 3rd local
exp.add("Q_extra_local", """
void out_format_buffer(char *out)
{
    int i = 0;
    int j;
    char c;
    j = 0;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
        j++;
    }
    *out = c;
    (void)j;
}
""", note="Q: extra local for register pressure")


# R: pragma with named modifier and ecx in parms
exp.add("R_parm_eax_ecx", """
#pragma aux out_format_buffer parm caller [eax]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="R: parm caller [eax] only")


# Flag experiments: try variations of cflags
_BODY = """
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
"""

exp.add("flag_3r", _BODY, note="cflags -3r (386 instead of 486)",
        cflags="-bt=dos -mf -3r -s")
exp.add("flag_5r", _BODY, note="cflags -5r (Pentium)",
        cflags="-bt=dos -mf -5r -s")
exp.add("flag_ol", _BODY, note="cflags +ol (loop opts)",
        cflags="-bt=dos -mf -4r -s -ol")
exp.add("flag_os", _BODY, note="cflags +os (size)",
        cflags="-bt=dos -mf -4r -s -os")
exp.add("flag_ot", _BODY, note="cflags +ot (time)",
        cflags="-bt=dos -mf -4r -s -ot")
exp.add("flag_oa", _BODY, note="cflags +oa (alias)",
        cflags="-bt=dos -mf -4r -s -oa")
exp.add("flag_oh", _BODY, note="cflags +oh (super regalloc)",
        cflags="-bt=dos -mf -4r -s -oh")
exp.add("flag_oe", _BODY, note="cflags +oe (inline)",
        cflags="-bt=dos -mf -4r -s -oe")
exp.add("flag_oi", _BODY, note="cflags +oi (intrinsics)",
        cflags="-bt=dos -mf -4r -s -oi")
exp.add("flag_d1", _BODY, note="cflags +d1 (line debug)",
        cflags="-bt=dos -mf -4r -s -d1")
exp.add("flag_d2", _BODY, note="cflags +d2 (full debug)",
        cflags="-bt=dos -mf -4r -s -d2")
exp.add("flag_zc", _BODY, note="cflags +zc (const in code)",
        cflags="-bt=dos -mf -4r -s -zc")
exp.add("flag_zm", _BODY, note="cflags +zm (seg per module)",
        cflags="-bt=dos -mf -4r -s -zm")
exp.add("flag_zp1", _BODY, note="cflags +zp1 (pack 1)",
        cflags="-bt=dos -mf -4r -s -zp1")
exp.add("flag_zp4", _BODY, note="cflags +zp4 (pack 4)",
        cflags="-bt=dos -mf -4r -s -zp4")


# format_buffer declaration variations
exp.add("S_fb_no_size", """
extern char format_buffer[];
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="S: extern fb with no size (override)")


# Cast format_buffer indexing
exp.add("T_uchar_index", """
void out_format_buffer(char *out)
{
    int i = 0;
    unsigned char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="T: unsigned char c")


# Use a pointer cache for format_buffer
exp.add("U_fb_cache_far", """
void out_format_buffer(char *out)
{
    static char *fb = format_buffer;
    int i = 0;
    char c;
    while ((c = fb[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="U: static fb pointer cache")


# Different combine: use long indexing
exp.add("V_long_i", """
void out_format_buffer(char *out)
{
    long i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="V: long i")


# i as unsigned int
exp.add("W_uint_i", """
void out_format_buffer(char *out)
{
    unsigned int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="W: unsigned int i")


# X: try far function
exp.add("X_far_fn", """
void __far out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="X: __far function")


# Y: try __saveregs
exp.add("Y_saveregs", """
void __saveregs out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="Y: __saveregs (preserve all regs)")


# Z: __loadds 
exp.add("Z_loadds", """
void __loadds out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="Z: __loadds")


# AA: pragma aux with frame
exp.add("AA_pragma_frame", """
#pragma aux out_format_buffer frame parm caller [eax]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="AA: pragma frame")


# BB: pragma with explicit caller-cleans-stack
exp.add("BB_pragma_routine_caller", """
#pragma aux out_format_buffer = caller parm [eax]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="BB: pragma routine, caller cleanup")


# CC: declare as int returning (PS-asm doesn't set EAX before ret, but maybe void/int matter for regalloc)
exp.add("CC_int_return", """
int out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
    return 0;
}
""", note="CC: int return type")


# DD: declare returning char *
exp.add("DD_charp_return", """
char *out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
    return out;
}
""", note="DD: char* return value")


# EE: pragma with explicit value [edx] return reg
exp.add("EE_value_edx", """
#pragma aux out_format_buffer value [edx]
int out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
    return i;
}
""", note="EE: pragma value [edx] -- return in EDX")


# FF: implicit-int return (no return statement)
exp.add("FF_implicit_int", """
out_format_buffer(out)
char *out;
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="FF: K&R style implicit int")


# GG: include <string.h> for prototypes that may affect regalloc default
exp.add("GG_with_string_h", """
#include <string.h>
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="GG: #include <string.h>")


# HH: include <stdio.h>
exp.add("HH_with_stdio", """
#include <stdio.h>
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="HH: #include <stdio.h>")


# II: ec (extern fns convention, declare extern caller)
exp.add("II_disable_intrinsics", """
#pragma intrinsic(strcpy)
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="II: pragma intrinsic strcpy")


# Memory model variations (only -mf works with -bt=dos; try others)
exp.add("ms_model", _BODY, note="-ms (small)",
        cflags="-bt=dos -ms -4r -s")
exp.add("mm_model", _BODY, note="-mm (medium)",
        cflags="-bt=dos -mm -4r -s")
exp.add("mc_model", _BODY, note="-mc (compact)",
        cflags="-bt=dos -mc -4r -s")
exp.add("ml_model", _BODY, note="-ml (large)",
        cflags="-bt=dos -ml -4r -s")
exp.add("mh_model", _BODY, note="-mh (huge)",
        cflags="-bt=dos -mh -4r -s")

# Stack convention variations
exp.add("flag_3s", _BODY, note="-3s (stack convention)",
        cflags="-bt=dos -mf -3s -s")
exp.add("flag_4s", _BODY, note="-4s (stack convention)",
        cflags="-bt=dos -mf -4s -s")

# Floating point
exp.add("flag_fpc", _BODY, note="-fpc (emulated FP)",
        cflags="-bt=dos -mf -4r -s -fpc")
exp.add("flag_fpi87", _BODY, note="-fpi87 (387 inline)",
        cflags="-bt=dos -mf -4r -s -fpi87")

# Aggressive optimization
exp.add("flag_oxax", _BODY, note="-ox -ax (max opt + alias-related)",
        cflags="-bt=dos -mf -4r -s -ox")
exp.add("flag_obr", _BODY, note="-obr (branch?)",
        cflags="-bt=dos -mf -4r -s -obr")

# Compile environment vars (env-flag style)
exp.add("flag_zq_zs", _BODY, note="-zq -zs (quiet + syntax)",
        cflags="-bt=dos -mf -4r -s -zq -zs")


# JJ: include i86.h (DOS register defs)
exp.add("JJ_include_i86", """
#include <i86.h>
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="JJ: #include <i86.h>")


# KK: include conio.h
exp.add("KK_include_conio", """
#include <conio.h>
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="KK: #include <conio.h>")


# LL: declare strcpy intrinsic outside the function, may affect default modify set
exp.add("LL_strcpy_intrinsic", """
extern char *strcpy(char *, const char *);
#pragma intrinsic(strcpy)
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="LL: strcpy intrinsic declared")


# MM: a fake call to strcpy to force intrinsic resolution
exp.add("MM_force_intrinsic", """
extern char *strcpy(char *, const char *);
#pragma intrinsic(strcpy)
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
    if (i == 0xdeadbeef) strcpy(out, format_buffer);
}
""", note="MM: dead-code strcpy forces intrinsic")


# NN: rename parm to force aliasing
exp.add("NN_p_to_out", """
void out_format_buffer(char *p)
{
    char *out = p;
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="NN: parm p, local out = p")


# OO: shorter loop end
exp.add("OO_postfix_inc_only", """
void out_format_buffer(char *out)
{
    int i = 0;
    while (format_buffer[i] != 0) {
        out[i] = format_buffer[i];
        i++;
    }
    out[i] = 0;
}
""", note="OO: out[i] indexing, end with 0")


# PP: more uses of out (bias allocator)
exp.add("PP_out_uses_more", """
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    char *start = out;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
    (void)start;
}
""", note="PP: extra unused use of out via start")


# QQ: explicit cast emphasis
exp.add("QQ_cast", """
void out_format_buffer(char *out)
{
    int i = (int)0;
    char c;
    while ((c = format_buffer[i]) != (char)0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="QQ: explicit (int) casts")


# RR: __cdecl (stack-passing)
exp.add("RR_cdecl", """
void __cdecl out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="RR: __cdecl convention")


# SS: __stdcall
exp.add("SS_stdcall", """
void __stdcall out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="SS: __stdcall convention")


# TT: __pascal
exp.add("TT_pascal", """
void __pascal out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="TT: __pascal convention")


# UU: __fastcall
exp.add("UU_fastcall", """
void __fastcall out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="UU: __fastcall")


# VV: store c via int -- forces extra masking
exp.add("VV_int_c", """
void out_format_buffer(char *out)
{
    int i = 0;
    int c;
    while ((c = format_buffer[i] & 0xff) != 0) {
        *out++ = (char)c;
        i++;
    }
    *out = (char)c;
}
""", note="VV: int c instead of char")


# WW: dummy c live before loop
exp.add("WW_c_pre_init", """
void out_format_buffer(char *out)
{
    int i = 0;
    char c = 0;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="WW: c = 0 init")


# XX: c declared as short
exp.add("XX_short_c", """
void out_format_buffer(char *out)
{
    int i = 0;
    short c;
    while ((c = (short)format_buffer[i]) != 0) {
        *out++ = (char)c;
        i++;
    }
    *out = (char)c;
}
""", note="XX: short c (forces 16-bit reg)")


# YY: explicit type for parm via pragma value
exp.add("YY_pragma_caller_edx", """
#pragma aux out_format_buffer parm caller [edx]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="YY: parm caller [edx] -- out arrives in EDX!")


# ZZ: explicit modify list with edx and eax (eax always implicit)
exp.add("ZZ_modify_edx", """
#pragma aux out_format_buffer modify [eax edx ebx]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="ZZ: modify [eax edx ebx]")


# AAA: modify with just ebx
exp.add("AAA_modify_ebx", """
#pragma aux out_format_buffer modify [ebx]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="AAA: modify [ebx] only")


# BBB: pragma with explicit assembly hints
exp.add("BBB_pragma_simple", """
#pragma aux out_format_buffer "*"
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="BBB: pragma aux name '*'")


# CCC: pragma modify exact [eax ebx] -- preserve edx, ecx, esi, edi
exp.add("CCC_preserve_edx", """
#pragma aux out_format_buffer modify exact [eax ebx]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="CCC: modify exact [eax ebx] preserves EDX,ECX,ESI,EDI")


# DDD: modify exact with only eax 
exp.add("DDD_modify_exact_eax", """
#pragma aux out_format_buffer modify exact [eax]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="DDD: modify exact [eax] -- preserve ALL except EAX")


# EEE: modify exact [] empty -- preserve all (would force lots of saving)
exp.add("EEE_modify_exact_empty", """
#pragma aux out_format_buffer modify exact []
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="EEE: modify exact [] preserve EVERYTHING")


# FFF: aux default save_regs=[ebx edx] — preserve EBX and EDX as save set
exp.add("FFF_default_save_ebx_edx", """
#pragma aux default modify exact []
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="FFF: aux default modify exact [] preserves ALL")


# GGG: declare extern functions THAT we don't call but they may set default
exp.add("GGG_extern_helpers", """
extern void some_helper1(void);
extern void some_helper2(int);
extern int some_helper3(char *);
#pragma aux some_helper1 modify exact [eax esi edi]
#pragma aux some_helper2 modify exact [eax esi edi]
#pragma aux some_helper3 modify exact [eax esi edi]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="GGG: extern helpers with pragmas, may affect default")


# HHH: dummy preceding function in same TU
exp.add("HHH_preceding_fn", """
extern int dummy_int;
void dummy_fn(void)
{
    dummy_int = 1;
}
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="HHH: preceding fn in TU")


# III: try -bm flag (multi-threaded - shouldn't apply to dos but try)
exp.add("III_bm_flag", _BODY, note="-bm (multi-threaded)",
        cflags="-bt=dos -mf -4r -s -bm")


# JJJ: -fp3 floating point
exp.add("JJJ_fp3", _BODY, note="-fp3 (387 instruction sets)",
        cflags="-bt=dos -mf -4r -s -fp3")


# KKK: -dvar (define preproc macro)
exp.add("KKK_define_macro", """
#ifdef CAESAR2_BUILD
char *fb = format_buffer;
#endif
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="KKK: define -DCAESAR2_BUILD", cflags="-bt=dos -mf -4r -s -dCAESAR2_BUILD")


# LLL: try with explicit /od (no optimization)
exp.add("LLL_od_flag", _BODY, note="-od (no optimization)",
        cflags="-bt=dos -mf -4r -s -od")


# MMM: try -ow (window-style alignment)
exp.add("MMM_ow_flag", _BODY, note="-ow (window alignment)",
        cflags="-bt=dos -mf -4r -s -ow")


# NNN: -ec defs (no enum-int conversion?)
exp.add("NNN_ec_flag", _BODY, note="-ec (extern C convention)",
        cflags="-bt=dos -mf -4r -s -ec=__cdecl")


# OOO: -j (signed char default)
exp.add("OOO_j_signed_char", _BODY, note="-j (signed char default)",
        cflags="-bt=dos -mf -4r -s -j")


# PPP: -zev (enums as variable size)
exp.add("PPP_zev", _BODY, note="-zev (variable enum size)",
        cflags="-bt=dos -mf -4r -s -zev")


# QQQ: -zu (assume SS != DS)
exp.add("QQQ_zu", _BODY, note="-zu (SS != DS)",
        cflags="-bt=dos -mf -4r -s -zu")


# RRR: register on out (param-level register hint)
exp.add("RRR_register_out", """
void out_format_buffer(register char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="RRR: register char *out param")


# SSS: register on i
exp.add("SSS_register_i", """
void out_format_buffer(char *out)
{
    register int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="SSS: register int i")


# TTT: both register
exp.add("TTT_register_both", """
void out_format_buffer(register char *out)
{
    register int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="TTT: both register")


# UUU: alias out to another local in if-block
exp.add("UUU_outer_local_swap", """
void out_format_buffer(char *out)
{
    char *p;
    int i;
    char c;
    p = out;
    for (i = 0; (c = format_buffer[i]) != 0; i++)
        *p++ = c;
    *p = c;
}
""", note="UUU: p alias + for-loop")


# VVV: use base+offset where base is a pointer arg
exp.add("VVV_base_offset_swap", """
void out_format_buffer(char *out)
{
    char c;
    int i;
    i = 0;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="VVV: c before i in decl, separate init")


# WWW: explicit type widening for i to match Watcom's expected lifetime
exp.add("WWW_long_i_inited", """
void out_format_buffer(char *out)
{
    long i = 0L;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="WWW: long i with explicit 0L")


# XXX: try with do-while
exp.add("XXX_do_while", """
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    do {
        c = format_buffer[i];
        *out++ = c;
        i++;
    } while (c != 0);
    /* *out = c is implicit since last iteration writes 0 */
}
""", note="XXX: do-while (write before test)")


# YYY: variable-init expression that touches both
exp.add("YYY_paired_decl", """
void out_format_buffer(char *out)
{
    int i;
    char c;
    for (i = 0; (c = format_buffer[i]) != 0; i++)
        *out++ = c;
    *out = c;
}
""", note="YYY: for-loop init + step")


# ZZZ: explicit Watcom save_regs pragma
exp.add("ZZZ_explicit_save", """
#pragma aux out_format_buffer save [ebx edx]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="ZZZ: pragma aux ... save [ebx edx]")


# AAAA: add dummy variables earlier to change conflict numbering
exp.add("AAAA_many_dummy_vars", """
void out_format_buffer(char *out)
{
    int dummy1 = 0, dummy2 = 0, dummy3 = 0, dummy4 = 0;
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
    (void)dummy1; (void)dummy2; (void)dummy3; (void)dummy4;
}
""", note="AAAA: 4 dummies before i")


# BBBB: prior dummy fn that uses many regs
exp.add("BBBB_prior_fn_uses_regs", """
extern int dummy_a, dummy_b, dummy_c, dummy_d;
void dummy_fn_first(int p) {
    dummy_a = p + 1;
    dummy_b = p * 2;
    dummy_c = p - 1;
    dummy_d = p / 2;
}
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="BBBB: prior fn using all regs")


# CCCC: try _Packed or alignment
exp.add("CCCC_packed", """
_Packed struct fb_t { char data[256]; };
extern _Packed struct fb_t fb_struct;
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="CCCC: _Packed unused")


# DDDD: extern declarations of MANY OTHER functions that have unusual pragmas
exp.add("DDDD_priorpragmas", """
extern void some_external_a(int);
extern int some_external_b(int);
extern void some_external_c(int, int);
#pragma aux some_external_a parm caller [edx] modify exact [eax]
#pragma aux some_external_b parm caller [eax] value [edx] modify exact [eax edx ecx]
#pragma aux some_external_c parm caller [eax ebx] modify exact [eax edx esi]
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="DDDD: prior #pragma aux declarations")


# EEEE: explicit pragma off check_stack
exp.add("EEEE_check_stack_off", """
#pragma off (check_stack)
void out_format_buffer(char *out)
{
    int i = 0;
    char c;
    while ((c = format_buffer[i]) != 0) {
        *out++ = c;
        i++;
    }
    *out = c;
}
""", note="EEEE: #pragma off check_stack")


# FFFF: turn off -s flag (default IS off, but -s ON => no check)
exp.add("FFFF_no_s_flag", _BODY, note="without -s (check_stack ON)",
        cflags="-bt=dos -mf -4r")


# GGGG: -zw windows compatibility
exp.add("GGGG_zw", _BODY, note="-zw (windows)",
        cflags="-bt=dos -mf -4r -s -zw")


# HHHH: aggressive optimizations
exp.add("HHHH_or", _BODY, note="-or (instruction scheduling)",
        cflags="-bt=dos -mf -4r -s -or")


# IIII: target nt
exp.add("IIII_nt", _BODY, note="-bt=nt",
        cflags="-bt=nt -mf -4r -s")


# JJJJ: combine -ol + ox
exp.add("JJJJ_ol_ox", _BODY, note="-ol -ox",
        cflags="-bt=dos -mf -4r -s -ol -ox")


# KKKK: nested expression — no named c
exp.add("KKKK_no_named_c", """
void out_format_buffer(char *out)
{
    int i = 0;
    while (format_buffer[i] != 0) {
        *out++ = format_buffer[i];
        i++;
    }
    *out = 0;
}
""", note="KKKK: no named c, double load")


# LLLL: out + i as standalone pointer arith
exp.add("LLLL_ptrdiff_idiom", """
void out_format_buffer(char *out)
{
    char *p;
    for (p = format_buffer; *p != 0; p++)
        *out++ = *p;
    *out = 0;
}
""", note="LLLL: pure pointer iter")


# MMMM: store via pointer-deref but use index for read
exp.add("MMMM_mixed_idx_ptr", """
void out_format_buffer(char *out)
{
    char *src = format_buffer;
    char c;
    while ((c = *src) != 0) {
        *out = c;
        src++;
        out++;
    }
    *out = c;
}
""", note="MMMM: char *src reads, separate out++")


# NNNN: outer copy pattern that mimics strcpy
exp.add("NNNN_strcpy_like", """
void out_format_buffer(char *out)
{
    char *s = format_buffer;
    while ((*out++ = *s++) != 0)
        ;
}
""", note="NNNN: K&R strcpy idiom")


# OOOO: KKKK + tighter inc order
exp.add("OOOO_inc_swap", """
void out_format_buffer(char *out)
{
    int i = 0;
    while (format_buffer[i] != 0) {
        *out = format_buffer[i];
        i++;
        out++;
    }
    *out = 0;
}
""", note="OOOO: KKKK with i++ before out++")


# PPPP: write through nested for w/ explicit increments
exp.add("PPPP_for_loop", """
void out_format_buffer(char *out)
{
    int i;
    for (i = 0; format_buffer[i] != 0; i++) {
        *out = format_buffer[i];
        out++;
    }
    *out = 0;
}
""", note="PPPP: for-loop with i in step")


# QQQQ: KKKK base with explicit final via format_buffer
exp.add("QQQQ_final_via_fb", """
void out_format_buffer(char *out)
{
    int i = 0;
    while (format_buffer[i] != 0) {
        *out++ = format_buffer[i];
        i++;
    }
    *out = format_buffer[i];
}
""", note="QQQQ: final = format_buffer[i] (the 0 byte)")
