/* Direct CD-ROM drive access for game-data import.
 *
 * A data disc in a real drive presents the same 2048-byte logical sectors
 * as a plain ISO image, so this file only supplies a device-backed
 * c2_source_reader; cataloguing and extraction reuse the in-tree ISO-9660
 * reader.  Devices need sector-aligned transfers (mandatory on Windows
 * volume handles and macOS raw disks), so every read is bounced through
 * whole sectors.  The logical size and the cache fingerprint both come
 * from the primary volume descriptor because device nodes report neither
 * a useful st_size nor a stable identity for the inserted disc.
 */

#include "c2_import.h"

#include <stdio.h>
#include <string.h>

#define C2_CDROM_SECTOR 2048u
#define C2_CDROM_MAX_DESCRIPTORS 240u

static void set_error(char *error, size_t capacity, const char *message)
{
    if (error && capacity) snprintf(error, capacity, "%s", message);
}

#if PORT_PLATFORM_WASM

int c2_cdrom_is_device_path(const char *path)
{
    (void)path;
    return 0;
}

int c2_cdrom_open(const char *path, struct c2_cdrom_reader *reader,
                  char *error, size_t error_capacity)
{
    (void)path;
    if (reader) memset(reader, 0, sizeof(*reader));
    set_error(error, error_capacity,
              "CD-ROM drives cannot be read from the browser");
    return 0;
}

void c2_cdrom_close(struct c2_cdrom_reader *reader)
{
    (void)reader;
}

int c2_cdrom_find_drives(char paths[][C2_CDROM_DRIVE_PATH_CAPACITY], int max)
{
    (void)paths; (void)max;
    return 0;
}

int c2_cdrom_drive_has_disc(const char *path)
{
    (void)path;
    return 0;
}

#else /* native */

static uint32_t read_le32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

#if PORT_PLATFORM_WIN32

#include <windows.h>

#include <ctype.h>

/* Accept "\\.\X:" directly, plus "X:", "X:\" and "X:/" when the drive is
 * an optical drive; a mounted data disc root would otherwise be imported
 * in place as a directory, forcing the disc to stay in the drive. */
static int device_letter_path(const char *path, char *device, size_t capacity)
{
    if (path[0] == '\\' && path[1] == '\\' && path[2] == '.' &&
        path[3] == '\\' && isalpha((unsigned char)path[4]) &&
        path[5] == ':' && path[6] == '\0') {
        snprintf(device, capacity, "%s", path);
        return 1;
    }
    if (isalpha((unsigned char)path[0]) && path[1] == ':' &&
        (path[2] == '\0' ||
         ((path[2] == '\\' || path[2] == '/') && path[3] == '\0'))) {
        char root[4] = { path[0], ':', '\\', '\0' };
        if (GetDriveTypeA(root) != DRIVE_CDROM) return 0;
        snprintf(device, capacity, "\\\\.\\%c:", path[0]);
        return 1;
    }
    return 0;
}

int c2_cdrom_is_device_path(const char *path)
{
    char device[8];
    return path != NULL && device_letter_path(path, device, sizeof(device));
}

static int cdrom_open_handle(struct c2_cdrom_reader *reader, const char *path)
{
    char device[8];
    HANDLE handle;
    if (!device_letter_path(path, device, sizeof(device))) return 0;
    handle = CreateFileA(device, GENERIC_READ,
                         FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
                         OPEN_EXISTING, 0, NULL);
    if (handle == INVALID_HANDLE_VALUE) return 0;
    reader->win32_handle = handle;
    return 1;
}

/* offset and size must stay multiples of the logical sector size. */
static int cdrom_read_raw(struct c2_cdrom_reader *reader, uint64_t offset,
                          void *buffer, size_t size)
{
    LARGE_INTEGER position;
    position.QuadPart = (LONGLONG)offset;
    if (!SetFilePointerEx((HANDLE)reader->win32_handle, position, NULL,
                          FILE_BEGIN)) {
        return 0;
    }
    while (size > 0) {
        DWORD wanted = size > 0x10000000u ? 0x10000000u : (DWORD)size;
        DWORD got = 0;
        if (!ReadFile((HANDLE)reader->win32_handle, buffer, wanted, &got,
                      NULL) || got == 0) {
            return 0;
        }
        buffer = (unsigned char *)buffer + got;
        size -= got;
    }
    return 1;
}

void c2_cdrom_close(struct c2_cdrom_reader *reader)
{
    if (reader == NULL) return;
    if (reader->win32_handle != NULL &&
        reader->win32_handle != INVALID_HANDLE_VALUE) {
        CloseHandle((HANDLE)reader->win32_handle);
    }
    memset(reader, 0, sizeof(*reader));
}

int c2_cdrom_drive_has_disc(const char *path)
{
    char device[8];
    HANDLE handle;
    DWORD returned = 0;
    BOOL ok;
    if (!device_letter_path(path, device, sizeof(device))) return 0;
    handle = CreateFileA(device, 0, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
                         OPEN_EXISTING, 0, NULL);
    if (handle == INVALID_HANDLE_VALUE) return 0;
    ok = DeviceIoControl(handle, IOCTL_STORAGE_CHECK_VERIFY2, NULL, 0, NULL, 0,
                         &returned, NULL);
    CloseHandle(handle);
    return ok ? 1 : 0;
}

int c2_cdrom_find_drives(char paths[][C2_CDROM_DRIVE_PATH_CAPACITY], int max)
{
    DWORD mask = GetLogicalDrives();
    int count = 0;
    int letter;
    for (letter = 0; letter < 26 && count < max; letter++) {
        char root[4] = { (char)('A' + letter), ':', '\\', '\0' };
        if (!(mask & (1u << letter))) continue;
        if (GetDriveTypeA(root) != DRIVE_CDROM) continue;
        snprintf(paths[count], C2_CDROM_DRIVE_PATH_CAPACITY, "%c:",
                 'A' + letter);
        count++;
    }
    return count;
}

#else /* POSIX */

#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#if PORT_PLATFORM_LINUX
#include <limits.h>
#include <linux/cdrom.h>
#include <sys/ioctl.h>
#endif

int c2_cdrom_drive_has_disc(const char *path)
{
#if PORT_PLATFORM_LINUX
    int fd = open(path, O_RDONLY | O_NONBLOCK);
    int status;
    if (fd < 0) return 0;
    status = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT);
    close(fd);
    return status == CDS_DISC_OK;
#else
    struct c2_cdrom_reader reader;
    if (!c2_cdrom_open(path, &reader, NULL, 0)) return 0;
    c2_cdrom_close(&reader);
    return 1;
#endif
}

int c2_cdrom_is_device_path(const char *path)
{
    struct stat st;
    if (path == NULL || stat(path, &st) != 0) return 0;
    return S_ISBLK(st.st_mode) || S_ISCHR(st.st_mode);
}

static int cdrom_open_handle(struct c2_cdrom_reader *reader, const char *path)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) return 0;
    reader->fd = fd;
    return 1;
}

static int cdrom_read_raw(struct c2_cdrom_reader *reader, uint64_t offset,
                          void *buffer, size_t size)
{
    while (size > 0) {
        ssize_t got = pread(reader->fd, buffer, size, (off_t)offset);
        if (got <= 0) return 0;
        buffer = (unsigned char *)buffer + got;
        offset += (uint64_t)got;
        size -= (size_t)got;
    }
    return 1;
}

void c2_cdrom_close(struct c2_cdrom_reader *reader)
{
    if (reader == NULL) return;
    if (reader->fd >= 0) close(reader->fd);
    memset(reader, 0, sizeof(*reader));
    reader->fd = -1;
}

int c2_cdrom_find_drives(char paths[][C2_CDROM_DRIVE_PATH_CAPACITY], int max)
{
    /* Common optical device names across Linux and the BSDs.  macOS device
     * numbering is dynamic, so a fixed candidate list is deliberately not
     * attempted there; users can still pass /dev/diskN explicitly. */
    static const char *candidates[] = {
        "/dev/sr0", "/dev/sr1", "/dev/sr2", "/dev/sr3",
        "/dev/cd0", "/dev/cd1"
    };
    size_t i;
    int count = 0;
    for (i = 0; i < sizeof(candidates) / sizeof(candidates[0]); i++) {
        if (count >= max) break;
        if (!c2_cdrom_is_device_path(candidates[i])) continue;
        snprintf(paths[count], C2_CDROM_DRIVE_PATH_CAPACITY, "%s",
                 candidates[i]);
        count++;
    }
    return count;
}

#endif /* POSIX */

static uint64_t fnv1a(uint64_t hash, const unsigned char *data, size_t size)
{
    while (size--) {
        hash ^= *data++;
        hash *= 1099511628211ULL;
    }
    return hash;
}

int c2_cdrom_open(const char *path, struct c2_cdrom_reader *reader,
                  char *error, size_t error_capacity)
{
    unsigned char sector[C2_CDROM_SECTOR];
    unsigned int index;
    int found;

    if (reader == NULL) return 0;
    memset(reader, 0, sizeof(*reader));
    reader->fd = -1;
    if (path == NULL || !cdrom_open_handle(reader, path)) {
        set_error(error, error_capacity, "could not open the CD-ROM drive");
        return 0;
    }
    found = 0;
    for (index = 16; index < 16 + C2_CDROM_MAX_DESCRIPTORS; index++) {
        if (!cdrom_read_raw(reader, (uint64_t)index * C2_CDROM_SECTOR,
                            sector, sizeof(sector))) {
            break;
        }
        if (memcmp(sector + 1, "CD001", 5) != 0 || sector[6] != 1) continue;
        if (sector[0] == 1) { found = 1; break; }
        if (sector[0] == 255) break;
    }
    if (!found) {
        c2_cdrom_close(reader);
        set_error(error, error_capacity,
                  "no ISO-9660 data track was found on the disc");
        return 0;
    }
    reader->size = (uint64_t)read_le32(sector + 80) * C2_CDROM_SECTOR;
    if (reader->size < 17u * C2_CDROM_SECTOR) {
        c2_cdrom_close(reader);
        set_error(error, error_capacity,
                  "the disc reports an invalid volume size");
        return 0;
    }
    reader->fingerprint = fnv1a(1469598103934665603ULL, sector,
                                sizeof(sector));
    return 1;
}

#endif /* native */

static int cdrom_read_at(void *userdata, uint64_t offset, void *buffer,
                         size_t size, size_t *read_out)
{
#if PORT_PLATFORM_WASM
    (void)userdata; (void)offset; (void)buffer; (void)size;
    if (read_out) *read_out = 0;
    return 0;
#else
    struct c2_cdrom_reader *reader = userdata;
    unsigned char sector[C2_CDROM_SECTOR];
    size_t done = 0;

    if (read_out) *read_out = 0;
    if (offset > reader->size) return 0;
    if (size > reader->size - offset) size = (size_t)(reader->size - offset);
    while (done < size) {
        uint64_t position = offset + done;
        size_t within = (size_t)(position % C2_CDROM_SECTOR);
        size_t chunk;
        if (within == 0 && size - done >= C2_CDROM_SECTOR) {
            chunk = ((size - done) / C2_CDROM_SECTOR) * C2_CDROM_SECTOR;
            if (chunk > 64u * C2_CDROM_SECTOR) chunk = 64u * C2_CDROM_SECTOR;
            if (!cdrom_read_raw(reader, position,
                                (unsigned char *)buffer + done, chunk)) {
                return 0;
            }
        } else {
            if (!cdrom_read_raw(reader, position - within, sector,
                                sizeof(sector))) {
                return 0;
            }
            chunk = C2_CDROM_SECTOR - within;
            if (chunk > size - done) chunk = size - done;
            memcpy((unsigned char *)buffer + done, sector + within, chunk);
        }
        done += chunk;
    }
    if (read_out) *read_out = done;
    return 1;
#endif
}

void c2_cdrom_source(struct c2_cdrom_reader *reader,
                     struct c2_source_reader *source)
{
    source->userdata = reader;
    source->size = reader->size;
    source->read_at = cdrom_read_at;
}
