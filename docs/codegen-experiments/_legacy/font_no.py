"""font_no — lib32 numeric-formatting routine.

PS @ 0x2704E, 220 bytes.  Current source is at ~165 b diff against PS.
The remaining diffs cluster on:

  * div10 living in [esp] (volatile) vs PS's ebp register reloaded
    twice per loop body
  * pad_char NOT spilled to stack in recomp; PS stores it at [esp+4]
  * x NOT spilled in recomp (lives in callee-save edi); PS stores
    at [esp+0]
  * buf address loaded as immediate in recomp; PS keeps it in edi
    as `mov edi, 0xa35` literal

Each is regalloc-driven.  The experiment enumerates source shapes
that move levers in those directions.

Run::

    uv run c2 cgex run font_no
    uv run c2 cgex run font_no --trial baseline
"""

from c2.commands.cgex import Experiment

_PRELUDE = '''
extern int font_screen_limit;
'''

_DEFS = '''
int font_screen_limit;
int g_ten = 10;
'''

exp = Experiment(
    name="font_no",
    ps_function="font_no",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
    externs={
        "strip_leading_space":
            "extern void strip_leading_space(signed char *s);",
        "put_a_font_string":
            "extern void put_a_font_string(char *buf, int x, int y,"
            " unsigned char *font, int color);",
    },
)


_BUF = 'static char buf[] = "                ";'


def _body(decls, init, pad_loop, suffix_loop, digit_loop, tail):
    return f'''
void font_no(int value, char pad_char, char *suffix, int x,
             int y, unsigned char *font, int color)
{{
    {_BUF}
{decls}
{init}
{pad_loop}
{suffix_loop}
{digit_loop}
{tail}
}}
'''


# Baseline = current source.
exp.add(
    "baseline",
    _body(
        decls="""
    int  i;
    volatile int div10;
    char had_zero;
    char saved_pad;
    int  saved_x;
""",
        init="""
    saved_pad = pad_char;
    saved_x   = x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            buf[i] = saved_pad;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &buf[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    buf[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            buf[i] = ' ';
        } else {
            div10 = 10;
            buf[i] = (char)((value % div10) + '0');
        }
    next:
        div10 = 10;
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)buf);
    put_a_font_string(buf, saved_x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="current decomp/src/lib32.c source (~165 b diff)",
)


# Variant: address-take pad_char only (force [esp+4] spill).
exp.add(
    "addr-pad",
    _body(
        decls="""
    int  i;
    volatile int div10;
    char had_zero;
    char saved_pad;
    int  saved_x;
    char *pp;
""",
        init="""
    saved_pad = pad_char;
    pp        = &saved_pad;
    saved_x   = x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            buf[i] = *pp;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &buf[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    buf[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            buf[i] = ' ';
        } else {
            div10 = 10;
            buf[i] = (char)((value % div10) + '0');
        }
    next:
        div10 = 10;
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)buf);
    put_a_font_string(buf, saved_x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="address-taken saved_pad forces stack spill",
)


# Variant: address-take both pad_char AND x.
exp.add(
    "addr-pad-x",
    _body(
        decls="""
    int  i;
    volatile int div10;
    char had_zero;
    char saved_pad;
    int  saved_x;
    char *pp;
    int  *px;
""",
        init="""
    saved_pad = pad_char;
    pp        = &saved_pad;
    saved_x   = x;
    px        = &saved_x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            buf[i] = *pp;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &buf[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    buf[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            buf[i] = ' ';
        } else {
            div10 = 10;
            buf[i] = (char)((value % div10) + '0');
        }
    next:
        div10 = 10;
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)buf);
    put_a_font_string(buf, *px, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="address-take both pad_char and x",
)


# Variant: drop saved_x/saved_pad, use params directly.
exp.add(
    "no-saved",
    _body(
        decls="""
    int  i;
    volatile int div10;
    char had_zero;
""",
        init="""
    had_zero = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            buf[i] = pad_char;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &buf[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    buf[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            buf[i] = ' ';
        } else {
            div10 = 10;
            buf[i] = (char)((value % div10) + '0');
        }
    next:
        div10 = 10;
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)buf);
    put_a_font_string(buf, x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="no saved_x/saved_pad locals; use params directly",
)


# Variant: non-volatile div10 (control — magic-mul or hoist).
exp.add(
    "no-volatile",
    _body(
        decls="""
    int  i;
    int  div10;
    char had_zero;
    char saved_pad;
    int  saved_x;
""",
        init="""
    saved_pad = pad_char;
    saved_x   = x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            buf[i] = saved_pad;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &buf[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    buf[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            buf[i] = ' ';
        } else {
            div10 = 10;
            buf[i] = (char)((value % div10) + '0');
        }
    next:
        div10 = 10;
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)buf);
    put_a_font_string(buf, saved_x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="non-volatile div10 — control",
)


# Variant: bufp pointer cached at function start.
exp.add(
    "bufp-cache",
    _body(
        decls="""
    char *bufp;
    int  i;
    volatile int div10;
    char had_zero;
    char saved_pad;
    int  saved_x;
""",
        init="""
    bufp      = buf;
    saved_pad = pad_char;
    saved_x   = x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            bufp[i] = saved_pad;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &bufp[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    bufp[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            bufp[i] = ' ';
        } else {
            div10 = 10;
            bufp[i] = (char)((value % div10) + '0');
        }
    next:
        div10 = 10;
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)bufp);
    put_a_font_string(bufp, saved_x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="cache buf into bufp pointer (force edi=buf)",
)


# Variant: bufp + non-volatile div10 (both levers)
exp.add(
    "bufp-nonvol",
    _body(
        decls="""
    char *bufp;
    int  i;
    int  div10;
    char had_zero;
    char saved_pad;
    int  saved_x;
""",
        init="""
    bufp      = buf;
    saved_pad = pad_char;
    saved_x   = x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            bufp[i] = saved_pad;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &bufp[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    bufp[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            bufp[i] = ' ';
        } else {
            div10 = 10;
            bufp[i] = (char)((value % div10) + '0');
        }
    next:
        div10 = 10;
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)bufp);
    put_a_font_string(bufp, saved_x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="bufp cache + non-volatile div10",
)

# Variant: bufp + no saved_x (force x on stack since edi=bufp)
exp.add(
    "bufp-no-savedx",
    _body(
        decls="""
    char *bufp;
    int  i;
    int  div10;
    char had_zero;
    char saved_pad;
""",
        init="""
    bufp      = buf;
    saved_pad = pad_char;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            bufp[i] = saved_pad;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &bufp[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    bufp[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            bufp[i] = ' ';
        } else {
            div10 = 10;
            bufp[i] = (char)((value % div10) + '0');
        }
    next:
        div10 = 10;
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)bufp);
    put_a_font_string(bufp, x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="bufp + drop saved_x (use x directly in tail)",
)

# Divisor variants — search for the form that makes Watcom
# allocate div10 to ebp (register, not [esp]) while still
# reloading it twice per iteration.  PS uses `mov ebp, 0xa`
# twice per loop body.

# Use a local with computed init that the compiler can't easily fold.
# Watcom 10.0a is sometimes blocked by an apparent dependency.
exp.add(
    "div-computed",
    _body(
        decls="""
    int  i;
    int  div10;
    char had_zero;
    char saved_pad;
    int  saved_x;
""",
        init="""
    saved_pad = pad_char;
    saved_x   = x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            buf[i] = saved_pad;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &buf[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    buf[i] = 0;
""",
        digit_loop="""
    div10 = 10;
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            buf[i] = ' ';
        } else {
            buf[i] = (char)((value % div10) + '0');
        }
    next:
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)buf);
    put_a_font_string(buf, saved_x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="div10 = 10 outside loop (control: should hoist + magic mul)",
)

# Use two separate identifiers div10a / div10b — block scope.
exp.add(
    "div-two-locals",
    _body(
        decls="""
    int  i;
    char had_zero;
    char saved_pad;
    int  saved_x;
""",
        init="""
    saved_pad = pad_char;
    saved_x   = x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            buf[i] = saved_pad;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &buf[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    buf[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            buf[i] = ' ';
        } else {
            int da = 10;
            buf[i] = (char)((value % da) + '0');
        }
    next:
        {
            int db = 10;
            value = value / db;
        }
    }
""",
        tail="""
    strip_leading_space((signed char *)buf);
    put_a_font_string(buf, saved_x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="two separately-scoped divisor locals",
)

# Pass through a self-modifying-looking helper.
exp.add(
    "div-via-global",
    _body(
        decls="""
    int  i;
    char had_zero;
    char saved_pad;
    int  saved_x;
    extern int g_ten;
""",
        init="""
    saved_pad = pad_char;
    saved_x   = x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            buf[i] = saved_pad;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &buf[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    buf[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            buf[i] = ' ';
        } else {
            buf[i] = (char)((value % g_ten) + '0');
        }
    next:
        value = value / g_ten;
    }
""",
        tail="""
    strip_leading_space((signed char *)buf);
    put_a_font_string(buf, saved_x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="divisor via extern global g_ten",
)

# Variant: use pad_char (param directly) inside the loop instead
# of saved_pad. saved_pad untouched so it lives in stack/reg.
exp.add(
    "pad-direct",
    _body(
        decls="""
    int  i;
    volatile int div10;
    char had_zero;
    int  saved_x;
""",
        init="""
    saved_x   = x;
    had_zero  = 0;
""",
        pad_loop="""
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            buf[i] = pad_char;
    }
""",
        suffix_loop="""
    i = 10;
    while (*suffix != 0) {
        char *dst = &buf[i];
        *dst = *suffix++;
        i++;
        if (i >= 16) break;
    }
    buf[i] = 0;
""",
        digit_loop="""
    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9) {
            if (!had_zero) {
                had_zero = 1;
                goto next;
            }
        }
        if (value <= 0 && i != 9 && had_zero) {
            buf[i] = ' ';
        } else {
            div10 = 10;
            buf[i] = (char)((value % div10) + '0');
        }
    next:
        div10 = 10;
        value = value / div10;
    }
""",
        tail="""
    strip_leading_space((signed char *)buf);
    put_a_font_string(buf, saved_x, y, font, color);
    font_screen_limit = 0;
""",
    ),
    note="use pad_char directly (no saved_pad)",
)
