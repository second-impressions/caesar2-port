"""DecodeChar — index/base register choice on son[c].

PS: `and edx,0xffff; mov eax,[son]; mov dx,[eax+edx*2]` (c-index kept in
edx, son base loaded into eax).
RC: `xor eax,eax; mov ax,dx; mov edx,[son]; mov dx,[edx+eax*2]`
(c moved to eax, son base into edx).
Probe source shapes that keep c in its home register as the index.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="decodechar",
    ps_function="DecodeChar",
    externs={
        "GetBit": "extern int GetBit(void);",
        "update": "extern void update(short c);",
    },
    extra_defs="short *son;\n",
    prelude="extern short *son;\n",
)


def fn(decl, loop):
    return f"""
unsigned int DecodeChar(void)
{{
    {decl}
    c = ((unsigned short *)son)[0x272];
    while (c < 0x273) {{
{loop}
    }}
    c -= 0x273;
    update((short)c);
    return (unsigned int)c;
}}
"""


exp.add("baseline", fn(
    "unsigned short c;",
    "        c += (unsigned short)GetBit();\n"
    "        c = ((unsigned short *)son)[c];"),
    note="current source")

exp.add("mask_idx", fn(
    "unsigned short c;",
    "        c += (unsigned short)GetBit();\n"
    "        c = ((unsigned short *)son)[c & 0xffff];"),
    note="explicit & 0xffff on index")

exp.add("uint_mask", fn(
    "unsigned int c;",
    "        c = (c + (unsigned int)(unsigned short)GetBit()) & 0xffff;\n"
    "        c = ((unsigned short *)son)[c];"),
    note="uint c, mask the sum, plain index")

exp.add("uint_idxmask", fn(
    "unsigned int c;",
    "        c += (unsigned short)GetBit();\n"
    "        c = ((unsigned short *)son)[c & 0xffff];"),
    note="uint c, mask only at index")

exp.add("ptr_idx", fn(
    "unsigned short c; unsigned short *sp;",
    "        c += (unsigned short)GetBit();\n"
    "        sp = (unsigned short *)son;\n"
    "        c = sp[c];"),
    note="load son into local before index")

exp.add("sep_add", fn(
    "unsigned short c; int b;",
    "        b = GetBit();\n"
    "        c = (unsigned short)(c + b);\n"
    "        c = ((unsigned short *)son)[c];"),
    note="separate GetBit into b, cast sum")
