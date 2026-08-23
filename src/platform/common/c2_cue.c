#include "c2_import.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>

#define C2_RAW_SECTOR_SIZE 2352u
#define C2_ISO_SECTOR_SIZE 2048u

static const unsigned char c2_cd_sync[12] = {
    0x00, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xff, 0xff, 0xff, 0xff, 0xff, 0x00
};

static void set_error(char *error, size_t capacity, const char *message)
{
    if (error == NULL || capacity == 0) return;
    snprintf(error, capacity, "%s", message);
}

static int starts_word(const char *line, const char *word)
{
    while (*word != '\0') {
        if (toupper((unsigned char)*line++) !=
            toupper((unsigned char)*word++)) return 0;
    }
    return *line == '\0' || isspace((unsigned char)*line);
}

int c2_cue_parse_single_data_track(const char *cue,
                                   char *bin_name, size_t bin_name_capacity,
                                   enum c2_cd_sector_mode *mode,
                                   char *error, size_t error_capacity)
{
    const char *cursor;
    int files;
    int tracks;
    int indexes;
    enum c2_cd_sector_mode selected;

    if (cue == NULL || bin_name == NULL || bin_name_capacity == 0 ||
        mode == NULL) return 0;
    bin_name[0] = '\0';
    files = tracks = indexes = 0;
    selected = 0;
    cursor = cue;
    while (*cursor != '\0') {
        const char *end = strchr(cursor, '\n');
        const char *line = cursor;
        size_t length = end == NULL ? strlen(cursor) : (size_t)(end - cursor);
        char temp[1024];
        char *p;

        if (length >= sizeof(temp)) {
            set_error(error, error_capacity, "CUE line is too long");
            return 0;
        }
        memcpy(temp, line, length);
        temp[length] = '\0';
        if (length != 0 && temp[length - 1] == '\r') temp[length - 1] = '\0';
        p = temp;
        while (isspace((unsigned char)*p)) p++;
        if (starts_word(p, "FILE")) {
            char quote;
            char *start;
            char *finish;
            size_t name_length;
            p += 4;
            while (isspace((unsigned char)*p)) p++;
            quote = *p == '"' ? *p++ : 0;
            start = p;
            finish = quote ? strchr(start, quote) : start;
            if (!quote) {
                while (*finish != '\0' && !isspace((unsigned char)*finish)) finish++;
            }
            if (finish == NULL || finish == start) {
                set_error(error, error_capacity, "invalid CUE FILE line");
                return 0;
            }
            name_length = (size_t)(finish - start);
            if (name_length >= bin_name_capacity) {
                set_error(error, error_capacity, "CUE filename is too long");
                return 0;
            }
            memcpy(bin_name, start, name_length);
            bin_name[name_length] = '\0';
            files++;
        } else if (starts_word(p, "TRACK")) {
            tracks++;
            if (strstr(p, "MODE1/2352") != NULL) selected = C2_CD_MODE1_2352;
            else if (strstr(p, "MODE2/2352") != NULL) selected = C2_CD_MODE2_2352;
            else {
                set_error(error, error_capacity, "unsupported CUE track mode");
                return 0;
            }
        } else if (starts_word(p, "INDEX")) {
            if (strstr(p, "01 00:00:00") == NULL) {
                set_error(error, error_capacity, "unsupported CUE track index");
                return 0;
            }
            indexes++;
        }
        cursor = end == NULL ? cursor + strlen(cursor) : end + 1;
    }
    if (files != 1 || tracks != 1 || indexes != 1 || selected == 0) {
        set_error(error, error_capacity,
                  "CUE must contain one BIN and one data track at 00:00:00");
        return 0;
    }
    *mode = selected;
    return 1;
}

static int raw_read_exact(const struct c2_source_reader *raw, uint64_t offset,
                          void *buffer, size_t size)
{
    size_t done = 0;
    while (done < size) {
        size_t got = 0;
        if (!raw->read_at(raw->userdata, offset + done,
                          (unsigned char *)buffer + done,
                          size - done, &got) || got == 0) return 0;
        done += got;
    }
    return 1;
}

int c2_raw_cd_reader_init(struct c2_raw_cd_reader *reader,
                          const struct c2_source_reader *raw,
                          enum c2_cd_sector_mode mode,
                          char *error, size_t error_capacity)
{
    unsigned char first[C2_RAW_SECTOR_SIZE];
    if (reader == NULL || raw == NULL || raw->read_at == NULL ||
        (mode != C2_CD_MODE1_2352 && mode != C2_CD_MODE2_2352)) return 0;
    if (raw->size == 0 || raw->size % C2_RAW_SECTOR_SIZE != 0) {
        set_error(error, error_capacity, "BIN size is not a whole number of raw sectors");
        return 0;
    }
    if (!raw_read_exact(raw, 0, first, sizeof(first)) ||
        memcmp(first, c2_cd_sync, sizeof(c2_cd_sync)) != 0 ||
        first[15] != (unsigned char)mode) {
        set_error(error, error_capacity, "BIN sector framing does not match CUE mode");
        return 0;
    }
    reader->raw = *raw;
    reader->mode = mode;
    return 1;
}

static int raw_cd_read_at(void *userdata, uint64_t offset,
                          void *buffer, size_t size, size_t *read_out)
{
    struct c2_raw_cd_reader *reader = userdata;
    unsigned char raw[C2_RAW_SECTOR_SIZE];
    unsigned char *out = buffer;
    uint64_t logical_size;
    size_t done = 0;
    size_t payload_offset = reader->mode == C2_CD_MODE1_2352 ? 16u : 24u;

    logical_size = (reader->raw.size / C2_RAW_SECTOR_SIZE) * C2_ISO_SECTOR_SIZE;
    if (read_out != NULL) *read_out = 0;
    if (offset > logical_size) return 0;
    if ((uint64_t)size > logical_size - offset) size = (size_t)(logical_size - offset);
    while (done < size) {
        uint64_t logical = offset + done;
        uint64_t sector = logical / C2_ISO_SECTOR_SIZE;
        size_t within = (size_t)(logical % C2_ISO_SECTOR_SIZE);
        size_t chunk = C2_ISO_SECTOR_SIZE - within;
        if (chunk > size - done) chunk = size - done;
        if (!raw_read_exact(&reader->raw, sector * C2_RAW_SECTOR_SIZE,
                            raw, sizeof(raw)) ||
            memcmp(raw, c2_cd_sync, sizeof(c2_cd_sync)) != 0 ||
            raw[15] != (unsigned char)reader->mode) {
            return 0;
        }
        memcpy(out + done, raw + payload_offset + within, chunk);
        done += chunk;
    }
    if (read_out != NULL) *read_out = done;
    return 1;
}

void c2_raw_cd_source(struct c2_raw_cd_reader *reader,
                      struct c2_source_reader *source)
{
    source->userdata = reader;
    source->size = (reader->raw.size / C2_RAW_SECTOR_SIZE) * C2_ISO_SECTOR_SIZE;
    source->read_at = raw_cd_read_at;
}
