/*
 * Compiled-in game text: gettext .po -> the recovered Textfile/Helpfile
 * layouts, rebuilt in memory at startup. See c2_port_text.h and
 * tools/c2-text.py, whose `compile` command is the reference for what
 * this file produces.
 */
#include "c2_port_text.h"
#include "c2_host.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TEXT_GROUPS 147
#define TEXT_TABLE_END (8 + TEXT_GROUPS * 4)
#define HELP_PAGES 2000
#define HELP_RECORD 0x3a
#define HELP_TABLE_END (8 + HELP_PAGES * HELP_RECORD)
#define HELP_SLOTS 3
#define HELP_BREAK '$'
#define PO_STRING_CAPACITY 8192
#define PO_KEY_CAPACITY 64
#define ALIAS_DEPTH 16

/* The 1996 Textfile alias layout: group -> the group whose payload it shares. */
static int text_alias(int group)
{
    if (group == 117 || group == 118) return 116;
    if (group == 120) return 119;
    return 0;
}

struct help_record {
    short left_sprite;
    short right_sprite;
    short width;
    const char *left;
    const char *right;
    const char *voc;
};

static const struct help_record help_records[HELP_PAGES] = {
#include "c2_port_help_records.inc"
};

/* ---------------------------------------------------------------------- */
/* UTF-8 -> CP437 (the bitmap font's code points)                         */

static const unsigned short cp437_high[128] = {
    0x00C7, 0x00FC, 0x00E9, 0x00E2, 0x00E4, 0x00E0, 0x00E5, 0x00E7,
    0x00EA, 0x00EB, 0x00E8, 0x00EF, 0x00EE, 0x00EC, 0x00C4, 0x00C5,
    0x00C9, 0x00E6, 0x00C6, 0x00F4, 0x00F6, 0x00F2, 0x00FB, 0x00F9,
    0x00FF, 0x00D6, 0x00DC, 0x00A2, 0x00A3, 0x00A5, 0x20A7, 0x0192,
    0x00E1, 0x00ED, 0x00F3, 0x00FA, 0x00F1, 0x00D1, 0x00AA, 0x00BA,
    0x00BF, 0x2310, 0x00AC, 0x00BD, 0x00BC, 0x00A1, 0x00AB, 0x00BB,
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,
    0x2555, 0x2563, 0x2551, 0x2557, 0x255D, 0x255C, 0x255B, 0x2510,
    0x2514, 0x2534, 0x252C, 0x251C, 0x2500, 0x253C, 0x255E, 0x255F,
    0x255A, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256C, 0x2567,
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256B,
    0x256A, 0x2518, 0x250C, 0x2588, 0x2584, 0x258C, 0x2590, 0x2580,
    0x03B1, 0x00DF, 0x0393, 0x03C0, 0x03A3, 0x03C3, 0x00B5, 0x03C4,
    0x03A6, 0x0398, 0x03A9, 0x03B4, 0x221E, 0x03C6, 0x03B5, 0x2229,
    0x2261, 0x00B1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00F7, 0x2248,
    0x00B0, 0x2219, 0x00B7, 0x221A, 0x207F, 0x00B2, 0x25A0, 0x00A0
};

static unsigned char cp437_from_codepoint(unsigned int cp)
{
    int i;

    if (cp < 0x80) return (unsigned char)cp;
    for (i = 0; i < 128; i++) {
        if (cp437_high[i] == cp) return (unsigned char)(0x80 + i);
    }
    return '?';
}

/* Decode one UTF-8 sequence; returns its length (at least 1). */
static int utf8_decode(const unsigned char *s, size_t n, unsigned int *cp)
{
    unsigned char c = s[0];
    int len;
    int i;

    if (c < 0x80) { *cp = c; return 1; }
    if ((c & 0xE0) == 0xC0) { len = 2; *cp = c & 0x1F; }
    else if ((c & 0xF0) == 0xE0) { len = 3; *cp = c & 0x0F; }
    else if ((c & 0xF8) == 0xF0) { len = 4; *cp = c & 0x07; }
    else { *cp = '?'; return 1; }
    if ((size_t)len > n) { *cp = '?'; return 1; }
    for (i = 1; i < len; i++) {
        if ((s[i] & 0xC0) != 0x80) { *cp = '?'; return 1; }
        *cp = (*cp << 6) | (s[i] & 0x3F);
    }
    return len;
}

/* In place: UTF-8 text with "\n" -> CP437 bytes with the help line break.
 * Returns the new length. Newlines only occur in help text. */
static size_t transcode(char *text, size_t length)
{
    size_t in = 0;
    size_t out = 0;
    unsigned int cp;

    while (in < length) {
        in += (size_t)utf8_decode((const unsigned char *)text + in, length - in, &cp);
        if (cp == '\n') text[out++] = HELP_BREAK;
        else text[out++] = (char)cp437_from_codepoint(cp);
    }
    text[out] = '\0';
    return out;
}

/* ---------------------------------------------------------------------- */
/* .po parsing (msgctxt / msgid / msgstr, C escapes, fuzzy)               */

struct po_reader {
    const unsigned char *data;
    size_t size;
    size_t pos;
};

struct po_entry {
    char ctxt[PO_KEY_CAPACITY];
    char *msgid;
    char *msgstr;
    size_t msgid_length;
    size_t msgstr_length;
    int has_ctxt;
    int fuzzy;
};

static int po_next_line(struct po_reader *r, const char **line, size_t *length)
{
    size_t start = r->pos;
    size_t end;

    if (start >= r->size) return 0;
    end = start;
    while (end < r->size && r->data[end] != '\n') end++;
    *line = (const char *)r->data + start;
    *length = end - start;
    if (*length && (*line)[*length - 1] == '\r') (*length)--;
    r->pos = end + 1;
    return 1;
}

/* Append the unescaped content of one quoted "..." piece. */
static int po_unquote_append(const char *s, size_t n, char *out, size_t *out_length,
                             size_t capacity)
{
    size_t i;

    while (n && (s[0] == ' ' || s[0] == '\t')) { s++; n--; }
    while (n && (s[n - 1] == ' ' || s[n - 1] == '\t')) n--;
    if (n < 2 || s[0] != '"' || s[n - 1] != '"') return 0;
    for (i = 1; i + 1 < n; i++) {
        char c = s[i];
        if (c == '\\') {
            i++;
            if (i + 1 >= n) return 0;
            switch (s[i]) {
            case 'n': c = '\n'; break;
            case 't': c = '\t'; break;
            case 'r': c = '\r'; break;
            case '\\': c = '\\'; break;
            case '"': c = '"'; break;
            default: return 0;
            }
        }
        if (*out_length + 1 >= capacity) return 0;
        out[(*out_length)++] = c;
    }
    out[*out_length] = '\0';
    return 1;
}

static int contains(const char *s, size_t n, const char *word)
{
    size_t w = strlen(word);
    size_t i;

    for (i = 0; i + w <= n; i++) {
        if (memcmp(s + i, word, w) == 0) return 1;
    }
    return 0;
}

enum po_field { PO_NONE, PO_CTXT, PO_MSGID, PO_MSGSTR };

/* Read the next entry. Returns 1 on an entry, 0 at end, -1 on a syntax error. */
static int po_read_entry(struct po_reader *r, struct po_entry *e)
{
    const char *line;
    size_t length;
    enum po_field field = PO_NONE;
    int have = 0;
    int fuzzy = 0;
    char ctxt_tmp[PO_KEY_CAPACITY];
    size_t ctxt_length = 0;

    e->has_ctxt = 0;
    e->fuzzy = 0;
    e->msgid_length = 0;
    e->msgstr_length = 0;
    e->msgid[0] = '\0';
    e->msgstr[0] = '\0';
    e->ctxt[0] = '\0';
    ctxt_tmp[0] = '\0';

    for (;;) {
        size_t save = r->pos;
        if (!po_next_line(r, &line, &length)) break;
        if (length == 0) {
            if (have) break;
            continue;
        }
        if (line[0] == '#') {
            if (have) { r->pos = save; break; }
            if (length > 1 && line[1] == ',' && contains(line, length, "fuzzy"))
                fuzzy = 1;
            continue;
        }
        if (line[0] == '"') {
            int ok;
            if (field == PO_CTXT) ok = po_unquote_append(line, length, ctxt_tmp, &ctxt_length, sizeof(ctxt_tmp));
            else if (field == PO_MSGID) ok = po_unquote_append(line, length, e->msgid, &e->msgid_length, PO_STRING_CAPACITY);
            else if (field == PO_MSGSTR) ok = po_unquote_append(line, length, e->msgstr, &e->msgstr_length, PO_STRING_CAPACITY);
            else ok = 0;
            if (!ok) return -1;
            continue;
        }
        if (length > 8 && memcmp(line, "msgctxt ", 8) == 0) {
            if (have) { r->pos = save; break; }
            field = PO_CTXT;
            e->has_ctxt = 1;
            if (!po_unquote_append(line + 8, length - 8, ctxt_tmp, &ctxt_length, sizeof(ctxt_tmp))) return -1;
        } else if (length > 6 && memcmp(line, "msgid ", 6) == 0) {
            if (field == PO_MSGSTR) { r->pos = save; break; }
            field = PO_MSGID;
            have = 1;
            if (!po_unquote_append(line + 6, length - 6, e->msgid, &e->msgid_length, PO_STRING_CAPACITY)) return -1;
        } else if (length > 7 && memcmp(line, "msgstr ", 7) == 0) {
            field = PO_MSGSTR;
            have = 1;
            if (!po_unquote_append(line + 7, length - 7, e->msgstr, &e->msgstr_length, PO_STRING_CAPACITY)) return -1;
        } else {
            return -1;
        }
    }
    if (!have) return 0;
    memcpy(e->ctxt, ctxt_tmp, ctxt_length + 1);
    e->fuzzy = fuzzy;
    return 1;
}

/* Value of a "Key: value" line in a po header msgstr. */
static int po_header_value(const char *header, const char *key, char *out, size_t capacity)
{
    const char *p = header;
    size_t key_length = strlen(key);

    while (p && *p) {
        const char *end = strchr(p, '\n');
        size_t line_length = end ? (size_t)(end - p) : strlen(p);
        if (line_length > key_length + 1 && memcmp(p, key, key_length) == 0 && p[key_length] == ':') {
            const char *v = p + key_length + 1;
            size_t n;
            while (*v == ' ') v++;
            n = line_length - (size_t)(v - p);
            if (n + 1 > capacity) n = capacity - 1;
            memcpy(out, v, n);
            out[n] = '\0';
            return 1;
        }
        p = end ? end + 1 : NULL;
    }
    return 0;
}

/* ---------------------------------------------------------------------- */
/* Language table                                                         */

#define LANGUAGE_CAPACITY 16
#define NAME_CAPACITY 48

static struct c2_port_language languages[LANGUAGE_CAPACITY];
static char language_names[LANGUAGE_CAPACITY][NAME_CAPACITY];
static char language_detects[LANGUAGE_CAPACITY][NAME_CAPACITY];
static int language_count = -1;
static char selected_tag[16];
static char effective_tag[16];

static void load_language_table(void)
{
    int i;
    struct po_reader r;
    struct po_entry e;

    if (language_count >= 0) return;
    language_count = 0;
    e.msgid = malloc(PO_STRING_CAPACITY);
    e.msgstr = malloc(PO_STRING_CAPACITY);
    if (!e.msgid || !e.msgstr) { free(e.msgid); free(e.msgstr); return; }
    for (i = 0; i < c2_text_bundle_count && language_count < LANGUAGE_CAPACITY; i++) {
        r.data = c2_text_bundle[i].data;
        r.size = c2_text_bundle[i].size;
        r.pos = 0;
        if (po_read_entry(&r, &e) != 1 || e.has_ctxt || e.msgid_length != 0) continue;
        languages[language_count].tag = c2_text_bundle[i].tag;
        if (!po_header_value(e.msgstr, "X-C2-Name", language_names[language_count], NAME_CAPACITY))
            snprintf(language_names[language_count], NAME_CAPACITY, "%s", c2_text_bundle[i].tag);
        if (!po_header_value(e.msgstr, "X-C2-Detect", language_detects[language_count], NAME_CAPACITY))
            language_detects[language_count][0] = '\0';
        transcode(language_detects[language_count], strlen(language_detects[language_count]));
        languages[language_count].name = language_names[language_count];
        languages[language_count].detect = language_detects[language_count];
        language_count++;
    }
    free(e.msgid);
    free(e.msgstr);
}

int c2_port_text_language_count(void)
{
    load_language_table();
    return language_count;
}

const struct c2_port_language *c2_port_text_language(int index)
{
    load_language_table();
    if (index < 0 || index >= language_count) return NULL;
    return &languages[index];
}

static int language_index(const char *tag)
{
    int i;

    load_language_table();
    if (!tag) return -1;
    for (i = 0; i < language_count; i++) {
        if (strcmp(languages[i].tag, tag) == 0) return i;
    }
    return -1;
}

int c2_port_text_select(const char *tag)
{
    if (tag && language_index(tag) < 0) return 0;
    snprintf(selected_tag, sizeof(selected_tag), "%s", tag ? tag : "");
    effective_tag[0] = '\0';
    c2_port_text_shutdown();
    return 1;
}

const char *c2_port_text_detect(const unsigned char *c2eng, size_t size)
{
    unsigned int offset;
    size_t n;
    int i;

    load_language_table();
    /* The detect string is the first string of group 1 (the File menu). */
    if (size < 16 || memcmp(c2eng, "Textfile", 8) != 0) return NULL;
    offset = c2eng[12] | (unsigned int)c2eng[13] << 8 | (unsigned int)c2eng[14] << 16;
    if (offset >= size) return NULL;
    n = 0;
    while (offset + n < size && c2eng[offset + n] != 0) n++;
    for (i = 0; i < language_count; i++) {
        if (languages[i].detect[0] && strlen(languages[i].detect) == n &&
            memcmp(languages[i].detect, c2eng + offset, n) == 0)
            return languages[i].tag;
    }
    return NULL;
}

const char *c2_port_text_selected(void)
{
    unsigned char *probe;
    size_t n;
    const char *tag;

    load_language_table();
    if (selected_tag[0]) return selected_tag;
    if (effective_tag[0]) return effective_tag;
    tag = NULL;
    probe = malloc(1024);
    if (probe) {
        n = c2_host_asset_read("C2.ENG", probe, 1024, 0);
        if (n) tag = c2_port_text_detect(probe, n);
        free(probe);
    }
    if (!tag || language_index(tag) < 0) tag = language_count ? languages[0].tag : "en";
    snprintf(effective_tag, sizeof(effective_tag), "%s", tag);
    return effective_tag;
}

/* ---------------------------------------------------------------------- */
/* The model: text strings by (group, index); help pages by page/slot     */

struct text_string {
    unsigned short group;
    unsigned short index;
    char *value;
};

struct help_page {
    short alias;               /* > 0: same text as that page */
    char *slot[HELP_SLOTS];
};

static struct text_string *text_strings;
static size_t text_string_count;
static size_t text_string_capacity;
static struct help_page help_pages[HELP_PAGES];
static unsigned char *built_c2eng;
static size_t built_c2eng_size;
static unsigned char *built_help;
static size_t built_help_size;
static int built;

static char *dup_bytes(const char *s, size_t n)
{
    char *copy = malloc(n + 1);
    if (!copy) return NULL;
    memcpy(copy, s, n);
    copy[n] = '\0';
    return copy;
}

static int add_text_string(int group, int index, const char *value, size_t n)
{
    struct text_string *grown;

    if (text_string_count == text_string_capacity) {
        size_t capacity = text_string_capacity ? text_string_capacity * 2 : 1536;
        grown = realloc(text_strings, capacity * sizeof(*grown));
        if (!grown) return 0;
        text_strings = grown;
        text_string_capacity = capacity;
    }
    text_strings[text_string_count].group = (unsigned short)group;
    text_strings[text_string_count].index = (unsigned short)index;
    text_strings[text_string_count].value = dup_bytes(value, n);
    if (!text_strings[text_string_count].value) return 0;
    text_string_count++;
    return 1;
}

static int compare_text_strings(const void *a, const void *b)
{
    const struct text_string *x = a;
    const struct text_string *y = b;
    if (x->group != y->group) return (int)x->group - (int)y->group;
    return (int)x->index - (int)y->index;
}

static void free_model(void)
{
    size_t i;
    int p;
    int s;

    for (i = 0; i < text_string_count; i++) free(text_strings[i].value);
    free(text_strings);
    text_strings = NULL;
    text_string_count = text_string_capacity = 0;
    for (p = 0; p < HELP_PAGES; p++) {
        help_pages[p].alias = 0;
        for (s = 0; s < HELP_SLOTS; s++) {
            free(help_pages[p].slot[s]);
            help_pages[p].slot[s] = NULL;
        }
    }
}

/* Parse "0x2f/3" or "help/12/0". */
static int parse_key(const char *ctxt, int *kind, int *a, int *b)
{
    char *end;
    long x;
    long y;

    if (strncmp(ctxt, "help/", 5) == 0) {
        x = strtol(ctxt + 5, &end, 10);
        if (*end != '/' || x <= 0 || x >= HELP_PAGES) return 0;
        y = strtol(end + 1, &end, 10);
        if (*end || y < 0 || y >= HELP_SLOTS) return 0;
        *kind = 1;
    } else {
        x = strtol(ctxt, &end, 16);
        if (*end != '/' || x <= 0 || x >= TEXT_GROUPS) return 0;
        y = strtol(end + 1, &end, 10);
        if (*end || y < 0 || y > 0xffff) return 0;
        *kind = 0;
    }
    *a = (int)x;
    *b = (int)y;
    return 1;
}

static int load_model(const char *tag)
{
    int i = language_index(tag);
    struct po_reader r;
    struct po_entry e;
    int status;
    int ok = 1;

    if (i < 0) return 0;
    free_model();
    e.msgid = malloc(PO_STRING_CAPACITY);
    e.msgstr = malloc(PO_STRING_CAPACITY);
    if (!e.msgid || !e.msgstr) { free(e.msgid); free(e.msgstr); return 0; }
    r.data = c2_text_bundle[i].data;
    r.size = c2_text_bundle[i].size;
    r.pos = 0;
    while ((status = po_read_entry(&r, &e)) == 1) {
        const char *value;
        size_t n;
        int kind;
        int a;
        int b;

        if (!e.has_ctxt) continue;
        if (!parse_key(e.ctxt, &kind, &a, &b)) continue;
        if (e.msgstr_length && !e.fuzzy) { value = e.msgstr; n = e.msgstr_length; }
        else { value = e.msgid; n = e.msgid_length; }
        n = transcode((char *)value, n);
        if (kind == 0) {
            if (!add_text_string(a, b, value, n)) { ok = 0; break; }
        } else {
            if (n >= 2 && value[0] == '@') {
                long target = strtol(value + 1, NULL, 10);
                if (target > 0 && target < HELP_PAGES) help_pages[a].alias = (short)target;
            } else {
                free(help_pages[a].slot[b]);
                help_pages[a].slot[b] = dup_bytes(value, n);
                if (!help_pages[a].slot[b]) { ok = 0; break; }
            }
        }
    }
    if (status < 0) {
        fprintf(stderr, "caesar2: bundled text for '%s' is malformed near byte %lu\n",
                tag, (unsigned long)r.pos);
        ok = 0;
    }
    free(e.msgid);
    free(e.msgstr);
    if (ok) qsort(text_strings, text_string_count, sizeof(*text_strings), compare_text_strings);
    return ok;
}

/* ---------------------------------------------------------------------- */
/* Builders                                                               */

static void put_u32(unsigned char *p, unsigned int v)
{
    p[0] = (unsigned char)v;
    p[1] = (unsigned char)(v >> 8);
    p[2] = (unsigned char)(v >> 16);
    p[3] = (unsigned char)(v >> 24);
}

static void put_u16(unsigned char *p, int v)
{
    p[0] = (unsigned char)v;
    p[1] = (unsigned char)(v >> 8);
}

static int build_c2eng(void)
{
    size_t total = TEXT_TABLE_END;
    size_t i;
    int g;
    unsigned int offsets[TEXT_GROUPS];
    unsigned char *out;
    size_t pos;

    /* Each payload is its strings NUL-terminated; a group without any
     * holds one empty string. */
    for (g = 1, i = 0; g < TEXT_GROUPS; g++) {
        if (text_alias(g)) continue;
        if (i >= text_string_count || text_strings[i].group != g) {
            total += 1;
            continue;
        }
        while (i < text_string_count && text_strings[i].group == g) {
            total += strlen(text_strings[i].value) + 1;
            i++;
        }
    }
    out = malloc(total);
    if (!out) return 0;
    memcpy(out, "Textfile", 8);
    pos = TEXT_TABLE_END;
    offsets[0] = 0;
    for (g = 1, i = 0; g < TEXT_GROUPS; g++) {
        if (text_alias(g)) {
            offsets[g] = offsets[text_alias(g)];
            continue;
        }
        offsets[g] = (unsigned int)pos;
        if (i >= text_string_count || text_strings[i].group != g) {
            out[pos++] = 0;
            continue;
        }
        while (i < text_string_count && text_strings[i].group == g) {
            size_t n = strlen(text_strings[i].value);
            memcpy(out + pos, text_strings[i].value, n);
            pos += n;
            out[pos++] = 0;
            i++;
        }
    }
    for (g = 0; g < TEXT_GROUPS; g++) put_u32(out + 8 + g * 4, offsets[g]);
    built_c2eng = out;
    built_c2eng_size = pos;
    return 1;
}

static const struct help_page *resolve_help_page(int page, int *resolved)
{
    int depth;

    for (depth = 0; depth < ALIAS_DEPTH; depth++) {
        if (page <= 0 || page >= HELP_PAGES) return NULL;
        if (help_pages[page].alias == 0) {
            if (!help_pages[page].slot[0]) return NULL;
            *resolved = page;
            return &help_pages[page];
        }
        page = help_pages[page].alias;
    }
    return NULL;
}

static int build_help(void)
{
    unsigned int offsets[HELP_PAGES];
    size_t total = HELP_TABLE_END;
    unsigned char *out;
    size_t pos;
    int page;
    int s;

    for (page = 0; page < HELP_PAGES; page++) {
        offsets[page] = 0;
        if (help_pages[page].alias) continue;
        for (s = 0; s < HELP_SLOTS && help_pages[page].slot[s]; s++)
            total += strlen(help_pages[page].slot[s]) + 1;
    }
    out = calloc(total, 1);
    if (!out) return 0;
    memcpy(out, "Helpfile", 8);
    pos = HELP_TABLE_END;
    for (page = 1; page < HELP_PAGES; page++) {
        if (help_pages[page].alias || !help_pages[page].slot[0]) continue;
        offsets[page] = (unsigned int)pos;
        for (s = 0; s < HELP_SLOTS && help_pages[page].slot[s]; s++) {
            size_t n = strlen(help_pages[page].slot[s]);
            memcpy(out + pos, help_pages[page].slot[s], n);
            pos += n;
            out[pos++] = 0;
        }
    }
    for (page = 0; page < HELP_PAGES; page++) {
        unsigned char *rec = out + 8 + page * HELP_RECORD;
        const struct help_record *r = &help_records[page];
        int resolved = 0;
        unsigned int offset = 0;
        if (page > 0 && resolve_help_page(page, &resolved)) offset = offsets[resolved];
        put_u32(rec, offset);
        put_u16(rec + 4, r->left_sprite);
        put_u16(rec + 6, r->right_sprite);
        put_u16(rec + 8, r->width);
        snprintf((char *)rec + 10, 16, "%s", r->left);
        snprintf((char *)rec + 26, 16, "%s", r->right);
        snprintf((char *)rec + 42, 16, "%s", r->voc);
    }
    built_help = out;
    built_help_size = pos;
    return 1;
}

static int ensure_built(void)
{
    const char *tag;

    if (built) return built > 0;
    tag = c2_port_text_selected();
    if (!load_model(tag) || !build_c2eng() || !build_help()) {
        fprintf(stderr, "caesar2: could not build the '%s' game text\n", tag);
        free_model();
        built = -1;
        return 0;
    }
    free_model();
    built = 1;
    return 1;
}

void c2_port_text_shutdown(void)
{
    free(built_c2eng);
    free(built_help);
    built_c2eng = built_help = NULL;
    built_c2eng_size = built_help_size = 0;
    built = 0;
}

const unsigned char *c2_port_text_c2eng(size_t *size)
{
    if (!ensure_built()) return NULL;
    *size = built_c2eng_size;
    return built_c2eng;
}

const unsigned char *c2_port_text_helpeng(size_t *size)
{
    if (!ensure_built()) return NULL;
    *size = built_help_size;
    return built_help;
}

/* ---------------------------------------------------------------------- */
/* readfile() hooks                                                       */

static int name_matches(const char *filename, const char *stem)
{
    const char *base = filename;
    const char *p;
    size_t n = strlen(stem);
    size_t i;

    for (p = filename; *p; p++) if (*p == '/' || *p == '\\') base = p + 1;
    for (i = 0; i < n; i++) {
        char c = base[i];
        if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
        if (c != stem[i]) return 0;
    }
    if (base[n] != '.') return 0;
    /* c2.eng, c2.ger, c2.fre, c2.spa: every name set_language() knows */
    return strlen(base) == n + 4;
}

int c2_port_text_is_language_file(const char *filename)
{
    return filename && name_matches(filename, "c2");
}

int c2_port_text_is_help_file(const char *filename)
{
    return filename && name_matches(filename, "help");
}

int c2_port_text_read(const char *filename, void *buffer, size_t size,
                      size_t offset, size_t *bytes_read)
{
    const unsigned char *data;
    size_t data_size;

    *bytes_read = 0;
    if (c2_port_text_is_language_file(filename)) data = c2_port_text_c2eng(&data_size);
    else if (c2_port_text_is_help_file(filename)) data = c2_port_text_helpeng(&data_size);
    else return 0;
    if (!data || offset >= data_size) return 1;
    if (size > data_size - offset) size = data_size - offset;
    memcpy(buffer, data + offset, size);
    *bytes_read = size;
    return 1;
}
