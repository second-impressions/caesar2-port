#include "c2_import.h"

#include <SDL3/SDL.h>

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define C2_PACK_PATH_CAPACITY 4096
#define C2_PACK_LINE_CAPACITY 2048
#define C2_PACK_COMPONENT_CAPACITY 32

static void set_error(char *error, size_t capacity, const char *message)
{
    if (error && capacity) snprintf(error, capacity, "%s", message);
}

static int safe_relative(const char *path)
{
    const char *p = path;
    if (!p || !*p || *p == '/' || *p == '\\' || strchr(p, ':')) return 0;
    while (*p) {
        const char *start;
        size_t n;
        while (*p == '/' || *p == '\\') p++;
        start = p;
        while (*p && *p != '/' && *p != '\\') {
            unsigned char c = (unsigned char)*p++;
            if (c < 0x20 || c >= 0x7f) return 0;
        }
        n = (size_t)(p - start);
        if (!n || (n == 1 && start[0] == '.') ||
            (n == 2 && start[0] == '.' && start[1] == '.')) return 0;
    }
    return 1;
}

static int selected(char components[][128], size_t count, const char *name)
{
    size_t i;
    for (i = 0; i < count; i++) if (strcmp(components[i], name) == 0) return 1;
    return 0;
}

int c2_pack_activate(const char *pack_root, const char *profile,
                     char *active_root, size_t active_root_capacity,
                     char *error, size_t error_capacity)
{
    char index_path[C2_PACK_PATH_CAPACITY];
    char selected_profile[128] = {0};
    char components[C2_PACK_COMPONENT_CAPACITY][128];
    size_t component_count = 0;
    char line[C2_PACK_LINE_CAPACITY];
    FILE *index;
    char current_component[128] = {0};
    int header = 0;
    FILE *map = NULL;

    if (snprintf(index_path, sizeof(index_path), "%s/C2PACK.IDX", pack_root) >= (int)sizeof(index_path)) return 0;
    index = fopen(index_path, "rb");
    if (!index) { set_error(error, error_capacity, "asset pack index is missing"); return 0; }
    while (fgets(line, sizeof(line), index)) {
        char *kind = strtok(line, "\t\r\n");
        char *name = strtok(NULL, "\t\r\n");
        char *values = strtok(NULL, "\t\r\n");
        if (!kind) continue;
        if (!header) {
            if (strcmp(kind, "C2PACK1") != 0) { fclose(index); set_error(error, error_capacity, "unsupported asset pack index"); return 0; }
            header = 1; continue;
        }
        if (strcmp(kind, "DEFAULT_LANGUAGE") == 0 && name && (!profile || !*profile)) {
            snprintf(selected_profile, sizeof(selected_profile), "%s", name);
        } else if (strcmp(kind, "PROFILE") == 0 && name && values) {
            const char *wanted = profile && *profile ? profile : selected_profile;
            if (strcmp(name, wanted) == 0) {
                char *value = strtok(values, ",");
                while (value && component_count < C2_PACK_COMPONENT_CAPACITY) {
                    snprintf(components[component_count++], sizeof(components[0]), "%s", value);
                    value = strtok(NULL, ",");
                }
            }
        }
    }
    if (!header || component_count == 0) { fclose(index); set_error(error, error_capacity, "asset pack profile was not found"); return 0; }
    rewind(index);
    if (snprintf(active_root, active_root_capacity, "%s/ACTIVE-%s", pack_root,
                 profile && *profile ? profile : selected_profile) >= (int)active_root_capacity ||
        (!SDL_CreateDirectory(active_root) && !SDL_GetPathInfo(active_root, NULL))) {
        fclose(index); set_error(error, error_capacity, "could not create active asset view"); return 0;
    }
    {
        char map_path[C2_PACK_PATH_CAPACITY];
        if (snprintf(map_path, sizeof(map_path), "%s/.c2-object-map", active_root) >= (int)sizeof(map_path)) {
            fclose(index); return 0;
        }
        map = fopen(map_path, "wb");
        if (!map) { fclose(index); set_error(error, error_capacity, "could not create active object map"); return 0; }
    }
    while (fgets(line, sizeof(line), index)) {
        char *kind = strtok(line, "\t\r\n");
        char *first = strtok(NULL, "\t\r\n");
        char *second = strtok(NULL, "\t\r\n");
        if (!kind) continue;
        if (strcmp(kind, "COMPONENT") == 0 && first) {
            snprintf(current_component, sizeof(current_component), "%s", first);
        } else if (strcmp(kind, "FILE") == 0 && first && second &&
                   selected(components, component_count, current_component)) {
            char source[C2_PACK_PATH_CAPACITY];
            SDL_PathInfo info;
            if (!safe_relative(first) || !safe_relative(second) ||
                snprintf(source, sizeof(source), "%s/OBJECTS/%s", pack_root, second) >= (int)sizeof(source) ||
                !SDL_GetPathInfo(source, &info) || info.type != SDL_PATHTYPE_FILE ||
                fprintf(map, "%s\t../OBJECTS/%s\n", first, second) < 0) {
                fclose(map); fclose(index); set_error(error, error_capacity, "could not activate asset-pack object"); return 0;
            }
        }
    }
    if (fclose(map) != 0) { fclose(index); return 0; }
    fclose(index);
    return 1;
}
