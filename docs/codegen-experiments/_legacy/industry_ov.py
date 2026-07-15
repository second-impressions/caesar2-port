"""get_industry_ov_image — byte-register home of `industry` (DH vs AL).

PS packs kind->DL, industry->DH (both EDX halves) and re-extends kind per
comparison (`xor eax,eax; mov al,dl`).  Our build promotes kind to int in
EDX once (`and edx,0xff`) and puts industry in AL.  The root is industry's
byte home: PS DH (3rd in AH,AL,DH,DL,...), RC AL (2nd).  The exact sibling
get_admin_ov_image uses admin->AL (one kind check), so the divergence is the
TWO kind comparisons forcing PS to keep EAX as the per-branch extension
scratch (industry thus exiled to DH).

Run::  uv run c2 cgex run industry_ov
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="industry_ov",
    ps_function="get_industry_ov_image",
    chk=False,
    externs={},
    prelude="""
extern unsigned char city_map[];
extern unsigned char landfill_pool[];
extern int cm_sptr;
extern int cm_dptr;
""",
    extra_defs="""
unsigned char city_map[128000];
unsigned char landfill_pool[6400];
int cm_sptr;
int cm_dptr;
""",
)

# ── baseline: current source (kind decl first, ==0xfa branch first) ──
exp.add(
    "baseline",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="current source",
)

# ── declaration order: industry first ──
exp.add(
    "decl_industry_first",
    """
void get_industry_ov_image(void)
{
    unsigned char industry;
    unsigned char kind;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="industry declared before kind",
)

# ── load industry before kind ──
exp.add(
    "load_industry_first",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    kind = city_map[cm_sptr];
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="industry assigned before kind",
)

# ── range-first control flow (matches PS branch order) ──
exp.add(
    "range_first",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="range check first (PS order)",
)

# ── OR form, range first (single 0x96 store) ──
exp.add(
    "or_range_first",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if ((kind >= 0xfc && kind <= 0xff) || kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="OR, range first",
)

# ── OR form, ==0xfa first ──
exp.add(
    "or_fa_first",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind == 0xfa || (kind >= 0xfc && kind <= 0xff)) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="OR, ==0xfa first",
)

# ── explicit base pointer (keeps cm_sptr-base in a reg across both loads) ──
exp.add(
    "cell_ptr",
    """
void get_industry_ov_image(void)
{
    unsigned char *cell;
    unsigned char kind;
    unsigned char industry;
    cell = &city_map[cm_sptr];
    kind = cell[0];
    industry = cell[0xa] & 0xc0;
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="explicit base pointer for both loads",
)

# ── kind as int (movzx load, no byte for kind) ──
exp.add(
    "kind_int",
    """
void get_industry_ov_image(void)
{
    int kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="kind as int",
)

# ── industry as int ──
exp.add(
    "industry_int",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    int industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = (unsigned char)industry;
    }
}
""",
    note="industry as int",
)

# ── cell_ptr + range first ──
exp.add(
    "cell_range_first",
    """
void get_industry_ov_image(void)
{
    unsigned char *cell;
    unsigned char kind;
    unsigned char industry;
    cell = &city_map[cm_sptr];
    kind = cell[0];
    industry = cell[0xa] & 0xc0;
    if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="cell ptr + range first",
)

# ── baseline addressing (cm_sptr index) but defeat CSE: nested else ──
exp.add(
    "nested_fa_in_else",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else {
        if (kind == 0xfa) {
            landfill_pool[cm_dptr] = 0x96;
        } else if (industry != 0) {
            if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
            else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
            else landfill_pool[cm_dptr] = 0x8d;
        } else {
            landfill_pool[cm_dptr] = industry;
        }
    }
}
""",
    note="range first, ==fa nested in else",
)

# ── cell_ptr, industry compared as the masked byte each time (no kind int CSE) ──
exp.add(
    "cell_range_industry_byte",
    """
void get_industry_ov_image(void)
{
    unsigned char *cell;
    unsigned char kind;
    unsigned char industry;
    cell = &city_map[cm_sptr];
    kind = cell[0];
    industry = cell[0xa] & 0xc0;
    if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry == 0) {
        landfill_pool[cm_dptr] = industry;
    } else if (industry == 0x40) {
        landfill_pool[cm_dptr] = 0x93;
    } else if (industry == 0x80) {
        landfill_pool[cm_dptr] = 0x90;
    } else {
        landfill_pool[cm_dptr] = 0x8d;
    }
}
""",
    note="cell + range first + flat industry chain",
)

# ── range-first with early returns (matches PS ret-after-store) ──
exp.add(
    "range_first_early_ret",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
        return;
    }
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
        return;
    }
    if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="range first + early returns",
)

# ── ==0xfa first with early returns ──
exp.add(
    "fa_first_early_ret",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
        return;
    }
    if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
        return;
    }
    if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="==fa first + early returns",
)

# ── break kind-extension CSE: separate copy for the range check ──
exp.add(
    "kind_copy_range",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char kind2;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    kind2 = kind;
    if (kind2 >= 0xfc && kind2 <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="separate kind2 for range",
)

# ── re-read city_map for range branch (defeat CSE via reload) ──
exp.add(
    "reread_range",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (city_map[cm_sptr] >= 0xfc && city_map[cm_sptr] <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="re-read city_map in range branch",
)

# ── ==fa first, separate kind2 for range (no CSE), industry survives ──
exp.add(
    "fa_first_kind2",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char kind2;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else {
        kind2 = kind;
        if (kind2 >= 0xfc && kind2 <= 0xff) {
            landfill_pool[cm_dptr] = 0x96;
        } else if (industry != 0) {
            if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
            else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
            else landfill_pool[cm_dptr] = 0x8d;
        } else {
            landfill_pool[cm_dptr] = industry;
        }
    }
}
""",
    note="==fa first, kind2 for range in else",
)

# ── no kind var: inline city_map[cm_sptr], range first ──
exp.add(
    "no_kind_var",
    """
void get_industry_ov_image(void)
{
    unsigned char industry;
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (city_map[cm_sptr] >= 0xfc && city_map[cm_sptr] <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (city_map[cm_sptr] == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="inline kind reads, range first",
)

# ── switch on kind ──
exp.add(
    "switch_kind",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    switch (kind) {
    case 0xfa:
    case 0xfc:
    case 0xfd:
    case 0xfe:
    case 0xff:
        landfill_pool[cm_dptr] = 0x96;
        break;
    default:
        if (industry != 0) {
            if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
            else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
            else landfill_pool[cm_dptr] = 0x8d;
        } else {
            landfill_pool[cm_dptr] = industry;
        }
    }
}
""",
    note="switch on kind",
)

# ── industry compared via the masked field re-read, kind cached ──
exp.add(
    "fa_first_no_industry_cache",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    kind = city_map[cm_sptr];
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if ((city_map[cm_sptr + 0xa] & 0xc0) != 0) {
        if ((city_map[cm_sptr + 0xa] & 0xc0) == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if ((city_map[cm_sptr + 0xa] & 0xc0) == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = 0;
    }
}
""",
    note="kind cached, industry inlined",
)

# ── industry loaded AFTER kind checks (range first, early returns) ──
exp.add(
    "industry_late_range",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
        return;
    }
    if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
        return;
    }
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (industry != 0) {
        if (industry == 0x40) landfill_pool[cm_dptr] = 0x93;
        else if (industry == 0x80) landfill_pool[cm_dptr] = 0x90;
        else landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="industry loaded after kind checks, range first",
)

# ── industry loaded early but kind checks reference it (pin industry live early) ──
exp.add(
    "range_first_industry_early_used",
    """
void get_industry_ov_image(void)
{
    unsigned char kind;
    unsigned char industry;
    kind = city_map[cm_sptr];
    industry = city_map[cm_sptr + 0xa] & 0xc0;
    if (kind >= 0xfc && kind <= 0xff) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (kind == 0xfa) {
        landfill_pool[cm_dptr] = 0x96;
    } else if (industry == 0x40) {
        landfill_pool[cm_dptr] = 0x93;
    } else if (industry == 0x80) {
        landfill_pool[cm_dptr] = 0x90;
    } else if (industry != 0) {
        landfill_pool[cm_dptr] = 0x8d;
    } else {
        landfill_pool[cm_dptr] = industry;
    }
}
""",
    note="range first, flat industry chain",
)
