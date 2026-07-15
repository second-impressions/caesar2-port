.386p
.MODEL FLAT

PUBLIC place_i_large_diamond_
PUBLIC place_i_large_diamond_lefthalf_
PUBLIC place_i_large_diamond_righthalf_
PUBLIC write_large_diamond_hat_
PUBLIC write_large_diamond_lefthat_
PUBLIC write_large_diamond_righthat_
PUBLIC write_large_diamond_lefthalfhat_
PUBLIC write_large_diamond_righthalfhat_

EXTRN _internal_screen: BYTE
EXTRN _screen_width: BYTE
EXTRN _sndinit: BYTE
EXTRN _sprite_hat_start: BYTE
EXTRN _sprite_start: BYTE
EXTRN _sprite_x: BYTE
EXTRN _sprite_y: BYTE
EXTRN _y_length: BYTE

_TEXT SEGMENT BYTE PUBLIC USE32 'CODE'

; ════════════════════════════════════════════════════════════
; place_i_large_diamond
; ════════════════════════════════════════════════════════════
place_i_large_diamond_:
    pushad
    mov esi, eax
    mov ebx, edx
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp ebx, 2
    jne place_i_large_diamond_L1
    jmp near ptr place_i_large_diamond_L2
place_i_large_diamond_L1:
    mov ax, word ptr [esi]
    mov word ptr [edi + 1ch], ax
    mov eax, dword ptr [esi + 2]
    mov dword ptr [edi + 29ah], eax
    mov ax, word ptr [esi + 6]
    mov word ptr [edi + 29eh], ax
    mov eax, dword ptr [esi + 8]
    mov dword ptr [edi + 518h], eax
    mov eax, dword ptr [esi + 0ch]
    mov dword ptr [edi + 51ch], eax
    mov ax, word ptr [esi + 10h]
    mov word ptr [edi + 520h], ax
    mov eax, dword ptr [esi + 12h]
    mov dword ptr [edi + 796h], eax
    mov eax, dword ptr [esi + 16h]
    mov dword ptr [edi + 79ah], eax
    mov eax, dword ptr [esi + 1ah]
    mov dword ptr [edi + 79eh], eax
    mov ax, word ptr [esi + 1eh]
    mov word ptr [edi + 7a2h], ax
    mov eax, dword ptr [esi + 20h]
    mov dword ptr [edi + 0a14h], eax
    mov eax, dword ptr [esi + 24h]
    mov dword ptr [edi + 0a18h], eax
    mov eax, dword ptr [esi + 28h]
    mov dword ptr [edi + 0a1ch], eax
    mov eax, dword ptr [esi + 2ch]
    mov dword ptr [edi + 0a20h], eax
    mov ax, word ptr [esi + 30h]
    mov word ptr [edi + 0a24h], ax
    mov eax, dword ptr [esi + 32h]
    mov dword ptr [edi + 0c92h], eax
    mov eax, dword ptr [esi + 36h]
    mov dword ptr [edi + 0c96h], eax
    mov eax, dword ptr [esi + 3ah]
    mov dword ptr [edi + 0c9ah], eax
    mov eax, dword ptr [esi + 3eh]
    mov dword ptr [edi + 0c9eh], eax
    mov eax, dword ptr [esi + 42h]
    mov dword ptr [edi + 0ca2h], eax
    mov ax, word ptr [esi + 46h]
    mov word ptr [edi + 0ca6h], ax
    mov eax, dword ptr [esi + 48h]
    mov dword ptr [edi + 0f10h], eax
    mov eax, dword ptr [esi + 4ch]
    mov dword ptr [edi + 0f14h], eax
    mov eax, dword ptr [esi + 50h]
    mov dword ptr [edi + 0f18h], eax
    mov eax, dword ptr [esi + 54h]
    mov dword ptr [edi + 0f1ch], eax
    mov eax, dword ptr [esi + 58h]
    mov dword ptr [edi + 0f20h], eax
    mov eax, dword ptr [esi + 5ch]
    mov dword ptr [edi + 0f24h], eax
    mov ax, word ptr [esi + 60h]
    mov word ptr [edi + 0f28h], ax
    mov eax, dword ptr [esi + 62h]
    mov dword ptr [edi + 118eh], eax
    mov eax, dword ptr [esi + 66h]
    mov dword ptr [edi + 1192h], eax
    mov eax, dword ptr [esi + 6ah]
    mov dword ptr [edi + 1196h], eax
    mov eax, dword ptr [esi + 6eh]
    mov dword ptr [edi + 119ah], eax
    mov eax, dword ptr [esi + 72h]
    mov dword ptr [edi + 119eh], eax
    mov eax, dword ptr [esi + 76h]
    mov dword ptr [edi + 11a2h], eax
    mov eax, dword ptr [esi + 7ah]
    mov dword ptr [edi + 11a6h], eax
    mov ax, word ptr [esi + 7eh]
    mov word ptr [edi + 11aah], ax
    mov eax, dword ptr [esi + 80h]
    mov dword ptr [edi + 140ch], eax
    mov eax, dword ptr [esi + 84h]
    mov dword ptr [edi + 1410h], eax
    mov eax, dword ptr [esi + 88h]
    mov dword ptr [edi + 1414h], eax
    mov eax, dword ptr [esi + 8ch]
    mov dword ptr [edi + 1418h], eax
    mov eax, dword ptr [esi + 90h]
    mov dword ptr [edi + 141ch], eax
    mov eax, dword ptr [esi + 94h]
    mov dword ptr [edi + 1420h], eax
    mov eax, dword ptr [esi + 98h]
    mov dword ptr [edi + 1424h], eax
    mov eax, dword ptr [esi + 9ch]
    mov dword ptr [edi + 1428h], eax
    mov ax, word ptr [esi + 0a0h]
    mov word ptr [edi + 142ch], ax
    mov eax, dword ptr [esi + 0a2h]
    mov dword ptr [edi + 168ah], eax
    mov eax, dword ptr [esi + 0a6h]
    mov dword ptr [edi + 168eh], eax
    mov eax, dword ptr [esi + 0aah]
    mov dword ptr [edi + 1692h], eax
    mov eax, dword ptr [esi + 0aeh]
    mov dword ptr [edi + 1696h], eax
    mov eax, dword ptr [esi + 0b2h]
    mov dword ptr [edi + 169ah], eax
    mov eax, dword ptr [esi + 0b6h]
    mov dword ptr [edi + 169eh], eax
    mov eax, dword ptr [esi + 0bah]
    mov dword ptr [edi + 16a2h], eax
    mov eax, dword ptr [esi + 0beh]
    mov dword ptr [edi + 16a6h], eax
    mov eax, dword ptr [esi + 0c2h]
    mov dword ptr [edi + 16aah], eax
    mov ax, word ptr [esi + 0c6h]
    mov word ptr [edi + 16aeh], ax
    mov eax, dword ptr [esi + 0c8h]
    mov dword ptr [edi + 1908h], eax
    mov eax, dword ptr [esi + 0cch]
    mov dword ptr [edi + 190ch], eax
    mov eax, dword ptr [esi + 0d0h]
    mov dword ptr [edi + 1910h], eax
    mov eax, dword ptr [esi + 0d4h]
    mov dword ptr [edi + 1914h], eax
    mov eax, dword ptr [esi + 0d8h]
    mov dword ptr [edi + 1918h], eax
    mov eax, dword ptr [esi + 0dch]
    mov dword ptr [edi + 191ch], eax
    mov eax, dword ptr [esi + 0e0h]
    mov dword ptr [edi + 1920h], eax
    mov eax, dword ptr [esi + 0e4h]
    mov dword ptr [edi + 1924h], eax
    mov eax, dword ptr [esi + 0e8h]
    mov dword ptr [edi + 1928h], eax
    mov eax, dword ptr [esi + 0ech]
    mov dword ptr [edi + 192ch], eax
    mov ax, word ptr [esi + 0f0h]
    mov word ptr [edi + 1930h], ax
    mov eax, dword ptr [esi + 0f2h]
    mov dword ptr [edi + 1b86h], eax
    mov eax, dword ptr [esi + 0f6h]
    mov dword ptr [edi + 1b8ah], eax
    mov eax, dword ptr [esi + 0fah]
    mov dword ptr [edi + 1b8eh], eax
    mov eax, dword ptr [esi + 0feh]
    mov dword ptr [edi + 1b92h], eax
    mov eax, dword ptr [esi + 102h]
    mov dword ptr [edi + 1b96h], eax
    mov eax, dword ptr [esi + 106h]
    mov dword ptr [edi + 1b9ah], eax
    mov eax, dword ptr [esi + 10ah]
    mov dword ptr [edi + 1b9eh], eax
    mov eax, dword ptr [esi + 10eh]
    mov dword ptr [edi + 1ba2h], eax
    mov eax, dword ptr [esi + 112h]
    mov dword ptr [edi + 1ba6h], eax
    mov eax, dword ptr [esi + 116h]
    mov dword ptr [edi + 1baah], eax
    mov eax, dword ptr [esi + 11ah]
    mov dword ptr [edi + 1baeh], eax
    mov ax, word ptr [esi + 11eh]
    mov word ptr [edi + 1bb2h], ax
    mov eax, dword ptr [esi + 120h]
    mov dword ptr [edi + 1e04h], eax
    mov eax, dword ptr [esi + 124h]
    mov dword ptr [edi + 1e08h], eax
    mov eax, dword ptr [esi + 128h]
    mov dword ptr [edi + 1e0ch], eax
    mov eax, dword ptr [esi + 12ch]
    mov dword ptr [edi + 1e10h], eax
    mov eax, dword ptr [esi + 130h]
    mov dword ptr [edi + 1e14h], eax
    mov eax, dword ptr [esi + 134h]
    mov dword ptr [edi + 1e18h], eax
    mov eax, dword ptr [esi + 138h]
    mov dword ptr [edi + 1e1ch], eax
    mov eax, dword ptr [esi + 13ch]
    mov dword ptr [edi + 1e20h], eax
    mov eax, dword ptr [esi + 140h]
    mov dword ptr [edi + 1e24h], eax
    mov eax, dword ptr [esi + 144h]
    mov dword ptr [edi + 1e28h], eax
    mov eax, dword ptr [esi + 148h]
    mov dword ptr [edi + 1e2ch], eax
    mov eax, dword ptr [esi + 14ch]
    mov dword ptr [edi + 1e30h], eax
    mov ax, word ptr [esi + 150h]
    mov word ptr [edi + 1e34h], ax
    mov eax, dword ptr [esi + 152h]
    mov dword ptr [edi + 2082h], eax
    mov eax, dword ptr [esi + 156h]
    mov dword ptr [edi + 2086h], eax
    mov eax, dword ptr [esi + 15ah]
    mov dword ptr [edi + 208ah], eax
    mov eax, dword ptr [esi + 15eh]
    mov dword ptr [edi + 208eh], eax
    mov eax, dword ptr [esi + 162h]
    mov dword ptr [edi + 2092h], eax
    mov eax, dword ptr [esi + 166h]
    mov dword ptr [edi + 2096h], eax
    mov eax, dword ptr [esi + 16ah]
    mov dword ptr [edi + 209ah], eax
    mov eax, dword ptr [esi + 16eh]
    mov dword ptr [edi + 209eh], eax
    mov eax, dword ptr [esi + 172h]
    mov dword ptr [edi + 20a2h], eax
    mov eax, dword ptr [esi + 176h]
    mov dword ptr [edi + 20a6h], eax
    mov eax, dword ptr [esi + 17ah]
    mov dword ptr [edi + 20aah], eax
    mov eax, dword ptr [esi + 17eh]
    mov dword ptr [edi + 20aeh], eax
    mov eax, dword ptr [esi + 182h]
    mov dword ptr [edi + 20b2h], eax
    mov ax, word ptr [esi + 186h]
    mov word ptr [edi + 20b6h], ax
    mov eax, dword ptr [esi + 188h]
    mov dword ptr [edi + 2300h], eax
    mov eax, dword ptr [esi + 18ch]
    mov dword ptr [edi + 2304h], eax
    mov eax, dword ptr [esi + 190h]
    mov dword ptr [edi + 2308h], eax
    mov eax, dword ptr [esi + 194h]
    mov dword ptr [edi + 230ch], eax
    mov eax, dword ptr [esi + 198h]
    mov dword ptr [edi + 2310h], eax
    mov eax, dword ptr [esi + 19ch]
    mov dword ptr [edi + 2314h], eax
    mov eax, dword ptr [esi + 1a0h]
    mov dword ptr [edi + 2318h], eax
    mov eax, dword ptr [esi + 1a4h]
    mov dword ptr [edi + 231ch], eax
    mov eax, dword ptr [esi + 1a8h]
    mov dword ptr [edi + 2320h], eax
    mov eax, dword ptr [esi + 1ach]
    mov dword ptr [edi + 2324h], eax
    mov eax, dword ptr [esi + 1b0h]
    mov dword ptr [edi + 2328h], eax
    mov eax, dword ptr [esi + 1b4h]
    mov dword ptr [edi + 232ch], eax
    mov eax, dword ptr [esi + 1b8h]
    mov dword ptr [edi + 2330h], eax
    mov eax, dword ptr [esi + 1bch]
    mov dword ptr [edi + 2334h], eax
    mov ax, word ptr [esi + 1c0h]
    mov word ptr [edi + 2338h], ax
    cmp ebx, 1
    jne place_i_large_diamond_L2
    jmp near ptr place_i_large_diamond_L3
place_i_large_diamond_L2:
    mov eax, dword ptr [esi + 1c2h]
    mov dword ptr [edi + 2580h], eax
    mov eax, dword ptr [esi + 1c6h]
    mov dword ptr [edi + 2584h], eax
    mov eax, dword ptr [esi + 1cah]
    mov dword ptr [edi + 2588h], eax
    mov eax, dword ptr [esi + 1ceh]
    mov dword ptr [edi + 258ch], eax
    mov eax, dword ptr [esi + 1d2h]
    mov dword ptr [edi + 2590h], eax
    mov eax, dword ptr [esi + 1d6h]
    mov dword ptr [edi + 2594h], eax
    mov eax, dword ptr [esi + 1dah]
    mov dword ptr [edi + 2598h], eax
    mov eax, dword ptr [esi + 1deh]
    mov dword ptr [edi + 259ch], eax
    mov eax, dword ptr [esi + 1e2h]
    mov dword ptr [edi + 25a0h], eax
    mov eax, dword ptr [esi + 1e6h]
    mov dword ptr [edi + 25a4h], eax
    mov eax, dword ptr [esi + 1eah]
    mov dword ptr [edi + 25a8h], eax
    mov eax, dword ptr [esi + 1eeh]
    mov dword ptr [edi + 25ach], eax
    mov eax, dword ptr [esi + 1f2h]
    mov dword ptr [edi + 25b0h], eax
    mov eax, dword ptr [esi + 1f6h]
    mov dword ptr [edi + 25b4h], eax
    mov ax, word ptr [esi + 1fah]
    mov word ptr [edi + 25b8h], ax
    mov eax, dword ptr [esi + 1fch]
    mov dword ptr [edi + 2802h], eax
    mov eax, dword ptr [esi + 200h]
    mov dword ptr [edi + 2806h], eax
    mov eax, dword ptr [esi + 204h]
    mov dword ptr [edi + 280ah], eax
    mov eax, dword ptr [esi + 208h]
    mov dword ptr [edi + 280eh], eax
    mov eax, dword ptr [esi + 20ch]
    mov dword ptr [edi + 2812h], eax
    mov eax, dword ptr [esi + 210h]
    mov dword ptr [edi + 2816h], eax
    mov eax, dword ptr [esi + 214h]
    mov dword ptr [edi + 281ah], eax
    mov eax, dword ptr [esi + 218h]
    mov dword ptr [edi + 281eh], eax
    mov eax, dword ptr [esi + 21ch]
    mov dword ptr [edi + 2822h], eax
    mov eax, dword ptr [esi + 220h]
    mov dword ptr [edi + 2826h], eax
    mov eax, dword ptr [esi + 224h]
    mov dword ptr [edi + 282ah], eax
    mov eax, dword ptr [esi + 228h]
    mov dword ptr [edi + 282eh], eax
    mov eax, dword ptr [esi + 22ch]
    mov dword ptr [edi + 2832h], eax
    mov ax, word ptr [esi + 230h]
    mov word ptr [edi + 2836h], ax
    mov eax, dword ptr [esi + 232h]
    mov dword ptr [edi + 2a84h], eax
    mov eax, dword ptr [esi + 236h]
    mov dword ptr [edi + 2a88h], eax
    mov eax, dword ptr [esi + 23ah]
    mov dword ptr [edi + 2a8ch], eax
    mov eax, dword ptr [esi + 23eh]
    mov dword ptr [edi + 2a90h], eax
    mov eax, dword ptr [esi + 242h]
    mov dword ptr [edi + 2a94h], eax
    mov eax, dword ptr [esi + 246h]
    mov dword ptr [edi + 2a98h], eax
    mov eax, dword ptr [esi + 24ah]
    mov dword ptr [edi + 2a9ch], eax
    mov eax, dword ptr [esi + 24eh]
    mov dword ptr [edi + 2aa0h], eax
    mov eax, dword ptr [esi + 252h]
    mov dword ptr [edi + 2aa4h], eax
    mov eax, dword ptr [esi + 256h]
    mov dword ptr [edi + 2aa8h], eax
    mov eax, dword ptr [esi + 25ah]
    mov dword ptr [edi + 2aach], eax
    mov eax, dword ptr [esi + 25eh]
    mov dword ptr [edi + 2ab0h], eax
    mov ax, word ptr [esi + 262h]
    mov word ptr [edi + 2ab4h], ax
    mov eax, dword ptr [esi + 264h]
    mov dword ptr [edi + 2d06h], eax
    mov eax, dword ptr [esi + 268h]
    mov dword ptr [edi + 2d0ah], eax
    mov eax, dword ptr [esi + 26ch]
    mov dword ptr [edi + 2d0eh], eax
    mov eax, dword ptr [esi + 270h]
    mov dword ptr [edi + 2d12h], eax
    mov eax, dword ptr [esi + 274h]
    mov dword ptr [edi + 2d16h], eax
    mov eax, dword ptr [esi + 278h]
    mov dword ptr [edi + 2d1ah], eax
    mov eax, dword ptr [esi + 27ch]
    mov dword ptr [edi + 2d1eh], eax
    mov eax, dword ptr [esi + 280h]
    mov dword ptr [edi + 2d22h], eax
    mov eax, dword ptr [esi + 284h]
    mov dword ptr [edi + 2d26h], eax
    mov eax, dword ptr [esi + 288h]
    mov dword ptr [edi + 2d2ah], eax
    mov eax, dword ptr [esi + 28ch]
    mov dword ptr [edi + 2d2eh], eax
    mov ax, word ptr [esi + 290h]
    mov word ptr [edi + 2d32h], ax
    mov eax, dword ptr [esi + 292h]
    mov dword ptr [edi + 2f88h], eax
    mov eax, dword ptr [esi + 296h]
    mov dword ptr [edi + 2f8ch], eax
    mov eax, dword ptr [esi + 29ah]
    mov dword ptr [edi + 2f90h], eax
    mov eax, dword ptr [esi + 29eh]
    mov dword ptr [edi + 2f94h], eax
    mov eax, dword ptr [esi + 2a2h]
    mov dword ptr [edi + 2f98h], eax
    mov eax, dword ptr [esi + 2a6h]
    mov dword ptr [edi + 2f9ch], eax
    mov eax, dword ptr [esi + 2aah]
    mov dword ptr [edi + 2fa0h], eax
    mov eax, dword ptr [esi + 2aeh]
    mov dword ptr [edi + 2fa4h], eax
    mov eax, dword ptr [esi + 2b2h]
    mov dword ptr [edi + 2fa8h], eax
    mov eax, dword ptr [esi + 2b6h]
    mov dword ptr [edi + 2fach], eax
    mov ax, word ptr [esi + 2bah]
    mov word ptr [edi + 2fb0h], ax
    mov eax, dword ptr [esi + 2bch]
    mov dword ptr [edi + 320ah], eax
    mov eax, dword ptr [esi + 2c0h]
    mov dword ptr [edi + 320eh], eax
    mov eax, dword ptr [esi + 2c4h]
    mov dword ptr [edi + 3212h], eax
    mov eax, dword ptr [esi + 2c8h]
    mov dword ptr [edi + 3216h], eax
    mov eax, dword ptr [esi + 2cch]
    mov dword ptr [edi + 321ah], eax
    mov eax, dword ptr [esi + 2d0h]
    mov dword ptr [edi + 321eh], eax
    mov eax, dword ptr [esi + 2d4h]
    mov dword ptr [edi + 3222h], eax
    mov eax, dword ptr [esi + 2d8h]
    mov dword ptr [edi + 3226h], eax
    mov eax, dword ptr [esi + 2dch]
    mov dword ptr [edi + 322ah], eax
    mov ax, word ptr [esi + 2e0h]
    mov word ptr [edi + 322eh], ax
    mov eax, dword ptr [esi + 2e2h]
    mov dword ptr [edi + 348ch], eax
    mov eax, dword ptr [esi + 2e6h]
    mov dword ptr [edi + 3490h], eax
    mov eax, dword ptr [esi + 2eah]
    mov dword ptr [edi + 3494h], eax
    mov eax, dword ptr [esi + 2eeh]
    mov dword ptr [edi + 3498h], eax
    mov eax, dword ptr [esi + 2f2h]
    mov dword ptr [edi + 349ch], eax
    mov eax, dword ptr [esi + 2f6h]
    mov dword ptr [edi + 34a0h], eax
    mov eax, dword ptr [esi + 2fah]
    mov dword ptr [edi + 34a4h], eax
    mov eax, dword ptr [esi + 2feh]
    mov dword ptr [edi + 34a8h], eax
    mov ax, word ptr [esi + 302h]
    mov word ptr [edi + 34ach], ax
    mov eax, dword ptr [esi + 304h]
    mov dword ptr [edi + 370eh], eax
    mov eax, dword ptr [esi + 308h]
    mov dword ptr [edi + 3712h], eax
    mov eax, dword ptr [esi + 30ch]
    mov dword ptr [edi + 3716h], eax
    mov eax, dword ptr [esi + 310h]
    mov dword ptr [edi + 371ah], eax
    mov eax, dword ptr [esi + 314h]
    mov dword ptr [edi + 371eh], eax
    mov eax, dword ptr [esi + 318h]
    mov dword ptr [edi + 3722h], eax
    mov eax, dword ptr [esi + 31ch]
    mov dword ptr [edi + 3726h], eax
    mov ax, word ptr [esi + 320h]
    mov word ptr [edi + 372ah], ax
    mov eax, dword ptr [esi + 322h]
    mov dword ptr [edi + 3990h], eax
    mov eax, dword ptr [esi + 326h]
    mov dword ptr [edi + 3994h], eax
    mov eax, dword ptr [esi + 32ah]
    mov dword ptr [edi + 3998h], eax
    mov eax, dword ptr [esi + 32eh]
    mov dword ptr [edi + 399ch], eax
    mov eax, dword ptr [esi + 332h]
    mov dword ptr [edi + 39a0h], eax
    mov eax, dword ptr [esi + 336h]
    mov dword ptr [edi + 39a4h], eax
    mov ax, word ptr [esi + 33ah]
    mov word ptr [edi + 39a8h], ax
    mov eax, dword ptr [esi + 33ch]
    mov dword ptr [edi + 3c12h], eax
    mov eax, dword ptr [esi + 340h]
    mov dword ptr [edi + 3c16h], eax
    mov eax, dword ptr [esi + 344h]
    mov dword ptr [edi + 3c1ah], eax
    mov eax, dword ptr [esi + 348h]
    mov dword ptr [edi + 3c1eh], eax
    mov eax, dword ptr [esi + 34ch]
    mov dword ptr [edi + 3c22h], eax
    mov ax, word ptr [esi + 350h]
    mov word ptr [edi + 3c26h], ax
    mov eax, dword ptr [esi + 352h]
    mov dword ptr [edi + 3e94h], eax
    mov eax, dword ptr [esi + 356h]
    mov dword ptr [edi + 3e98h], eax
    mov eax, dword ptr [esi + 35ah]
    mov dword ptr [edi + 3e9ch], eax
    mov eax, dword ptr [esi + 35eh]
    mov dword ptr [edi + 3ea0h], eax
    mov ax, word ptr [esi + 362h]
    mov word ptr [edi + 3ea4h], ax
    mov eax, dword ptr [esi + 364h]
    mov dword ptr [edi + 4116h], eax
    mov eax, dword ptr [esi + 368h]
    mov dword ptr [edi + 411ah], eax
    mov eax, dword ptr [esi + 36ch]
    mov dword ptr [edi + 411eh], eax
    mov ax, word ptr [esi + 370h]
    mov word ptr [edi + 4122h], ax
    mov eax, dword ptr [esi + 372h]
    mov dword ptr [edi + 4398h], eax
    mov eax, dword ptr [esi + 376h]
    mov dword ptr [edi + 439ch], eax
    mov ax, word ptr [esi + 37ah]
    mov word ptr [edi + 43a0h], ax
    mov eax, dword ptr [esi + 37ch]
    mov dword ptr [edi + 461ah], eax
    mov ax, word ptr [esi + 380h]
    mov word ptr [edi + 461eh], ax
    mov ax, word ptr [esi + 382h]
    mov word ptr [edi + 489ch], ax
place_i_large_diamond_L3:
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_i_large_diamond_lefthalf
; ════════════════════════════════════════════════════════════
place_i_large_diamond_lefthalf_:
    pushad
    mov esi, eax
    mov ebx, edx
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp ebx, 2
    jne place_i_large_diamond_lefthalf_L1
    jmp near ptr place_i_large_diamond_lefthalf_L2
place_i_large_diamond_lefthalf_L1:
    mov ax, word ptr [esi + 6]
    mov word ptr [edi + 280h], ax
    mov eax, dword ptr [esi + 0eh]
    mov dword ptr [edi + 500h], eax
    mov eax, dword ptr [esi + 1ah]
    mov dword ptr [edi + 780h], eax
    mov ax, word ptr [esi + 1eh]
    mov word ptr [edi + 784h], ax
    mov eax, dword ptr [esi + 2ah]
    mov dword ptr [edi + 0a00h], eax
    mov eax, dword ptr [esi + 2eh]
    mov dword ptr [edi + 0a04h], eax
    mov eax, dword ptr [esi + 3eh]
    mov dword ptr [edi + 0c80h], eax
    mov eax, dword ptr [esi + 42h]
    mov dword ptr [edi + 0c84h], eax
    mov ax, word ptr [esi + 46h]
    mov word ptr [edi + 0c88h], ax
    mov eax, dword ptr [esi + 56h]
    mov dword ptr [edi + 0f00h], eax
    mov eax, dword ptr [esi + 5ah]
    mov dword ptr [edi + 0f04h], eax
    mov eax, dword ptr [esi + 5eh]
    mov dword ptr [edi + 0f08h], eax
    mov eax, dword ptr [esi + 72h]
    mov dword ptr [edi + 1180h], eax
    mov eax, dword ptr [esi + 76h]
    mov dword ptr [edi + 1184h], eax
    mov eax, dword ptr [esi + 7ah]
    mov dword ptr [edi + 1188h], eax
    mov ax, word ptr [esi + 7eh]
    mov word ptr [edi + 118ch], ax
    mov eax, dword ptr [esi + 92h]
    mov dword ptr [edi + 1400h], eax
    mov eax, dword ptr [esi + 96h]
    mov dword ptr [edi + 1404h], eax
    mov eax, dword ptr [esi + 9ah]
    mov dword ptr [edi + 1408h], eax
    mov eax, dword ptr [esi + 9eh]
    mov dword ptr [edi + 140ch], eax
    mov eax, dword ptr [esi + 0b6h]
    mov dword ptr [edi + 1680h], eax
    mov eax, dword ptr [esi + 0bah]
    mov dword ptr [edi + 1684h], eax
    mov eax, dword ptr [esi + 0beh]
    mov dword ptr [edi + 1688h], eax
    mov eax, dword ptr [esi + 0c2h]
    mov dword ptr [edi + 168ch], eax
    mov ax, word ptr [esi + 0c6h]
    mov word ptr [edi + 1690h], ax
    mov eax, dword ptr [esi + 0deh]
    mov dword ptr [edi + 1900h], eax
    mov eax, dword ptr [esi + 0e2h]
    mov dword ptr [edi + 1904h], eax
    mov eax, dword ptr [esi + 0e6h]
    mov dword ptr [edi + 1908h], eax
    mov eax, dword ptr [esi + 0eah]
    mov dword ptr [edi + 190ch], eax
    mov eax, dword ptr [esi + 0eeh]
    mov dword ptr [edi + 1910h], eax
    mov eax, dword ptr [esi + 10ah]
    mov dword ptr [edi + 1b80h], eax
    mov eax, dword ptr [esi + 10eh]
    mov dword ptr [edi + 1b84h], eax
    mov eax, dword ptr [esi + 112h]
    mov dword ptr [edi + 1b88h], eax
    mov eax, dword ptr [esi + 116h]
    mov dword ptr [edi + 1b8ch], eax
    mov eax, dword ptr [esi + 11ah]
    mov dword ptr [edi + 1b90h], eax
    mov ax, word ptr [esi + 11eh]
    mov word ptr [edi + 1b94h], ax
    mov eax, dword ptr [esi + 13ah]
    mov dword ptr [edi + 1e00h], eax
    mov eax, dword ptr [esi + 13eh]
    mov dword ptr [edi + 1e04h], eax
    mov eax, dword ptr [esi + 142h]
    mov dword ptr [edi + 1e08h], eax
    mov eax, dword ptr [esi + 146h]
    mov dword ptr [edi + 1e0ch], eax
    mov eax, dword ptr [esi + 14ah]
    mov dword ptr [edi + 1e10h], eax
    mov eax, dword ptr [esi + 14eh]
    mov dword ptr [edi + 1e14h], eax
    mov eax, dword ptr [esi + 16eh]
    mov dword ptr [edi + 2080h], eax
    mov eax, dword ptr [esi + 172h]
    mov dword ptr [edi + 2084h], eax
    mov eax, dword ptr [esi + 176h]
    mov dword ptr [edi + 2088h], eax
    mov eax, dword ptr [esi + 17ah]
    mov dword ptr [edi + 208ch], eax
    mov eax, dword ptr [esi + 17eh]
    mov dword ptr [edi + 2090h], eax
    mov eax, dword ptr [esi + 182h]
    mov dword ptr [edi + 2094h], eax
    mov ax, word ptr [esi + 186h]
    mov word ptr [edi + 2098h], ax
    mov eax, dword ptr [esi + 1a6h]
    mov dword ptr [edi + 2300h], eax
    mov eax, dword ptr [esi + 1aah]
    mov dword ptr [edi + 2304h], eax
    mov eax, dword ptr [esi + 1aeh]
    mov dword ptr [edi + 2308h], eax
    mov eax, dword ptr [esi + 1b2h]
    mov dword ptr [edi + 230ch], eax
    mov eax, dword ptr [esi + 1b6h]
    mov dword ptr [edi + 2310h], eax
    mov eax, dword ptr [esi + 1bah]
    mov dword ptr [edi + 2314h], eax
    mov eax, dword ptr [esi + 1beh]
    mov dword ptr [edi + 2318h], eax
    cmp ebx, 1
    jne place_i_large_diamond_lefthalf_L2
    jmp near ptr place_i_large_diamond_lefthalf_L3
place_i_large_diamond_lefthalf_L2:
    mov eax, dword ptr [esi + 1e0h]
    mov dword ptr [edi + 2580h], eax
    mov eax, dword ptr [esi + 1e4h]
    mov dword ptr [edi + 2584h], eax
    mov eax, dword ptr [esi + 1e8h]
    mov dword ptr [edi + 2588h], eax
    mov eax, dword ptr [esi + 1ech]
    mov dword ptr [edi + 258ch], eax
    mov eax, dword ptr [esi + 1f0h]
    mov dword ptr [edi + 2590h], eax
    mov eax, dword ptr [esi + 1f4h]
    mov dword ptr [edi + 2594h], eax
    mov eax, dword ptr [esi + 1f8h]
    mov dword ptr [edi + 2598h], eax
    mov eax, dword ptr [esi + 218h]
    mov dword ptr [edi + 2800h], eax
    mov eax, dword ptr [esi + 21ch]
    mov dword ptr [edi + 2804h], eax
    mov eax, dword ptr [esi + 220h]
    mov dword ptr [edi + 2808h], eax
    mov eax, dword ptr [esi + 224h]
    mov dword ptr [edi + 280ch], eax
    mov eax, dword ptr [esi + 228h]
    mov dword ptr [edi + 2810h], eax
    mov eax, dword ptr [esi + 22ch]
    mov dword ptr [edi + 2814h], eax
    mov ax, word ptr [esi + 230h]
    mov word ptr [edi + 2818h], ax
    mov eax, dword ptr [esi + 24ch]
    mov dword ptr [edi + 2a80h], eax
    mov eax, dword ptr [esi + 250h]
    mov dword ptr [edi + 2a84h], eax
    mov eax, dword ptr [esi + 254h]
    mov dword ptr [edi + 2a88h], eax
    mov eax, dword ptr [esi + 258h]
    mov dword ptr [edi + 2a8ch], eax
    mov eax, dword ptr [esi + 25ch]
    mov dword ptr [edi + 2a90h], eax
    mov eax, dword ptr [esi + 260h]
    mov dword ptr [edi + 2a94h], eax
    mov eax, dword ptr [esi + 27ch]
    mov dword ptr [edi + 2d00h], eax
    mov eax, dword ptr [esi + 280h]
    mov dword ptr [edi + 2d04h], eax
    mov eax, dword ptr [esi + 284h]
    mov dword ptr [edi + 2d08h], eax
    mov eax, dword ptr [esi + 288h]
    mov dword ptr [edi + 2d0ch], eax
    mov eax, dword ptr [esi + 28ch]
    mov dword ptr [edi + 2d10h], eax
    mov ax, word ptr [esi + 290h]
    mov word ptr [edi + 2d14h], ax
    mov eax, dword ptr [esi + 2a8h]
    mov dword ptr [edi + 2f80h], eax
    mov eax, dword ptr [esi + 2ach]
    mov dword ptr [edi + 2f84h], eax
    mov eax, dword ptr [esi + 2b0h]
    mov dword ptr [edi + 2f88h], eax
    mov eax, dword ptr [esi + 2b4h]
    mov dword ptr [edi + 2f8ch], eax
    mov eax, dword ptr [esi + 2b8h]
    mov dword ptr [edi + 2f90h], eax
    mov eax, dword ptr [esi + 2d0h]
    mov dword ptr [edi + 3200h], eax
    mov eax, dword ptr [esi + 2d4h]
    mov dword ptr [edi + 3204h], eax
    mov eax, dword ptr [esi + 2d8h]
    mov dword ptr [edi + 3208h], eax
    mov eax, dword ptr [esi + 2dch]
    mov dword ptr [edi + 320ch], eax
    mov ax, word ptr [esi + 2e0h]
    mov word ptr [edi + 3210h], ax
    mov eax, dword ptr [esi + 2f4h]
    mov dword ptr [edi + 3480h], eax
    mov eax, dword ptr [esi + 2f8h]
    mov dword ptr [edi + 3484h], eax
    mov eax, dword ptr [esi + 2fch]
    mov dword ptr [edi + 3488h], eax
    mov eax, dword ptr [esi + 300h]
    mov dword ptr [edi + 348ch], eax
    mov eax, dword ptr [esi + 314h]
    mov dword ptr [edi + 3700h], eax
    mov eax, dword ptr [esi + 318h]
    mov dword ptr [edi + 3704h], eax
    mov eax, dword ptr [esi + 31ch]
    mov dword ptr [edi + 3708h], eax
    mov ax, word ptr [esi + 320h]
    mov word ptr [edi + 370ch], ax
    mov eax, dword ptr [esi + 330h]
    mov dword ptr [edi + 3980h], eax
    mov eax, dword ptr [esi + 334h]
    mov dword ptr [edi + 3984h], eax
    mov eax, dword ptr [esi + 338h]
    mov dword ptr [edi + 3988h], eax
    mov eax, dword ptr [esi + 348h]
    mov dword ptr [edi + 3c00h], eax
    mov eax, dword ptr [esi + 34ch]
    mov dword ptr [edi + 3c04h], eax
    mov ax, word ptr [esi + 350h]
    mov word ptr [edi + 3c08h], ax
    mov eax, dword ptr [esi + 35ch]
    mov dword ptr [edi + 3e80h], eax
    mov eax, dword ptr [esi + 360h]
    mov dword ptr [edi + 3e84h], eax
    mov eax, dword ptr [esi + 36ch]
    mov dword ptr [edi + 4100h], eax
    mov ax, word ptr [esi + 370h]
    mov word ptr [edi + 4104h], ax
    mov eax, dword ptr [esi + 378h]
    mov dword ptr [edi + 4380h], eax
    mov ax, word ptr [esi + 380h]
    mov word ptr [edi + 4600h], ax
place_i_large_diamond_lefthalf_L3:
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_i_large_diamond_righthalf
; ════════════════════════════════════════════════════════════
place_i_large_diamond_righthalf_:
    pushad
    mov esi, eax
    mov ebx, edx
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp ebx, 2
    jne place_i_large_diamond_righthalf_L1
    jmp near ptr place_i_large_diamond_righthalf_L2
place_i_large_diamond_righthalf_L1:
    mov ax, word ptr [esi + 2]
    mov word ptr [edi + 29ah], ax
    mov eax, dword ptr [esi + 8]
    mov dword ptr [edi + 518h], eax
    mov eax, dword ptr [esi + 12h]
    mov dword ptr [edi + 796h], eax
    mov ax, word ptr [esi + 16h]
    mov word ptr [edi + 79ah], ax
    mov eax, dword ptr [esi + 20h]
    mov dword ptr [edi + 0a14h], eax
    mov eax, dword ptr [esi + 24h]
    mov dword ptr [edi + 0a18h], eax
    mov eax, dword ptr [esi + 32h]
    mov dword ptr [edi + 0c92h], eax
    mov eax, dword ptr [esi + 36h]
    mov dword ptr [edi + 0c96h], eax
    mov ax, word ptr [esi + 3ah]
    mov word ptr [edi + 0c9ah], ax
    mov eax, dword ptr [esi + 48h]
    mov dword ptr [edi + 0f10h], eax
    mov eax, dword ptr [esi + 4ch]
    mov dword ptr [edi + 0f14h], eax
    mov eax, dword ptr [esi + 50h]
    mov dword ptr [edi + 0f18h], eax
    mov eax, dword ptr [esi + 62h]
    mov dword ptr [edi + 118eh], eax
    mov eax, dword ptr [esi + 66h]
    mov dword ptr [edi + 1192h], eax
    mov eax, dword ptr [esi + 6ah]
    mov dword ptr [edi + 1196h], eax
    mov ax, word ptr [esi + 6eh]
    mov word ptr [edi + 119ah], ax
    mov eax, dword ptr [esi + 80h]
    mov dword ptr [edi + 140ch], eax
    mov eax, dword ptr [esi + 84h]
    mov dword ptr [edi + 1410h], eax
    mov eax, dword ptr [esi + 88h]
    mov dword ptr [edi + 1414h], eax
    mov eax, dword ptr [esi + 8ch]
    mov dword ptr [edi + 1418h], eax
    mov eax, dword ptr [esi + 0a2h]
    mov dword ptr [edi + 168ah], eax
    mov eax, dword ptr [esi + 0a6h]
    mov dword ptr [edi + 168eh], eax
    mov eax, dword ptr [esi + 0aah]
    mov dword ptr [edi + 1692h], eax
    mov eax, dword ptr [esi + 0aeh]
    mov dword ptr [edi + 1696h], eax
    mov ax, word ptr [esi + 0b2h]
    mov word ptr [edi + 169ah], ax
    mov eax, dword ptr [esi + 0c8h]
    mov dword ptr [edi + 1908h], eax
    mov eax, dword ptr [esi + 0cch]
    mov dword ptr [edi + 190ch], eax
    mov eax, dword ptr [esi + 0d0h]
    mov dword ptr [edi + 1910h], eax
    mov eax, dword ptr [esi + 0d4h]
    mov dword ptr [edi + 1914h], eax
    mov eax, dword ptr [esi + 0d8h]
    mov dword ptr [edi + 1918h], eax
    mov eax, dword ptr [esi + 0f2h]
    mov dword ptr [edi + 1b86h], eax
    mov eax, dword ptr [esi + 0f6h]
    mov dword ptr [edi + 1b8ah], eax
    mov eax, dword ptr [esi + 0fah]
    mov dword ptr [edi + 1b8eh], eax
    mov eax, dword ptr [esi + 0feh]
    mov dword ptr [edi + 1b92h], eax
    mov eax, dword ptr [esi + 102h]
    mov dword ptr [edi + 1b96h], eax
    mov ax, word ptr [esi + 106h]
    mov word ptr [edi + 1b9ah], ax
    mov eax, dword ptr [esi + 120h]
    mov dword ptr [edi + 1e04h], eax
    mov eax, dword ptr [esi + 124h]
    mov dword ptr [edi + 1e08h], eax
    mov eax, dword ptr [esi + 128h]
    mov dword ptr [edi + 1e0ch], eax
    mov eax, dword ptr [esi + 12ch]
    mov dword ptr [edi + 1e10h], eax
    mov eax, dword ptr [esi + 130h]
    mov dword ptr [edi + 1e14h], eax
    mov eax, dword ptr [esi + 134h]
    mov dword ptr [edi + 1e18h], eax
    mov eax, dword ptr [esi + 152h]
    mov dword ptr [edi + 2082h], eax
    mov eax, dword ptr [esi + 156h]
    mov dword ptr [edi + 2086h], eax
    mov eax, dword ptr [esi + 15ah]
    mov dword ptr [edi + 208ah], eax
    mov eax, dword ptr [esi + 15eh]
    mov dword ptr [edi + 208eh], eax
    mov eax, dword ptr [esi + 162h]
    mov dword ptr [edi + 2092h], eax
    mov eax, dword ptr [esi + 166h]
    mov dword ptr [edi + 2096h], eax
    mov ax, word ptr [esi + 16ah]
    mov word ptr [edi + 209ah], ax
    mov eax, dword ptr [esi + 188h]
    mov dword ptr [edi + 2300h], eax
    mov eax, dword ptr [esi + 18ch]
    mov dword ptr [edi + 2304h], eax
    mov eax, dword ptr [esi + 190h]
    mov dword ptr [edi + 2308h], eax
    mov eax, dword ptr [esi + 194h]
    mov dword ptr [edi + 230ch], eax
    mov eax, dword ptr [esi + 198h]
    mov dword ptr [edi + 2310h], eax
    mov eax, dword ptr [esi + 19ch]
    mov dword ptr [edi + 2314h], eax
    mov eax, dword ptr [esi + 1a0h]
    mov dword ptr [edi + 2318h], eax
    cmp ebx, 1
    jne place_i_large_diamond_righthalf_L2
    jmp near ptr place_i_large_diamond_righthalf_L3
place_i_large_diamond_righthalf_L2:
    mov eax, dword ptr [esi + 1c2h]
    mov dword ptr [edi + 2580h], eax
    mov eax, dword ptr [esi + 1c6h]
    mov dword ptr [edi + 2584h], eax
    mov eax, dword ptr [esi + 1cah]
    mov dword ptr [edi + 2588h], eax
    mov eax, dword ptr [esi + 1ceh]
    mov dword ptr [edi + 258ch], eax
    mov eax, dword ptr [esi + 1d2h]
    mov dword ptr [edi + 2590h], eax
    mov eax, dword ptr [esi + 1d6h]
    mov dword ptr [edi + 2594h], eax
    mov eax, dword ptr [esi + 1dah]
    mov dword ptr [edi + 2598h], eax
    mov eax, dword ptr [esi + 1fch]
    mov dword ptr [edi + 2802h], eax
    mov eax, dword ptr [esi + 200h]
    mov dword ptr [edi + 2806h], eax
    mov eax, dword ptr [esi + 204h]
    mov dword ptr [edi + 280ah], eax
    mov eax, dword ptr [esi + 208h]
    mov dword ptr [edi + 280eh], eax
    mov eax, dword ptr [esi + 20ch]
    mov dword ptr [edi + 2812h], eax
    mov eax, dword ptr [esi + 210h]
    mov dword ptr [edi + 2816h], eax
    mov ax, word ptr [esi + 214h]
    mov word ptr [edi + 281ah], ax
    mov eax, dword ptr [esi + 232h]
    mov dword ptr [edi + 2a84h], eax
    mov eax, dword ptr [esi + 236h]
    mov dword ptr [edi + 2a88h], eax
    mov eax, dword ptr [esi + 23ah]
    mov dword ptr [edi + 2a8ch], eax
    mov eax, dword ptr [esi + 23eh]
    mov dword ptr [edi + 2a90h], eax
    mov eax, dword ptr [esi + 242h]
    mov dword ptr [edi + 2a94h], eax
    mov eax, dword ptr [esi + 246h]
    mov dword ptr [edi + 2a98h], eax
    mov eax, dword ptr [esi + 264h]
    mov dword ptr [edi + 2d06h], eax
    mov eax, dword ptr [esi + 268h]
    mov dword ptr [edi + 2d0ah], eax
    mov eax, dword ptr [esi + 26ch]
    mov dword ptr [edi + 2d0eh], eax
    mov eax, dword ptr [esi + 270h]
    mov dword ptr [edi + 2d12h], eax
    mov eax, dword ptr [esi + 274h]
    mov dword ptr [edi + 2d16h], eax
    mov ax, word ptr [esi + 278h]
    mov word ptr [edi + 2d1ah], ax
    mov eax, dword ptr [esi + 292h]
    mov dword ptr [edi + 2f88h], eax
    mov eax, dword ptr [esi + 296h]
    mov dword ptr [edi + 2f8ch], eax
    mov eax, dword ptr [esi + 29ah]
    mov dword ptr [edi + 2f90h], eax
    mov eax, dword ptr [esi + 29eh]
    mov dword ptr [edi + 2f94h], eax
    mov eax, dword ptr [esi + 2a2h]
    mov dword ptr [edi + 2f98h], eax
    mov eax, dword ptr [esi + 2bch]
    mov dword ptr [edi + 320ah], eax
    mov eax, dword ptr [esi + 2c0h]
    mov dword ptr [edi + 320eh], eax
    mov eax, dword ptr [esi + 2c4h]
    mov dword ptr [edi + 3212h], eax
    mov eax, dword ptr [esi + 2c8h]
    mov dword ptr [edi + 3216h], eax
    mov ax, word ptr [esi + 2cch]
    mov word ptr [edi + 321ah], ax
    mov eax, dword ptr [esi + 2e2h]
    mov dword ptr [edi + 348ch], eax
    mov eax, dword ptr [esi + 2e6h]
    mov dword ptr [edi + 3490h], eax
    mov eax, dword ptr [esi + 2eah]
    mov dword ptr [edi + 3494h], eax
    mov eax, dword ptr [esi + 2eeh]
    mov dword ptr [edi + 3498h], eax
    mov eax, dword ptr [esi + 304h]
    mov dword ptr [edi + 370eh], eax
    mov eax, dword ptr [esi + 308h]
    mov dword ptr [edi + 3712h], eax
    mov eax, dword ptr [esi + 30ch]
    mov dword ptr [edi + 3716h], eax
    mov ax, word ptr [esi + 310h]
    mov word ptr [edi + 371ah], ax
    mov eax, dword ptr [esi + 322h]
    mov dword ptr [edi + 3990h], eax
    mov eax, dword ptr [esi + 326h]
    mov dword ptr [edi + 3994h], eax
    mov eax, dword ptr [esi + 32ah]
    mov dword ptr [edi + 3998h], eax
    mov eax, dword ptr [esi + 33ch]
    mov dword ptr [edi + 3c12h], eax
    mov eax, dword ptr [esi + 340h]
    mov dword ptr [edi + 3c16h], eax
    mov ax, word ptr [esi + 344h]
    mov word ptr [edi + 3c1ah], ax
    mov eax, dword ptr [esi + 352h]
    mov dword ptr [edi + 3e94h], eax
    mov eax, dword ptr [esi + 356h]
    mov dword ptr [edi + 3e98h], eax
    mov eax, dword ptr [esi + 364h]
    mov dword ptr [edi + 4116h], eax
    mov ax, word ptr [esi + 368h]
    mov word ptr [edi + 411ah], ax
    mov eax, dword ptr [esi + 372h]
    mov dword ptr [edi + 4398h], eax
    mov ax, word ptr [esi + 37ch]
    mov word ptr [edi + 461ah], ax
place_i_large_diamond_righthalf_L3:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_large_diamond_hat
; ════════════════════════════════════════════════════════════
write_large_diamond_hat_:
    pushad
    mov esi, eax
    mov ebx, edx
    mov ecx, 0
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
write_large_diamond_hat_L1:
    cmp ebx, ecx
    jle near ptr write_large_diamond_hat_L60
    sub edi, dword ptr [_screen_width]
    push edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L2
    mov byte ptr [edi + 2300h], al
write_large_diamond_hat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L3
    mov byte ptr [edi + 2301h], al
write_large_diamond_hat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L4
    mov byte ptr [edi + 2080h], al
write_large_diamond_hat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L5
    mov byte ptr [edi + 2081h], al
write_large_diamond_hat_L5:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L6
    mov byte ptr [edi + 1e00h], al
write_large_diamond_hat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L7
    mov byte ptr [edi + 1e01h], al
write_large_diamond_hat_L7:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L8
    mov byte ptr [edi + 1b80h], al
write_large_diamond_hat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L9
    mov byte ptr [edi + 1b81h], al
write_large_diamond_hat_L9:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L10
    mov byte ptr [edi + 1900h], al
write_large_diamond_hat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L11
    mov byte ptr [edi + 1901h], al
write_large_diamond_hat_L11:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L12
    mov byte ptr [edi + 1680h], al
write_large_diamond_hat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L13
    mov byte ptr [edi + 1681h], al
write_large_diamond_hat_L13:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L14
    mov byte ptr [edi + 1400h], al
write_large_diamond_hat_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L15
    mov byte ptr [edi + 1401h], al
write_large_diamond_hat_L15:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L16
    mov byte ptr [edi + 1180h], al
write_large_diamond_hat_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L17
    mov byte ptr [edi + 1181h], al
write_large_diamond_hat_L17:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L18
    mov byte ptr [edi + 0f00h], al
write_large_diamond_hat_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L19
    mov byte ptr [edi + 0f01h], al
write_large_diamond_hat_L19:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L20
    mov byte ptr [edi + 0c80h], al
write_large_diamond_hat_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L21
    mov byte ptr [edi + 0c81h], al
write_large_diamond_hat_L21:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L22
    mov byte ptr [edi + 0a00h], al
write_large_diamond_hat_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L23
    mov byte ptr [edi + 0a01h], al
write_large_diamond_hat_L23:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L24
    mov byte ptr [edi + 780h], al
write_large_diamond_hat_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L25
    mov byte ptr [edi + 781h], al
write_large_diamond_hat_L25:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L26
    mov byte ptr [edi + 500h], al
write_large_diamond_hat_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L27
    mov byte ptr [edi + 501h], al
write_large_diamond_hat_L27:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L28
    mov byte ptr [edi + 280h], al
write_large_diamond_hat_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L29
    mov byte ptr [edi + 281h], al
write_large_diamond_hat_L29:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L30
    mov byte ptr [edi], al
write_large_diamond_hat_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L31
    mov byte ptr [edi + 1], al
write_large_diamond_hat_L31:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L32
    mov byte ptr [edi + 280h], al
write_large_diamond_hat_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L33
    mov byte ptr [edi + 281h], al
write_large_diamond_hat_L33:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L34
    mov byte ptr [edi + 500h], al
write_large_diamond_hat_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L35
    mov byte ptr [edi + 501h], al
write_large_diamond_hat_L35:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L36
    mov byte ptr [edi + 780h], al
write_large_diamond_hat_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L37
    mov byte ptr [edi + 781h], al
write_large_diamond_hat_L37:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L38
    mov byte ptr [edi + 0a00h], al
write_large_diamond_hat_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L39
    mov byte ptr [edi + 0a01h], al
write_large_diamond_hat_L39:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L40
    mov byte ptr [edi + 0c80h], al
write_large_diamond_hat_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L41
    mov byte ptr [edi + 0c81h], al
write_large_diamond_hat_L41:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L42
    mov byte ptr [edi + 0f00h], al
write_large_diamond_hat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L43
    mov byte ptr [edi + 0f01h], al
write_large_diamond_hat_L43:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L44
    mov byte ptr [edi + 1180h], al
write_large_diamond_hat_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L45
    mov byte ptr [edi + 1181h], al
write_large_diamond_hat_L45:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L46
    mov byte ptr [edi + 1400h], al
write_large_diamond_hat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L47
    mov byte ptr [edi + 1401h], al
write_large_diamond_hat_L47:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L48
    mov byte ptr [edi + 1680h], al
write_large_diamond_hat_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L49
    mov byte ptr [edi + 1681h], al
write_large_diamond_hat_L49:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L50
    mov byte ptr [edi + 1900h], al
write_large_diamond_hat_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L51
    mov byte ptr [edi + 1901h], al
write_large_diamond_hat_L51:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L52
    mov byte ptr [edi + 1b80h], al
write_large_diamond_hat_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L53
    mov byte ptr [edi + 1b81h], al
write_large_diamond_hat_L53:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L54
    mov byte ptr [edi + 1e00h], al
write_large_diamond_hat_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L55
    mov byte ptr [edi + 1e01h], al
write_large_diamond_hat_L55:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L56
    mov byte ptr [edi + 2080h], al
write_large_diamond_hat_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L57
    mov byte ptr [edi + 2081h], al
write_large_diamond_hat_L57:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L58
    mov byte ptr [edi + 2300h], al
write_large_diamond_hat_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L59
    mov byte ptr [edi + 2301h], al
write_large_diamond_hat_L59:
    inc esi
    add edi, 2
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_large_diamond_hat_L1
    popad
    ret
write_large_diamond_hat_L60:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L61
    mov byte ptr [edi + 2080h], al
write_large_diamond_hat_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L62
    mov byte ptr [edi + 2081h], al
write_large_diamond_hat_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L63
    mov byte ptr [edi + 1e02h], al
write_large_diamond_hat_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L64
    mov byte ptr [edi + 1e03h], al
write_large_diamond_hat_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L65
    mov byte ptr [edi + 1b84h], al
write_large_diamond_hat_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L66
    mov byte ptr [edi + 1b85h], al
write_large_diamond_hat_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L67
    mov byte ptr [edi + 1906h], al
write_large_diamond_hat_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L68
    mov byte ptr [edi + 1907h], al
write_large_diamond_hat_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L69
    mov byte ptr [edi + 1688h], al
write_large_diamond_hat_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L70
    mov byte ptr [edi + 1689h], al
write_large_diamond_hat_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L71
    mov byte ptr [edi + 140ah], al
write_large_diamond_hat_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L72
    mov byte ptr [edi + 140bh], al
write_large_diamond_hat_L72:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L73
    mov byte ptr [edi + 118ch], al
write_large_diamond_hat_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L74
    mov byte ptr [edi + 118dh], al
write_large_diamond_hat_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L75
    mov byte ptr [edi + 0f0eh], al
write_large_diamond_hat_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L76
    mov byte ptr [edi + 0f0fh], al
write_large_diamond_hat_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L77
    mov byte ptr [edi + 0c90h], al
write_large_diamond_hat_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L78
    mov byte ptr [edi + 0c91h], al
write_large_diamond_hat_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L79
    mov byte ptr [edi + 0a12h], al
write_large_diamond_hat_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L80
    mov byte ptr [edi + 0a13h], al
write_large_diamond_hat_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L81
    mov byte ptr [edi + 794h], al
write_large_diamond_hat_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L82
    mov byte ptr [edi + 795h], al
write_large_diamond_hat_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L83
    mov byte ptr [edi + 516h], al
write_large_diamond_hat_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L84
    mov byte ptr [edi + 517h], al
write_large_diamond_hat_L84:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L85
    mov byte ptr [edi + 298h], al
write_large_diamond_hat_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L86
    mov byte ptr [edi + 299h], al
write_large_diamond_hat_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L87
    mov byte ptr [edi + 1ah], al
write_large_diamond_hat_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L88
    mov byte ptr [edi + 1bh], al
write_large_diamond_hat_L88:
    inc esi
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L89
    mov byte ptr [edi + 1eh], al
write_large_diamond_hat_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L90
    mov byte ptr [edi + 1fh], al
write_large_diamond_hat_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L91
    mov byte ptr [edi + 2a0h], al
write_large_diamond_hat_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L92
    mov byte ptr [edi + 2a1h], al
write_large_diamond_hat_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L93
    mov byte ptr [edi + 522h], al
write_large_diamond_hat_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L94
    mov byte ptr [edi + 523h], al
write_large_diamond_hat_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L95
    mov byte ptr [edi + 7a4h], al
write_large_diamond_hat_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L96
    mov byte ptr [edi + 7a5h], al
write_large_diamond_hat_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L97
    mov byte ptr [edi + 0a26h], al
write_large_diamond_hat_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L98
    mov byte ptr [edi + 0a27h], al
write_large_diamond_hat_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L99
    mov byte ptr [edi + 0ca8h], al
write_large_diamond_hat_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L100
    mov byte ptr [edi + 0ca9h], al
write_large_diamond_hat_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L101
    mov byte ptr [edi + 0f2ah], al
write_large_diamond_hat_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L102
    mov byte ptr [edi + 0f2bh], al
write_large_diamond_hat_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L103
    mov byte ptr [edi + 11ach], al
write_large_diamond_hat_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L104
    mov byte ptr [edi + 11adh], al
write_large_diamond_hat_L104:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L105
    mov byte ptr [edi + 142eh], al
write_large_diamond_hat_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L106
    mov byte ptr [edi + 142fh], al
write_large_diamond_hat_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L107
    mov byte ptr [edi + 16b0h], al
write_large_diamond_hat_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L108
    mov byte ptr [edi + 16b1h], al
write_large_diamond_hat_L108:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L109
    mov byte ptr [edi + 1932h], al
write_large_diamond_hat_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L110
    mov byte ptr [edi + 1933h], al
write_large_diamond_hat_L110:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L111
    mov byte ptr [edi + 1bb4h], al
write_large_diamond_hat_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L112
    mov byte ptr [edi + 1bb5h], al
write_large_diamond_hat_L112:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L113
    mov byte ptr [edi + 1e36h], al
write_large_diamond_hat_L113:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L114
    mov byte ptr [edi + 1e37h], al
write_large_diamond_hat_L114:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L115
    mov byte ptr [edi + 20b8h], al
write_large_diamond_hat_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L116
    mov byte ptr [edi + 20b9h], al
write_large_diamond_hat_L116:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L117
    mov byte ptr [edi + 1e00h], al
write_large_diamond_hat_L117:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L118
    mov byte ptr [edi + 1e01h], al
write_large_diamond_hat_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L119
    mov byte ptr [edi + 1b82h], al
write_large_diamond_hat_L119:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L120
    mov byte ptr [edi + 1b83h], al
write_large_diamond_hat_L120:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L121
    mov byte ptr [edi + 1904h], al
write_large_diamond_hat_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L122
    mov byte ptr [edi + 1905h], al
write_large_diamond_hat_L122:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L123
    mov byte ptr [edi + 1686h], al
write_large_diamond_hat_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L124
    mov byte ptr [edi + 1687h], al
write_large_diamond_hat_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L125
    mov byte ptr [edi + 1408h], al
write_large_diamond_hat_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L126
    mov byte ptr [edi + 1409h], al
write_large_diamond_hat_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L127
    mov byte ptr [edi + 118ah], al
write_large_diamond_hat_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L128
    mov byte ptr [edi + 118bh], al
write_large_diamond_hat_L128:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L129
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_hat_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L130
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_hat_L130:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L131
    mov byte ptr [edi + 0c8eh], al
write_large_diamond_hat_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L132
    mov byte ptr [edi + 0c8fh], al
write_large_diamond_hat_L132:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L133
    mov byte ptr [edi + 0a10h], al
write_large_diamond_hat_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L134
    mov byte ptr [edi + 0a11h], al
write_large_diamond_hat_L134:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L135
    mov byte ptr [edi + 792h], al
write_large_diamond_hat_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L136
    mov byte ptr [edi + 793h], al
write_large_diamond_hat_L136:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L137
    mov byte ptr [edi + 514h], al
write_large_diamond_hat_L137:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L138
    mov byte ptr [edi + 515h], al
write_large_diamond_hat_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L139
    mov byte ptr [edi + 296h], al
write_large_diamond_hat_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L140
    mov byte ptr [edi + 297h], al
write_large_diamond_hat_L140:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L141
    mov byte ptr [edi + 18h], al
write_large_diamond_hat_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L142
    mov byte ptr [edi + 19h], al
write_large_diamond_hat_L142:
    inc esi
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L143
    mov byte ptr [edi + 20h], al
write_large_diamond_hat_L143:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L144
    mov byte ptr [edi + 21h], al
write_large_diamond_hat_L144:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L145
    mov byte ptr [edi + 2a2h], al
write_large_diamond_hat_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L146
    mov byte ptr [edi + 2a3h], al
write_large_diamond_hat_L146:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L147
    mov byte ptr [edi + 524h], al
write_large_diamond_hat_L147:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L148
    mov byte ptr [edi + 525h], al
write_large_diamond_hat_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L149
    mov byte ptr [edi + 7a6h], al
write_large_diamond_hat_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L150
    mov byte ptr [edi + 7a7h], al
write_large_diamond_hat_L150:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L151
    mov byte ptr [edi + 0a28h], al
write_large_diamond_hat_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L152
    mov byte ptr [edi + 0a29h], al
write_large_diamond_hat_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L153
    mov byte ptr [edi + 0caah], al
write_large_diamond_hat_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L154
    mov byte ptr [edi + 0cabh], al
write_large_diamond_hat_L154:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L155
    mov byte ptr [edi + 0f2ch], al
write_large_diamond_hat_L155:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L156
    mov byte ptr [edi + 0f2dh], al
write_large_diamond_hat_L156:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L157
    mov byte ptr [edi + 11aeh], al
write_large_diamond_hat_L157:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L158
    mov byte ptr [edi + 11afh], al
write_large_diamond_hat_L158:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L159
    mov byte ptr [edi + 1430h], al
write_large_diamond_hat_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L160
    mov byte ptr [edi + 1431h], al
write_large_diamond_hat_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L161
    mov byte ptr [edi + 16b2h], al
write_large_diamond_hat_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L162
    mov byte ptr [edi + 16b3h], al
write_large_diamond_hat_L162:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L163
    mov byte ptr [edi + 1934h], al
write_large_diamond_hat_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L164
    mov byte ptr [edi + 1935h], al
write_large_diamond_hat_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L165
    mov byte ptr [edi + 1bb6h], al
write_large_diamond_hat_L165:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L166
    mov byte ptr [edi + 1bb7h], al
write_large_diamond_hat_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L167
    mov byte ptr [edi + 1e38h], al
write_large_diamond_hat_L167:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L168
    mov byte ptr [edi + 1e39h], al
write_large_diamond_hat_L168:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L169
    mov byte ptr [edi + 1b80h], al
write_large_diamond_hat_L169:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L170
    mov byte ptr [edi + 1b81h], al
write_large_diamond_hat_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L171
    mov byte ptr [edi + 1902h], al
write_large_diamond_hat_L171:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L172
    mov byte ptr [edi + 1903h], al
write_large_diamond_hat_L172:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L173
    mov byte ptr [edi + 1684h], al
write_large_diamond_hat_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L174
    mov byte ptr [edi + 1685h], al
write_large_diamond_hat_L174:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L175
    mov byte ptr [edi + 1406h], al
write_large_diamond_hat_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L176
    mov byte ptr [edi + 1407h], al
write_large_diamond_hat_L176:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L177
    mov byte ptr [edi + 1188h], al
write_large_diamond_hat_L177:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L178
    mov byte ptr [edi + 1189h], al
write_large_diamond_hat_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L179
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_hat_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L180
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_hat_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L181
    mov byte ptr [edi + 0c8ch], al
write_large_diamond_hat_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L182
    mov byte ptr [edi + 0c8dh], al
write_large_diamond_hat_L182:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L183
    mov byte ptr [edi + 0a0eh], al
write_large_diamond_hat_L183:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L184
    mov byte ptr [edi + 0a0fh], al
write_large_diamond_hat_L184:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L185
    mov byte ptr [edi + 790h], al
write_large_diamond_hat_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L186
    mov byte ptr [edi + 791h], al
write_large_diamond_hat_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L187
    mov byte ptr [edi + 512h], al
write_large_diamond_hat_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L188
    mov byte ptr [edi + 513h], al
write_large_diamond_hat_L188:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L189
    mov byte ptr [edi + 294h], al
write_large_diamond_hat_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L190
    mov byte ptr [edi + 295h], al
write_large_diamond_hat_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L191
    mov byte ptr [edi + 16h], al
write_large_diamond_hat_L191:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L192
    mov byte ptr [edi + 17h], al
write_large_diamond_hat_L192:
    inc esi
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L193
    mov byte ptr [edi + 22h], al
write_large_diamond_hat_L193:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L194
    mov byte ptr [edi + 23h], al
write_large_diamond_hat_L194:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L195
    mov byte ptr [edi + 2a4h], al
write_large_diamond_hat_L195:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L196
    mov byte ptr [edi + 2a5h], al
write_large_diamond_hat_L196:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L197
    mov byte ptr [edi + 526h], al
write_large_diamond_hat_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L198
    mov byte ptr [edi + 527h], al
write_large_diamond_hat_L198:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L199
    mov byte ptr [edi + 7a8h], al
write_large_diamond_hat_L199:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L200
    mov byte ptr [edi + 7a9h], al
write_large_diamond_hat_L200:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L201
    mov byte ptr [edi + 0a2ah], al
write_large_diamond_hat_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L202
    mov byte ptr [edi + 0a2bh], al
write_large_diamond_hat_L202:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L203
    mov byte ptr [edi + 0cach], al
write_large_diamond_hat_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L204
    mov byte ptr [edi + 0cadh], al
write_large_diamond_hat_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L205
    mov byte ptr [edi + 0f2eh], al
write_large_diamond_hat_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L206
    mov byte ptr [edi + 0f2fh], al
write_large_diamond_hat_L206:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L207
    mov byte ptr [edi + 11b0h], al
write_large_diamond_hat_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L208
    mov byte ptr [edi + 11b1h], al
write_large_diamond_hat_L208:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L209
    mov byte ptr [edi + 1432h], al
write_large_diamond_hat_L209:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L210
    mov byte ptr [edi + 1433h], al
write_large_diamond_hat_L210:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L211
    mov byte ptr [edi + 16b4h], al
write_large_diamond_hat_L211:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L212
    mov byte ptr [edi + 16b5h], al
write_large_diamond_hat_L212:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L213
    mov byte ptr [edi + 1936h], al
write_large_diamond_hat_L213:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L214
    mov byte ptr [edi + 1937h], al
write_large_diamond_hat_L214:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L215
    mov byte ptr [edi + 1bb8h], al
write_large_diamond_hat_L215:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L216
    mov byte ptr [edi + 1bb9h], al
write_large_diamond_hat_L216:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L217
    mov byte ptr [edi + 1900h], al
write_large_diamond_hat_L217:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L218
    mov byte ptr [edi + 1901h], al
write_large_diamond_hat_L218:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L219
    mov byte ptr [edi + 1682h], al
write_large_diamond_hat_L219:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L220
    mov byte ptr [edi + 1683h], al
write_large_diamond_hat_L220:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L221
    mov byte ptr [edi + 1404h], al
write_large_diamond_hat_L221:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L222
    mov byte ptr [edi + 1405h], al
write_large_diamond_hat_L222:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L223
    mov byte ptr [edi + 1186h], al
write_large_diamond_hat_L223:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L224
    mov byte ptr [edi + 1187h], al
write_large_diamond_hat_L224:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L225
    mov byte ptr [edi + 0f08h], al
write_large_diamond_hat_L225:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L226
    mov byte ptr [edi + 0f09h], al
write_large_diamond_hat_L226:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L227
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_hat_L227:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L228
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_hat_L228:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L229
    mov byte ptr [edi + 0a0ch], al
write_large_diamond_hat_L229:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L230
    mov byte ptr [edi + 0a0dh], al
write_large_diamond_hat_L230:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L231
    mov byte ptr [edi + 78eh], al
write_large_diamond_hat_L231:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L232
    mov byte ptr [edi + 78fh], al
write_large_diamond_hat_L232:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L233
    mov byte ptr [edi + 510h], al
write_large_diamond_hat_L233:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L234
    mov byte ptr [edi + 511h], al
write_large_diamond_hat_L234:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L235
    mov byte ptr [edi + 292h], al
write_large_diamond_hat_L235:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L236
    mov byte ptr [edi + 293h], al
write_large_diamond_hat_L236:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L237
    mov byte ptr [edi + 14h], al
write_large_diamond_hat_L237:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L238
    mov byte ptr [edi + 15h], al
write_large_diamond_hat_L238:
    inc esi
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L239
    mov byte ptr [edi + 24h], al
write_large_diamond_hat_L239:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L240
    mov byte ptr [edi + 25h], al
write_large_diamond_hat_L240:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L241
    mov byte ptr [edi + 2a6h], al
write_large_diamond_hat_L241:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L242
    mov byte ptr [edi + 2a7h], al
write_large_diamond_hat_L242:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L243
    mov byte ptr [edi + 528h], al
write_large_diamond_hat_L243:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L244
    mov byte ptr [edi + 529h], al
write_large_diamond_hat_L244:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L245
    mov byte ptr [edi + 7aah], al
write_large_diamond_hat_L245:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L246
    mov byte ptr [edi + 7abh], al
write_large_diamond_hat_L246:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L247
    mov byte ptr [edi + 0a2ch], al
write_large_diamond_hat_L247:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L248
    mov byte ptr [edi + 0a2dh], al
write_large_diamond_hat_L248:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L249
    mov byte ptr [edi + 0caeh], al
write_large_diamond_hat_L249:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L250
    mov byte ptr [edi + 0cafh], al
write_large_diamond_hat_L250:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L251
    mov byte ptr [edi + 0f30h], al
write_large_diamond_hat_L251:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L252
    mov byte ptr [edi + 0f31h], al
write_large_diamond_hat_L252:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L253
    mov byte ptr [edi + 11b2h], al
write_large_diamond_hat_L253:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L254
    mov byte ptr [edi + 11b3h], al
write_large_diamond_hat_L254:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L255
    mov byte ptr [edi + 1434h], al
write_large_diamond_hat_L255:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L256
    mov byte ptr [edi + 1435h], al
write_large_diamond_hat_L256:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L257
    mov byte ptr [edi + 16b6h], al
write_large_diamond_hat_L257:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L258
    mov byte ptr [edi + 16b7h], al
write_large_diamond_hat_L258:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L259
    mov byte ptr [edi + 1938h], al
write_large_diamond_hat_L259:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L260
    mov byte ptr [edi + 1939h], al
write_large_diamond_hat_L260:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L261
    mov byte ptr [edi + 1680h], al
write_large_diamond_hat_L261:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L262
    mov byte ptr [edi + 1681h], al
write_large_diamond_hat_L262:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L263
    mov byte ptr [edi + 1402h], al
write_large_diamond_hat_L263:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L264
    mov byte ptr [edi + 1403h], al
write_large_diamond_hat_L264:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L265
    mov byte ptr [edi + 1184h], al
write_large_diamond_hat_L265:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L266
    mov byte ptr [edi + 1185h], al
write_large_diamond_hat_L266:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L267
    mov byte ptr [edi + 0f06h], al
write_large_diamond_hat_L267:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L268
    mov byte ptr [edi + 0f07h], al
write_large_diamond_hat_L268:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L269
    mov byte ptr [edi + 0c88h], al
write_large_diamond_hat_L269:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L270
    mov byte ptr [edi + 0c89h], al
write_large_diamond_hat_L270:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L271
    mov byte ptr [edi + 0a0ah], al
write_large_diamond_hat_L271:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L272
    mov byte ptr [edi + 0a0bh], al
write_large_diamond_hat_L272:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L273
    mov byte ptr [edi + 78ch], al
write_large_diamond_hat_L273:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L274
    mov byte ptr [edi + 78dh], al
write_large_diamond_hat_L274:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L275
    mov byte ptr [edi + 50eh], al
write_large_diamond_hat_L275:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L276
    mov byte ptr [edi + 50fh], al
write_large_diamond_hat_L276:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L277
    mov byte ptr [edi + 290h], al
write_large_diamond_hat_L277:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L278
    mov byte ptr [edi + 291h], al
write_large_diamond_hat_L278:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L279
    mov byte ptr [edi + 12h], al
write_large_diamond_hat_L279:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L280
    mov byte ptr [edi + 13h], al
write_large_diamond_hat_L280:
    inc esi
    add esi, 12h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L281
    mov byte ptr [edi + 26h], al
write_large_diamond_hat_L281:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L282
    mov byte ptr [edi + 27h], al
write_large_diamond_hat_L282:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L283
    mov byte ptr [edi + 2a8h], al
write_large_diamond_hat_L283:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L284
    mov byte ptr [edi + 2a9h], al
write_large_diamond_hat_L284:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L285
    mov byte ptr [edi + 52ah], al
write_large_diamond_hat_L285:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L286
    mov byte ptr [edi + 52bh], al
write_large_diamond_hat_L286:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L287
    mov byte ptr [edi + 7ach], al
write_large_diamond_hat_L287:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L288
    mov byte ptr [edi + 7adh], al
write_large_diamond_hat_L288:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L289
    mov byte ptr [edi + 0a2eh], al
write_large_diamond_hat_L289:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L290
    mov byte ptr [edi + 0a2fh], al
write_large_diamond_hat_L290:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L291
    mov byte ptr [edi + 0cb0h], al
write_large_diamond_hat_L291:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L292
    mov byte ptr [edi + 0cb1h], al
write_large_diamond_hat_L292:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L293
    mov byte ptr [edi + 0f32h], al
write_large_diamond_hat_L293:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L294
    mov byte ptr [edi + 0f33h], al
write_large_diamond_hat_L294:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L295
    mov byte ptr [edi + 11b4h], al
write_large_diamond_hat_L295:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L296
    mov byte ptr [edi + 11b5h], al
write_large_diamond_hat_L296:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L297
    mov byte ptr [edi + 1436h], al
write_large_diamond_hat_L297:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L298
    mov byte ptr [edi + 1437h], al
write_large_diamond_hat_L298:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L299
    mov byte ptr [edi + 16b8h], al
write_large_diamond_hat_L299:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L300
    mov byte ptr [edi + 16b9h], al
write_large_diamond_hat_L300:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L301
    mov byte ptr [edi + 1400h], al
write_large_diamond_hat_L301:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L302
    mov byte ptr [edi + 1401h], al
write_large_diamond_hat_L302:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L303
    mov byte ptr [edi + 1182h], al
write_large_diamond_hat_L303:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L304
    mov byte ptr [edi + 1183h], al
write_large_diamond_hat_L304:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L305
    mov byte ptr [edi + 0f04h], al
write_large_diamond_hat_L305:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L306
    mov byte ptr [edi + 0f05h], al
write_large_diamond_hat_L306:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L307
    mov byte ptr [edi + 0c86h], al
write_large_diamond_hat_L307:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L308
    mov byte ptr [edi + 0c87h], al
write_large_diamond_hat_L308:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L309
    mov byte ptr [edi + 0a08h], al
write_large_diamond_hat_L309:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L310
    mov byte ptr [edi + 0a09h], al
write_large_diamond_hat_L310:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L311
    mov byte ptr [edi + 78ah], al
write_large_diamond_hat_L311:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L312
    mov byte ptr [edi + 78bh], al
write_large_diamond_hat_L312:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L313
    mov byte ptr [edi + 50ch], al
write_large_diamond_hat_L313:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L314
    mov byte ptr [edi + 50dh], al
write_large_diamond_hat_L314:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L315
    mov byte ptr [edi + 28eh], al
write_large_diamond_hat_L315:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L316
    mov byte ptr [edi + 28fh], al
write_large_diamond_hat_L316:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L317
    mov byte ptr [edi + 10h], al
write_large_diamond_hat_L317:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L318
    mov byte ptr [edi + 11h], al
write_large_diamond_hat_L318:
    inc esi
    add esi, 16h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L319
    mov byte ptr [edi + 28h], al
write_large_diamond_hat_L319:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L320
    mov byte ptr [edi + 29h], al
write_large_diamond_hat_L320:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L321
    mov byte ptr [edi + 2aah], al
write_large_diamond_hat_L321:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L322
    mov byte ptr [edi + 2abh], al
write_large_diamond_hat_L322:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L323
    mov byte ptr [edi + 52ch], al
write_large_diamond_hat_L323:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L324
    mov byte ptr [edi + 52dh], al
write_large_diamond_hat_L324:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L325
    mov byte ptr [edi + 7aeh], al
write_large_diamond_hat_L325:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L326
    mov byte ptr [edi + 7afh], al
write_large_diamond_hat_L326:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L327
    mov byte ptr [edi + 0a30h], al
write_large_diamond_hat_L327:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L328
    mov byte ptr [edi + 0a31h], al
write_large_diamond_hat_L328:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L329
    mov byte ptr [edi + 0cb2h], al
write_large_diamond_hat_L329:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L330
    mov byte ptr [edi + 0cb3h], al
write_large_diamond_hat_L330:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L331
    mov byte ptr [edi + 0f34h], al
write_large_diamond_hat_L331:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L332
    mov byte ptr [edi + 0f35h], al
write_large_diamond_hat_L332:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L333
    mov byte ptr [edi + 11b6h], al
write_large_diamond_hat_L333:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L334
    mov byte ptr [edi + 11b7h], al
write_large_diamond_hat_L334:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L335
    mov byte ptr [edi + 1438h], al
write_large_diamond_hat_L335:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L336
    mov byte ptr [edi + 1439h], al
write_large_diamond_hat_L336:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L337
    mov byte ptr [edi + 1180h], al
write_large_diamond_hat_L337:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L338
    mov byte ptr [edi + 1181h], al
write_large_diamond_hat_L338:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L339
    mov byte ptr [edi + 0f02h], al
write_large_diamond_hat_L339:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L340
    mov byte ptr [edi + 0f03h], al
write_large_diamond_hat_L340:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L341
    mov byte ptr [edi + 0c84h], al
write_large_diamond_hat_L341:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L342
    mov byte ptr [edi + 0c85h], al
write_large_diamond_hat_L342:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L343
    mov byte ptr [edi + 0a06h], al
write_large_diamond_hat_L343:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L344
    mov byte ptr [edi + 0a07h], al
write_large_diamond_hat_L344:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L345
    mov byte ptr [edi + 788h], al
write_large_diamond_hat_L345:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L346
    mov byte ptr [edi + 789h], al
write_large_diamond_hat_L346:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L347
    mov byte ptr [edi + 50ah], al
write_large_diamond_hat_L347:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L348
    mov byte ptr [edi + 50bh], al
write_large_diamond_hat_L348:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L349
    mov byte ptr [edi + 28ch], al
write_large_diamond_hat_L349:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L350
    mov byte ptr [edi + 28dh], al
write_large_diamond_hat_L350:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L351
    mov byte ptr [edi + 0eh], al
write_large_diamond_hat_L351:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L352
    mov byte ptr [edi + 0fh], al
write_large_diamond_hat_L352:
    inc esi
    add esi, 1ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L353
    mov byte ptr [edi + 2ah], al
write_large_diamond_hat_L353:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L354
    mov byte ptr [edi + 2bh], al
write_large_diamond_hat_L354:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L355
    mov byte ptr [edi + 2ach], al
write_large_diamond_hat_L355:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L356
    mov byte ptr [edi + 2adh], al
write_large_diamond_hat_L356:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L357
    mov byte ptr [edi + 52eh], al
write_large_diamond_hat_L357:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L358
    mov byte ptr [edi + 52fh], al
write_large_diamond_hat_L358:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L359
    mov byte ptr [edi + 7b0h], al
write_large_diamond_hat_L359:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L360
    mov byte ptr [edi + 7b1h], al
write_large_diamond_hat_L360:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L361
    mov byte ptr [edi + 0a32h], al
write_large_diamond_hat_L361:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L362
    mov byte ptr [edi + 0a33h], al
write_large_diamond_hat_L362:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L363
    mov byte ptr [edi + 0cb4h], al
write_large_diamond_hat_L363:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L364
    mov byte ptr [edi + 0cb5h], al
write_large_diamond_hat_L364:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L365
    mov byte ptr [edi + 0f36h], al
write_large_diamond_hat_L365:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L366
    mov byte ptr [edi + 0f37h], al
write_large_diamond_hat_L366:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L367
    mov byte ptr [edi + 11b8h], al
write_large_diamond_hat_L367:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L368
    mov byte ptr [edi + 11b9h], al
write_large_diamond_hat_L368:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L369
    mov byte ptr [edi + 0f00h], al
write_large_diamond_hat_L369:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L370
    mov byte ptr [edi + 0f01h], al
write_large_diamond_hat_L370:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L371
    mov byte ptr [edi + 0c82h], al
write_large_diamond_hat_L371:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L372
    mov byte ptr [edi + 0c83h], al
write_large_diamond_hat_L372:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L373
    mov byte ptr [edi + 0a04h], al
write_large_diamond_hat_L373:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L374
    mov byte ptr [edi + 0a05h], al
write_large_diamond_hat_L374:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L375
    mov byte ptr [edi + 786h], al
write_large_diamond_hat_L375:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L376
    mov byte ptr [edi + 787h], al
write_large_diamond_hat_L376:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L377
    mov byte ptr [edi + 508h], al
write_large_diamond_hat_L377:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L378
    mov byte ptr [edi + 509h], al
write_large_diamond_hat_L378:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L379
    mov byte ptr [edi + 28ah], al
write_large_diamond_hat_L379:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L380
    mov byte ptr [edi + 28bh], al
write_large_diamond_hat_L380:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L381
    mov byte ptr [edi + 0ch], al
write_large_diamond_hat_L381:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L382
    mov byte ptr [edi + 0dh], al
write_large_diamond_hat_L382:
    inc esi
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L383
    mov byte ptr [edi + 2ch], al
write_large_diamond_hat_L383:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L384
    mov byte ptr [edi + 2dh], al
write_large_diamond_hat_L384:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L385
    mov byte ptr [edi + 2aeh], al
write_large_diamond_hat_L385:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L386
    mov byte ptr [edi + 2afh], al
write_large_diamond_hat_L386:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L387
    mov byte ptr [edi + 530h], al
write_large_diamond_hat_L387:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L388
    mov byte ptr [edi + 531h], al
write_large_diamond_hat_L388:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L389
    mov byte ptr [edi + 7b2h], al
write_large_diamond_hat_L389:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L390
    mov byte ptr [edi + 7b3h], al
write_large_diamond_hat_L390:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L391
    mov byte ptr [edi + 0a34h], al
write_large_diamond_hat_L391:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L392
    mov byte ptr [edi + 0a35h], al
write_large_diamond_hat_L392:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L393
    mov byte ptr [edi + 0cb6h], al
write_large_diamond_hat_L393:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L394
    mov byte ptr [edi + 0cb7h], al
write_large_diamond_hat_L394:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L395
    mov byte ptr [edi + 0f38h], al
write_large_diamond_hat_L395:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L396
    mov byte ptr [edi + 0f39h], al
write_large_diamond_hat_L396:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L397
    mov byte ptr [edi + 0c80h], al
write_large_diamond_hat_L397:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L398
    mov byte ptr [edi + 0c81h], al
write_large_diamond_hat_L398:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L399
    mov byte ptr [edi + 0a02h], al
write_large_diamond_hat_L399:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L400
    mov byte ptr [edi + 0a03h], al
write_large_diamond_hat_L400:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L401
    mov byte ptr [edi + 784h], al
write_large_diamond_hat_L401:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L402
    mov byte ptr [edi + 785h], al
write_large_diamond_hat_L402:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L403
    mov byte ptr [edi + 506h], al
write_large_diamond_hat_L403:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L404
    mov byte ptr [edi + 507h], al
write_large_diamond_hat_L404:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L405
    mov byte ptr [edi + 288h], al
write_large_diamond_hat_L405:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L406
    mov byte ptr [edi + 289h], al
write_large_diamond_hat_L406:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L407
    mov byte ptr [edi + 0ah], al
write_large_diamond_hat_L407:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L408
    mov byte ptr [edi + 0bh], al
write_large_diamond_hat_L408:
    inc esi
    add esi, 22h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L409
    mov byte ptr [edi + 2eh], al
write_large_diamond_hat_L409:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L410
    mov byte ptr [edi + 2fh], al
write_large_diamond_hat_L410:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L411
    mov byte ptr [edi + 2b0h], al
write_large_diamond_hat_L411:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L412
    mov byte ptr [edi + 2b1h], al
write_large_diamond_hat_L412:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L413
    mov byte ptr [edi + 532h], al
write_large_diamond_hat_L413:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L414
    mov byte ptr [edi + 533h], al
write_large_diamond_hat_L414:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L415
    mov byte ptr [edi + 7b4h], al
write_large_diamond_hat_L415:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L416
    mov byte ptr [edi + 7b5h], al
write_large_diamond_hat_L416:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L417
    mov byte ptr [edi + 0a36h], al
write_large_diamond_hat_L417:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L418
    mov byte ptr [edi + 0a37h], al
write_large_diamond_hat_L418:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L419
    mov byte ptr [edi + 0cb8h], al
write_large_diamond_hat_L419:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L420
    mov byte ptr [edi + 0cb9h], al
write_large_diamond_hat_L420:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L421
    mov byte ptr [edi + 0a00h], al
write_large_diamond_hat_L421:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L422
    mov byte ptr [edi + 0a01h], al
write_large_diamond_hat_L422:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L423
    mov byte ptr [edi + 782h], al
write_large_diamond_hat_L423:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L424
    mov byte ptr [edi + 783h], al
write_large_diamond_hat_L424:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L425
    mov byte ptr [edi + 504h], al
write_large_diamond_hat_L425:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L426
    mov byte ptr [edi + 505h], al
write_large_diamond_hat_L426:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L427
    mov byte ptr [edi + 286h], al
write_large_diamond_hat_L427:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L428
    mov byte ptr [edi + 287h], al
write_large_diamond_hat_L428:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L429
    mov byte ptr [edi + 8], al
write_large_diamond_hat_L429:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L430
    mov byte ptr [edi + 9], al
write_large_diamond_hat_L430:
    inc esi
    add esi, 26h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L431
    mov byte ptr [edi + 30h], al
write_large_diamond_hat_L431:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L432
    mov byte ptr [edi + 31h], al
write_large_diamond_hat_L432:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L433
    mov byte ptr [edi + 2b2h], al
write_large_diamond_hat_L433:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L434
    mov byte ptr [edi + 2b3h], al
write_large_diamond_hat_L434:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L435
    mov byte ptr [edi + 534h], al
write_large_diamond_hat_L435:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L436
    mov byte ptr [edi + 535h], al
write_large_diamond_hat_L436:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L437
    mov byte ptr [edi + 7b6h], al
write_large_diamond_hat_L437:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L438
    mov byte ptr [edi + 7b7h], al
write_large_diamond_hat_L438:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L439
    mov byte ptr [edi + 0a38h], al
write_large_diamond_hat_L439:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L440
    mov byte ptr [edi + 0a39h], al
write_large_diamond_hat_L440:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L441
    mov byte ptr [edi + 780h], al
write_large_diamond_hat_L441:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L442
    mov byte ptr [edi + 781h], al
write_large_diamond_hat_L442:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L443
    mov byte ptr [edi + 502h], al
write_large_diamond_hat_L443:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L444
    mov byte ptr [edi + 503h], al
write_large_diamond_hat_L444:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L445
    mov byte ptr [edi + 284h], al
write_large_diamond_hat_L445:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L446
    mov byte ptr [edi + 285h], al
write_large_diamond_hat_L446:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L447
    mov byte ptr [edi + 6], al
write_large_diamond_hat_L447:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L448
    mov byte ptr [edi + 7], al
write_large_diamond_hat_L448:
    inc esi
    add esi, 2ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L449
    mov byte ptr [edi + 32h], al
write_large_diamond_hat_L449:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L450
    mov byte ptr [edi + 33h], al
write_large_diamond_hat_L450:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L451
    mov byte ptr [edi + 2b4h], al
write_large_diamond_hat_L451:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L452
    mov byte ptr [edi + 2b5h], al
write_large_diamond_hat_L452:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L453
    mov byte ptr [edi + 536h], al
write_large_diamond_hat_L453:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L454
    mov byte ptr [edi + 537h], al
write_large_diamond_hat_L454:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L455
    mov byte ptr [edi + 7b8h], al
write_large_diamond_hat_L455:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L456
    mov byte ptr [edi + 7b9h], al
write_large_diamond_hat_L456:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L457
    mov byte ptr [edi + 500h], al
write_large_diamond_hat_L457:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L458
    mov byte ptr [edi + 501h], al
write_large_diamond_hat_L458:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L459
    mov byte ptr [edi + 282h], al
write_large_diamond_hat_L459:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L460
    mov byte ptr [edi + 283h], al
write_large_diamond_hat_L460:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L461
    mov byte ptr [edi + 4], al
write_large_diamond_hat_L461:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L462
    mov byte ptr [edi + 5], al
write_large_diamond_hat_L462:
    inc esi
    add esi, 2eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L463
    mov byte ptr [edi + 34h], al
write_large_diamond_hat_L463:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L464
    mov byte ptr [edi + 35h], al
write_large_diamond_hat_L464:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L465
    mov byte ptr [edi + 2b6h], al
write_large_diamond_hat_L465:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L466
    mov byte ptr [edi + 2b7h], al
write_large_diamond_hat_L466:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L467
    mov byte ptr [edi + 538h], al
write_large_diamond_hat_L467:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L468
    mov byte ptr [edi + 539h], al
write_large_diamond_hat_L468:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L469
    mov byte ptr [edi + 280h], al
write_large_diamond_hat_L469:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L470
    mov byte ptr [edi + 281h], al
write_large_diamond_hat_L470:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L471
    mov byte ptr [edi + 2], al
write_large_diamond_hat_L471:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L472
    mov byte ptr [edi + 3], al
write_large_diamond_hat_L472:
    inc esi
    add esi, 32h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L473
    mov byte ptr [edi + 36h], al
write_large_diamond_hat_L473:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L474
    mov byte ptr [edi + 37h], al
write_large_diamond_hat_L474:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L475
    mov byte ptr [edi + 2b8h], al
write_large_diamond_hat_L475:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L476
    mov byte ptr [edi + 2b9h], al
write_large_diamond_hat_L476:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_large_diamond_hat_L481
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L477
    mov byte ptr [edi], al
write_large_diamond_hat_L477:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L478
    mov byte ptr [edi + 1], al
write_large_diamond_hat_L478:
    inc esi
    add esi, 36h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L479
    mov byte ptr [edi + 38h], al
write_large_diamond_hat_L479:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_hat_L480
    mov byte ptr [edi + 39h], al
write_large_diamond_hat_L480:
    inc esi
write_large_diamond_hat_L481:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_large_diamond_lefthat
; ════════════════════════════════════════════════════════════
write_large_diamond_lefthat_:
    pushad
    mov esi, eax
    mov ebx, edx
    mov ecx, 0
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
write_large_diamond_lefthat_L1:
    cmp ebx, ecx
    jle near ptr write_large_diamond_lefthat_L30
    sub edi, dword ptr [_screen_width]
    push edi
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L2
    mov byte ptr [edi + 280h], al
write_large_diamond_lefthat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L3
    mov byte ptr [edi + 281h], al
write_large_diamond_lefthat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L4
    mov byte ptr [edi + 500h], al
write_large_diamond_lefthat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L5
    mov byte ptr [edi + 501h], al
write_large_diamond_lefthat_L5:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L6
    mov byte ptr [edi + 780h], al
write_large_diamond_lefthat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L7
    mov byte ptr [edi + 781h], al
write_large_diamond_lefthat_L7:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L8
    mov byte ptr [edi + 0a00h], al
write_large_diamond_lefthat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L9
    mov byte ptr [edi + 0a01h], al
write_large_diamond_lefthat_L9:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L10
    mov byte ptr [edi + 0c80h], al
write_large_diamond_lefthat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L11
    mov byte ptr [edi + 0c81h], al
write_large_diamond_lefthat_L11:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L12
    mov byte ptr [edi + 0f00h], al
write_large_diamond_lefthat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L13
    mov byte ptr [edi + 0f01h], al
write_large_diamond_lefthat_L13:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L14
    mov byte ptr [edi + 1180h], al
write_large_diamond_lefthat_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L15
    mov byte ptr [edi + 1181h], al
write_large_diamond_lefthat_L15:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L16
    mov byte ptr [edi + 1400h], al
write_large_diamond_lefthat_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L17
    mov byte ptr [edi + 1401h], al
write_large_diamond_lefthat_L17:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L18
    mov byte ptr [edi + 1680h], al
write_large_diamond_lefthat_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L19
    mov byte ptr [edi + 1681h], al
write_large_diamond_lefthat_L19:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L20
    mov byte ptr [edi + 1900h], al
write_large_diamond_lefthat_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L21
    mov byte ptr [edi + 1901h], al
write_large_diamond_lefthat_L21:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L22
    mov byte ptr [edi + 1b80h], al
write_large_diamond_lefthat_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L23
    mov byte ptr [edi + 1b81h], al
write_large_diamond_lefthat_L23:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L24
    mov byte ptr [edi + 1e00h], al
write_large_diamond_lefthat_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L25
    mov byte ptr [edi + 1e01h], al
write_large_diamond_lefthat_L25:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L26
    mov byte ptr [edi + 2080h], al
write_large_diamond_lefthat_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L27
    mov byte ptr [edi + 2081h], al
write_large_diamond_lefthat_L27:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L28
    mov byte ptr [edi + 2300h], al
write_large_diamond_lefthat_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L29
    mov byte ptr [edi + 2301h], al
write_large_diamond_lefthat_L29:
    inc esi
    add edi, 2
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_large_diamond_lefthat_L1
    popad
    ret
write_large_diamond_lefthat_L30:
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L31
    mov byte ptr [edi], al
write_large_diamond_lefthat_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L32
    mov byte ptr [edi + 1], al
write_large_diamond_lefthat_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L33
    mov byte ptr [edi + 282h], al
write_large_diamond_lefthat_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L34
    mov byte ptr [edi + 283h], al
write_large_diamond_lefthat_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L35
    mov byte ptr [edi + 504h], al
write_large_diamond_lefthat_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L36
    mov byte ptr [edi + 505h], al
write_large_diamond_lefthat_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L37
    mov byte ptr [edi + 786h], al
write_large_diamond_lefthat_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L38
    mov byte ptr [edi + 787h], al
write_large_diamond_lefthat_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L39
    mov byte ptr [edi + 0a08h], al
write_large_diamond_lefthat_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L40
    mov byte ptr [edi + 0a09h], al
write_large_diamond_lefthat_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L41
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_lefthat_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L42
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_lefthat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L43
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_lefthat_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L44
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_lefthat_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L45
    mov byte ptr [edi + 118eh], al
write_large_diamond_lefthat_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L46
    mov byte ptr [edi + 118fh], al
write_large_diamond_lefthat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L47
    mov byte ptr [edi + 1410h], al
write_large_diamond_lefthat_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L48
    mov byte ptr [edi + 1411h], al
write_large_diamond_lefthat_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L49
    mov byte ptr [edi + 1692h], al
write_large_diamond_lefthat_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L50
    mov byte ptr [edi + 1693h], al
write_large_diamond_lefthat_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L51
    mov byte ptr [edi + 1914h], al
write_large_diamond_lefthat_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L52
    mov byte ptr [edi + 1915h], al
write_large_diamond_lefthat_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L53
    mov byte ptr [edi + 1b96h], al
write_large_diamond_lefthat_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L54
    mov byte ptr [edi + 1b97h], al
write_large_diamond_lefthat_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L55
    mov byte ptr [edi + 1e18h], al
write_large_diamond_lefthat_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L56
    mov byte ptr [edi + 1e19h], al
write_large_diamond_lefthat_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L57
    mov byte ptr [edi + 209ah], al
write_large_diamond_lefthat_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L58
    mov byte ptr [edi + 209bh], al
write_large_diamond_lefthat_L58:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 20h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L59
    mov byte ptr [edi + 2], al
write_large_diamond_lefthat_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L60
    mov byte ptr [edi + 3], al
write_large_diamond_lefthat_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L61
    mov byte ptr [edi + 284h], al
write_large_diamond_lefthat_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L62
    mov byte ptr [edi + 285h], al
write_large_diamond_lefthat_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L63
    mov byte ptr [edi + 506h], al
write_large_diamond_lefthat_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L64
    mov byte ptr [edi + 507h], al
write_large_diamond_lefthat_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L65
    mov byte ptr [edi + 788h], al
write_large_diamond_lefthat_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L66
    mov byte ptr [edi + 789h], al
write_large_diamond_lefthat_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L67
    mov byte ptr [edi + 0a0ah], al
write_large_diamond_lefthat_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L68
    mov byte ptr [edi + 0a0bh], al
write_large_diamond_lefthat_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L69
    mov byte ptr [edi + 0c8ch], al
write_large_diamond_lefthat_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L70
    mov byte ptr [edi + 0c8dh], al
write_large_diamond_lefthat_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L71
    mov byte ptr [edi + 0f0eh], al
write_large_diamond_lefthat_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L72
    mov byte ptr [edi + 0f0fh], al
write_large_diamond_lefthat_L72:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L73
    mov byte ptr [edi + 1190h], al
write_large_diamond_lefthat_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L74
    mov byte ptr [edi + 1191h], al
write_large_diamond_lefthat_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L75
    mov byte ptr [edi + 1412h], al
write_large_diamond_lefthat_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L76
    mov byte ptr [edi + 1413h], al
write_large_diamond_lefthat_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L77
    mov byte ptr [edi + 1694h], al
write_large_diamond_lefthat_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L78
    mov byte ptr [edi + 1695h], al
write_large_diamond_lefthat_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L79
    mov byte ptr [edi + 1916h], al
write_large_diamond_lefthat_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L80
    mov byte ptr [edi + 1917h], al
write_large_diamond_lefthat_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L81
    mov byte ptr [edi + 1b98h], al
write_large_diamond_lefthat_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L82
    mov byte ptr [edi + 1b99h], al
write_large_diamond_lefthat_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L83
    mov byte ptr [edi + 1e1ah], al
write_large_diamond_lefthat_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L84
    mov byte ptr [edi + 1e1bh], al
write_large_diamond_lefthat_L84:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 22h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L85
    mov byte ptr [edi + 4], al
write_large_diamond_lefthat_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L86
    mov byte ptr [edi + 5], al
write_large_diamond_lefthat_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L87
    mov byte ptr [edi + 286h], al
write_large_diamond_lefthat_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L88
    mov byte ptr [edi + 287h], al
write_large_diamond_lefthat_L88:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L89
    mov byte ptr [edi + 508h], al
write_large_diamond_lefthat_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L90
    mov byte ptr [edi + 509h], al
write_large_diamond_lefthat_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L91
    mov byte ptr [edi + 78ah], al
write_large_diamond_lefthat_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L92
    mov byte ptr [edi + 78bh], al
write_large_diamond_lefthat_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L93
    mov byte ptr [edi + 0a0ch], al
write_large_diamond_lefthat_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L94
    mov byte ptr [edi + 0a0dh], al
write_large_diamond_lefthat_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L95
    mov byte ptr [edi + 0c8eh], al
write_large_diamond_lefthat_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L96
    mov byte ptr [edi + 0c8fh], al
write_large_diamond_lefthat_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L97
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthat_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L98
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthat_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L99
    mov byte ptr [edi + 1192h], al
write_large_diamond_lefthat_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L100
    mov byte ptr [edi + 1193h], al
write_large_diamond_lefthat_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L101
    mov byte ptr [edi + 1414h], al
write_large_diamond_lefthat_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L102
    mov byte ptr [edi + 1415h], al
write_large_diamond_lefthat_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L103
    mov byte ptr [edi + 1696h], al
write_large_diamond_lefthat_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L104
    mov byte ptr [edi + 1697h], al
write_large_diamond_lefthat_L104:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L105
    mov byte ptr [edi + 1918h], al
write_large_diamond_lefthat_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L106
    mov byte ptr [edi + 1919h], al
write_large_diamond_lefthat_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L107
    mov byte ptr [edi + 1b9ah], al
write_large_diamond_lefthat_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L108
    mov byte ptr [edi + 1b9bh], al
write_large_diamond_lefthat_L108:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 24h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L109
    mov byte ptr [edi + 6], al
write_large_diamond_lefthat_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L110
    mov byte ptr [edi + 7], al
write_large_diamond_lefthat_L110:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L111
    mov byte ptr [edi + 288h], al
write_large_diamond_lefthat_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L112
    mov byte ptr [edi + 289h], al
write_large_diamond_lefthat_L112:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L113
    mov byte ptr [edi + 50ah], al
write_large_diamond_lefthat_L113:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L114
    mov byte ptr [edi + 50bh], al
write_large_diamond_lefthat_L114:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L115
    mov byte ptr [edi + 78ch], al
write_large_diamond_lefthat_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L116
    mov byte ptr [edi + 78dh], al
write_large_diamond_lefthat_L116:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L117
    mov byte ptr [edi + 0a0eh], al
write_large_diamond_lefthat_L117:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L118
    mov byte ptr [edi + 0a0fh], al
write_large_diamond_lefthat_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L119
    mov byte ptr [edi + 0c90h], al
write_large_diamond_lefthat_L119:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L120
    mov byte ptr [edi + 0c91h], al
write_large_diamond_lefthat_L120:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L121
    mov byte ptr [edi + 0f12h], al
write_large_diamond_lefthat_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L122
    mov byte ptr [edi + 0f13h], al
write_large_diamond_lefthat_L122:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L123
    mov byte ptr [edi + 1194h], al
write_large_diamond_lefthat_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L124
    mov byte ptr [edi + 1195h], al
write_large_diamond_lefthat_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L125
    mov byte ptr [edi + 1416h], al
write_large_diamond_lefthat_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L126
    mov byte ptr [edi + 1417h], al
write_large_diamond_lefthat_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L127
    mov byte ptr [edi + 1698h], al
write_large_diamond_lefthat_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L128
    mov byte ptr [edi + 1699h], al
write_large_diamond_lefthat_L128:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L129
    mov byte ptr [edi + 191ah], al
write_large_diamond_lefthat_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L130
    mov byte ptr [edi + 191bh], al
write_large_diamond_lefthat_L130:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 26h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L131
    mov byte ptr [edi + 8], al
write_large_diamond_lefthat_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L132
    mov byte ptr [edi + 9], al
write_large_diamond_lefthat_L132:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L133
    mov byte ptr [edi + 28ah], al
write_large_diamond_lefthat_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L134
    mov byte ptr [edi + 28bh], al
write_large_diamond_lefthat_L134:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L135
    mov byte ptr [edi + 50ch], al
write_large_diamond_lefthat_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L136
    mov byte ptr [edi + 50dh], al
write_large_diamond_lefthat_L136:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L137
    mov byte ptr [edi + 78eh], al
write_large_diamond_lefthat_L137:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L138
    mov byte ptr [edi + 78fh], al
write_large_diamond_lefthat_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L139
    mov byte ptr [edi + 0a10h], al
write_large_diamond_lefthat_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L140
    mov byte ptr [edi + 0a11h], al
write_large_diamond_lefthat_L140:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L141
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthat_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L142
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthat_L142:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L143
    mov byte ptr [edi + 0f14h], al
write_large_diamond_lefthat_L143:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L144
    mov byte ptr [edi + 0f15h], al
write_large_diamond_lefthat_L144:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L145
    mov byte ptr [edi + 1196h], al
write_large_diamond_lefthat_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L146
    mov byte ptr [edi + 1197h], al
write_large_diamond_lefthat_L146:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L147
    mov byte ptr [edi + 1418h], al
write_large_diamond_lefthat_L147:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L148
    mov byte ptr [edi + 1419h], al
write_large_diamond_lefthat_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L149
    mov byte ptr [edi + 169ah], al
write_large_diamond_lefthat_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L150
    mov byte ptr [edi + 169bh], al
write_large_diamond_lefthat_L150:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 28h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L151
    mov byte ptr [edi + 0ah], al
write_large_diamond_lefthat_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L152
    mov byte ptr [edi + 0bh], al
write_large_diamond_lefthat_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L153
    mov byte ptr [edi + 28ch], al
write_large_diamond_lefthat_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L154
    mov byte ptr [edi + 28dh], al
write_large_diamond_lefthat_L154:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L155
    mov byte ptr [edi + 50eh], al
write_large_diamond_lefthat_L155:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L156
    mov byte ptr [edi + 50fh], al
write_large_diamond_lefthat_L156:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L157
    mov byte ptr [edi + 790h], al
write_large_diamond_lefthat_L157:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L158
    mov byte ptr [edi + 791h], al
write_large_diamond_lefthat_L158:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L159
    mov byte ptr [edi + 0a12h], al
write_large_diamond_lefthat_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L160
    mov byte ptr [edi + 0a13h], al
write_large_diamond_lefthat_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L161
    mov byte ptr [edi + 0c94h], al
write_large_diamond_lefthat_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L162
    mov byte ptr [edi + 0c95h], al
write_large_diamond_lefthat_L162:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L163
    mov byte ptr [edi + 0f16h], al
write_large_diamond_lefthat_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L164
    mov byte ptr [edi + 0f17h], al
write_large_diamond_lefthat_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L165
    mov byte ptr [edi + 1198h], al
write_large_diamond_lefthat_L165:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L166
    mov byte ptr [edi + 1199h], al
write_large_diamond_lefthat_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L167
    mov byte ptr [edi + 141ah], al
write_large_diamond_lefthat_L167:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L168
    mov byte ptr [edi + 141bh], al
write_large_diamond_lefthat_L168:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 2ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L169
    mov byte ptr [edi + 0ch], al
write_large_diamond_lefthat_L169:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L170
    mov byte ptr [edi + 0dh], al
write_large_diamond_lefthat_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L171
    mov byte ptr [edi + 28eh], al
write_large_diamond_lefthat_L171:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L172
    mov byte ptr [edi + 28fh], al
write_large_diamond_lefthat_L172:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L173
    mov byte ptr [edi + 510h], al
write_large_diamond_lefthat_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L174
    mov byte ptr [edi + 511h], al
write_large_diamond_lefthat_L174:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L175
    mov byte ptr [edi + 792h], al
write_large_diamond_lefthat_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L176
    mov byte ptr [edi + 793h], al
write_large_diamond_lefthat_L176:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L177
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthat_L177:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L178
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthat_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L179
    mov byte ptr [edi + 0c96h], al
write_large_diamond_lefthat_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L180
    mov byte ptr [edi + 0c97h], al
write_large_diamond_lefthat_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L181
    mov byte ptr [edi + 0f18h], al
write_large_diamond_lefthat_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L182
    mov byte ptr [edi + 0f19h], al
write_large_diamond_lefthat_L182:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L183
    mov byte ptr [edi + 119ah], al
write_large_diamond_lefthat_L183:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L184
    mov byte ptr [edi + 119bh], al
write_large_diamond_lefthat_L184:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 2ch
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L185
    mov byte ptr [edi + 0eh], al
write_large_diamond_lefthat_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L186
    mov byte ptr [edi + 0fh], al
write_large_diamond_lefthat_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L187
    mov byte ptr [edi + 290h], al
write_large_diamond_lefthat_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L188
    mov byte ptr [edi + 291h], al
write_large_diamond_lefthat_L188:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L189
    mov byte ptr [edi + 512h], al
write_large_diamond_lefthat_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L190
    mov byte ptr [edi + 513h], al
write_large_diamond_lefthat_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L191
    mov byte ptr [edi + 794h], al
write_large_diamond_lefthat_L191:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L192
    mov byte ptr [edi + 795h], al
write_large_diamond_lefthat_L192:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L193
    mov byte ptr [edi + 0a16h], al
write_large_diamond_lefthat_L193:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L194
    mov byte ptr [edi + 0a17h], al
write_large_diamond_lefthat_L194:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L195
    mov byte ptr [edi + 0c98h], al
write_large_diamond_lefthat_L195:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L196
    mov byte ptr [edi + 0c99h], al
write_large_diamond_lefthat_L196:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L197
    mov byte ptr [edi + 0f1ah], al
write_large_diamond_lefthat_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L198
    mov byte ptr [edi + 0f1bh], al
write_large_diamond_lefthat_L198:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 2eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L199
    mov byte ptr [edi + 10h], al
write_large_diamond_lefthat_L199:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L200
    mov byte ptr [edi + 11h], al
write_large_diamond_lefthat_L200:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L201
    mov byte ptr [edi + 292h], al
write_large_diamond_lefthat_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L202
    mov byte ptr [edi + 293h], al
write_large_diamond_lefthat_L202:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L203
    mov byte ptr [edi + 514h], al
write_large_diamond_lefthat_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L204
    mov byte ptr [edi + 515h], al
write_large_diamond_lefthat_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L205
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthat_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L206
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthat_L206:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L207
    mov byte ptr [edi + 0a18h], al
write_large_diamond_lefthat_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L208
    mov byte ptr [edi + 0a19h], al
write_large_diamond_lefthat_L208:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L209
    mov byte ptr [edi + 0c9ah], al
write_large_diamond_lefthat_L209:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L210
    mov byte ptr [edi + 0c9bh], al
write_large_diamond_lefthat_L210:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 30h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L211
    mov byte ptr [edi + 12h], al
write_large_diamond_lefthat_L211:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L212
    mov byte ptr [edi + 13h], al
write_large_diamond_lefthat_L212:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L213
    mov byte ptr [edi + 294h], al
write_large_diamond_lefthat_L213:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L214
    mov byte ptr [edi + 295h], al
write_large_diamond_lefthat_L214:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L215
    mov byte ptr [edi + 516h], al
write_large_diamond_lefthat_L215:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L216
    mov byte ptr [edi + 517h], al
write_large_diamond_lefthat_L216:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L217
    mov byte ptr [edi + 798h], al
write_large_diamond_lefthat_L217:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L218
    mov byte ptr [edi + 799h], al
write_large_diamond_lefthat_L218:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L219
    mov byte ptr [edi + 0a1ah], al
write_large_diamond_lefthat_L219:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L220
    mov byte ptr [edi + 0a1bh], al
write_large_diamond_lefthat_L220:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 32h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L221
    mov byte ptr [edi + 14h], al
write_large_diamond_lefthat_L221:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L222
    mov byte ptr [edi + 15h], al
write_large_diamond_lefthat_L222:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L223
    mov byte ptr [edi + 296h], al
write_large_diamond_lefthat_L223:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L224
    mov byte ptr [edi + 297h], al
write_large_diamond_lefthat_L224:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L225
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthat_L225:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L226
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthat_L226:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L227
    mov byte ptr [edi + 79ah], al
write_large_diamond_lefthat_L227:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L228
    mov byte ptr [edi + 79bh], al
write_large_diamond_lefthat_L228:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthat_L241
    add esi, 34h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L229
    mov byte ptr [edi + 16h], al
write_large_diamond_lefthat_L229:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L230
    mov byte ptr [edi + 17h], al
write_large_diamond_lefthat_L230:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L231
    mov byte ptr [edi + 298h], al
write_large_diamond_lefthat_L231:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L232
    mov byte ptr [edi + 299h], al
write_large_diamond_lefthat_L232:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L233
    mov byte ptr [edi + 51ah], al
write_large_diamond_lefthat_L233:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L234
    mov byte ptr [edi + 51bh], al
write_large_diamond_lefthat_L234:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_large_diamond_lefthat_L241
    add esi, 36h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L235
    mov byte ptr [edi + 18h], al
write_large_diamond_lefthat_L235:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L236
    mov byte ptr [edi + 19h], al
write_large_diamond_lefthat_L236:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L237
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthat_L237:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L238
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthat_L238:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_large_diamond_lefthat_L241
    add esi, 38h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L239
    mov byte ptr [edi + 1ah], al
write_large_diamond_lefthat_L239:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthat_L240
    mov byte ptr [edi + 1bh], al
write_large_diamond_lefthat_L240:
    inc esi
write_large_diamond_lefthat_L241:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_large_diamond_righthat
; ════════════════════════════════════════════════════════════
write_large_diamond_righthat_:
    pushad
    mov esi, eax
    mov ebx, edx
    mov ecx, 0
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
write_large_diamond_righthat_L1:
    cmp ebx, ecx
    jle near ptr write_large_diamond_righthat_L30
    sub edi, dword ptr [_screen_width]
    push edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L2
    mov byte ptr [edi + 2300h], al
write_large_diamond_righthat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L3
    mov byte ptr [edi + 2301h], al
write_large_diamond_righthat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L4
    mov byte ptr [edi + 2080h], al
write_large_diamond_righthat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L5
    mov byte ptr [edi + 2081h], al
write_large_diamond_righthat_L5:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L6
    mov byte ptr [edi + 1e00h], al
write_large_diamond_righthat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L7
    mov byte ptr [edi + 1e01h], al
write_large_diamond_righthat_L7:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L8
    mov byte ptr [edi + 1b80h], al
write_large_diamond_righthat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L9
    mov byte ptr [edi + 1b81h], al
write_large_diamond_righthat_L9:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L10
    mov byte ptr [edi + 1900h], al
write_large_diamond_righthat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L11
    mov byte ptr [edi + 1901h], al
write_large_diamond_righthat_L11:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L12
    mov byte ptr [edi + 1680h], al
write_large_diamond_righthat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L13
    mov byte ptr [edi + 1681h], al
write_large_diamond_righthat_L13:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L14
    mov byte ptr [edi + 1400h], al
write_large_diamond_righthat_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L15
    mov byte ptr [edi + 1401h], al
write_large_diamond_righthat_L15:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L16
    mov byte ptr [edi + 1180h], al
write_large_diamond_righthat_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L17
    mov byte ptr [edi + 1181h], al
write_large_diamond_righthat_L17:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L18
    mov byte ptr [edi + 0f00h], al
write_large_diamond_righthat_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L19
    mov byte ptr [edi + 0f01h], al
write_large_diamond_righthat_L19:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L20
    mov byte ptr [edi + 0c80h], al
write_large_diamond_righthat_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L21
    mov byte ptr [edi + 0c81h], al
write_large_diamond_righthat_L21:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L22
    mov byte ptr [edi + 0a00h], al
write_large_diamond_righthat_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L23
    mov byte ptr [edi + 0a01h], al
write_large_diamond_righthat_L23:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L24
    mov byte ptr [edi + 780h], al
write_large_diamond_righthat_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L25
    mov byte ptr [edi + 781h], al
write_large_diamond_righthat_L25:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L26
    mov byte ptr [edi + 500h], al
write_large_diamond_righthat_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L27
    mov byte ptr [edi + 501h], al
write_large_diamond_righthat_L27:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L28
    mov byte ptr [edi + 280h], al
write_large_diamond_righthat_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L29
    mov byte ptr [edi + 281h], al
write_large_diamond_righthat_L29:
    inc esi
    add edi, 2
    add esi, 1eh
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_large_diamond_righthat_L1
    popad
    ret
write_large_diamond_righthat_L30:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L31
    mov byte ptr [edi + 2080h], al
write_large_diamond_righthat_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L32
    mov byte ptr [edi + 2081h], al
write_large_diamond_righthat_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L33
    mov byte ptr [edi + 1e02h], al
write_large_diamond_righthat_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L34
    mov byte ptr [edi + 1e03h], al
write_large_diamond_righthat_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L35
    mov byte ptr [edi + 1b84h], al
write_large_diamond_righthat_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L36
    mov byte ptr [edi + 1b85h], al
write_large_diamond_righthat_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L37
    mov byte ptr [edi + 1906h], al
write_large_diamond_righthat_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L38
    mov byte ptr [edi + 1907h], al
write_large_diamond_righthat_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L39
    mov byte ptr [edi + 1688h], al
write_large_diamond_righthat_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L40
    mov byte ptr [edi + 1689h], al
write_large_diamond_righthat_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L41
    mov byte ptr [edi + 140ah], al
write_large_diamond_righthat_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L42
    mov byte ptr [edi + 140bh], al
write_large_diamond_righthat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L43
    mov byte ptr [edi + 118ch], al
write_large_diamond_righthat_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L44
    mov byte ptr [edi + 118dh], al
write_large_diamond_righthat_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L45
    mov byte ptr [edi + 0f0eh], al
write_large_diamond_righthat_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L46
    mov byte ptr [edi + 0f0fh], al
write_large_diamond_righthat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L47
    mov byte ptr [edi + 0c90h], al
write_large_diamond_righthat_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L48
    mov byte ptr [edi + 0c91h], al
write_large_diamond_righthat_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L49
    mov byte ptr [edi + 0a12h], al
write_large_diamond_righthat_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L50
    mov byte ptr [edi + 0a13h], al
write_large_diamond_righthat_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L51
    mov byte ptr [edi + 794h], al
write_large_diamond_righthat_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L52
    mov byte ptr [edi + 795h], al
write_large_diamond_righthat_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L53
    mov byte ptr [edi + 516h], al
write_large_diamond_righthat_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L54
    mov byte ptr [edi + 517h], al
write_large_diamond_righthat_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L55
    mov byte ptr [edi + 298h], al
write_large_diamond_righthat_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L56
    mov byte ptr [edi + 299h], al
write_large_diamond_righthat_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L57
    mov byte ptr [edi + 1ah], al
write_large_diamond_righthat_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L58
    mov byte ptr [edi + 1bh], al
write_large_diamond_righthat_L58:
    inc esi
    add esi, 1eh
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L59
    mov byte ptr [edi + 1e00h], al
write_large_diamond_righthat_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L60
    mov byte ptr [edi + 1e01h], al
write_large_diamond_righthat_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L61
    mov byte ptr [edi + 1b82h], al
write_large_diamond_righthat_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L62
    mov byte ptr [edi + 1b83h], al
write_large_diamond_righthat_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L63
    mov byte ptr [edi + 1904h], al
write_large_diamond_righthat_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L64
    mov byte ptr [edi + 1905h], al
write_large_diamond_righthat_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L65
    mov byte ptr [edi + 1686h], al
write_large_diamond_righthat_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L66
    mov byte ptr [edi + 1687h], al
write_large_diamond_righthat_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L67
    mov byte ptr [edi + 1408h], al
write_large_diamond_righthat_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L68
    mov byte ptr [edi + 1409h], al
write_large_diamond_righthat_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L69
    mov byte ptr [edi + 118ah], al
write_large_diamond_righthat_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L70
    mov byte ptr [edi + 118bh], al
write_large_diamond_righthat_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L71
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthat_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L72
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthat_L72:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L73
    mov byte ptr [edi + 0c8eh], al
write_large_diamond_righthat_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L74
    mov byte ptr [edi + 0c8fh], al
write_large_diamond_righthat_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L75
    mov byte ptr [edi + 0a10h], al
write_large_diamond_righthat_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L76
    mov byte ptr [edi + 0a11h], al
write_large_diamond_righthat_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L77
    mov byte ptr [edi + 792h], al
write_large_diamond_righthat_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L78
    mov byte ptr [edi + 793h], al
write_large_diamond_righthat_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L79
    mov byte ptr [edi + 514h], al
write_large_diamond_righthat_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L80
    mov byte ptr [edi + 515h], al
write_large_diamond_righthat_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L81
    mov byte ptr [edi + 296h], al
write_large_diamond_righthat_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L82
    mov byte ptr [edi + 297h], al
write_large_diamond_righthat_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L83
    mov byte ptr [edi + 18h], al
write_large_diamond_righthat_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L84
    mov byte ptr [edi + 19h], al
write_large_diamond_righthat_L84:
    inc esi
    add esi, 20h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L85
    mov byte ptr [edi + 1b80h], al
write_large_diamond_righthat_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L86
    mov byte ptr [edi + 1b81h], al
write_large_diamond_righthat_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L87
    mov byte ptr [edi + 1902h], al
write_large_diamond_righthat_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L88
    mov byte ptr [edi + 1903h], al
write_large_diamond_righthat_L88:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L89
    mov byte ptr [edi + 1684h], al
write_large_diamond_righthat_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L90
    mov byte ptr [edi + 1685h], al
write_large_diamond_righthat_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L91
    mov byte ptr [edi + 1406h], al
write_large_diamond_righthat_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L92
    mov byte ptr [edi + 1407h], al
write_large_diamond_righthat_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L93
    mov byte ptr [edi + 1188h], al
write_large_diamond_righthat_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L94
    mov byte ptr [edi + 1189h], al
write_large_diamond_righthat_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L95
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_righthat_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L96
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_righthat_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L97
    mov byte ptr [edi + 0c8ch], al
write_large_diamond_righthat_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L98
    mov byte ptr [edi + 0c8dh], al
write_large_diamond_righthat_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L99
    mov byte ptr [edi + 0a0eh], al
write_large_diamond_righthat_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L100
    mov byte ptr [edi + 0a0fh], al
write_large_diamond_righthat_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L101
    mov byte ptr [edi + 790h], al
write_large_diamond_righthat_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L102
    mov byte ptr [edi + 791h], al
write_large_diamond_righthat_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L103
    mov byte ptr [edi + 512h], al
write_large_diamond_righthat_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L104
    mov byte ptr [edi + 513h], al
write_large_diamond_righthat_L104:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L105
    mov byte ptr [edi + 294h], al
write_large_diamond_righthat_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L106
    mov byte ptr [edi + 295h], al
write_large_diamond_righthat_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L107
    mov byte ptr [edi + 16h], al
write_large_diamond_righthat_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L108
    mov byte ptr [edi + 17h], al
write_large_diamond_righthat_L108:
    inc esi
    add esi, 22h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L109
    mov byte ptr [edi + 1900h], al
write_large_diamond_righthat_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L110
    mov byte ptr [edi + 1901h], al
write_large_diamond_righthat_L110:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L111
    mov byte ptr [edi + 1682h], al
write_large_diamond_righthat_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L112
    mov byte ptr [edi + 1683h], al
write_large_diamond_righthat_L112:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L113
    mov byte ptr [edi + 1404h], al
write_large_diamond_righthat_L113:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L114
    mov byte ptr [edi + 1405h], al
write_large_diamond_righthat_L114:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L115
    mov byte ptr [edi + 1186h], al
write_large_diamond_righthat_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L116
    mov byte ptr [edi + 1187h], al
write_large_diamond_righthat_L116:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L117
    mov byte ptr [edi + 0f08h], al
write_large_diamond_righthat_L117:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L118
    mov byte ptr [edi + 0f09h], al
write_large_diamond_righthat_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L119
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthat_L119:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L120
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthat_L120:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L121
    mov byte ptr [edi + 0a0ch], al
write_large_diamond_righthat_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L122
    mov byte ptr [edi + 0a0dh], al
write_large_diamond_righthat_L122:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L123
    mov byte ptr [edi + 78eh], al
write_large_diamond_righthat_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L124
    mov byte ptr [edi + 78fh], al
write_large_diamond_righthat_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L125
    mov byte ptr [edi + 510h], al
write_large_diamond_righthat_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L126
    mov byte ptr [edi + 511h], al
write_large_diamond_righthat_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L127
    mov byte ptr [edi + 292h], al
write_large_diamond_righthat_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L128
    mov byte ptr [edi + 293h], al
write_large_diamond_righthat_L128:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L129
    mov byte ptr [edi + 14h], al
write_large_diamond_righthat_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L130
    mov byte ptr [edi + 15h], al
write_large_diamond_righthat_L130:
    inc esi
    add esi, 24h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L131
    mov byte ptr [edi + 1680h], al
write_large_diamond_righthat_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L132
    mov byte ptr [edi + 1681h], al
write_large_diamond_righthat_L132:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L133
    mov byte ptr [edi + 1402h], al
write_large_diamond_righthat_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L134
    mov byte ptr [edi + 1403h], al
write_large_diamond_righthat_L134:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L135
    mov byte ptr [edi + 1184h], al
write_large_diamond_righthat_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L136
    mov byte ptr [edi + 1185h], al
write_large_diamond_righthat_L136:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L137
    mov byte ptr [edi + 0f06h], al
write_large_diamond_righthat_L137:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L138
    mov byte ptr [edi + 0f07h], al
write_large_diamond_righthat_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L139
    mov byte ptr [edi + 0c88h], al
write_large_diamond_righthat_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L140
    mov byte ptr [edi + 0c89h], al
write_large_diamond_righthat_L140:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L141
    mov byte ptr [edi + 0a0ah], al
write_large_diamond_righthat_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L142
    mov byte ptr [edi + 0a0bh], al
write_large_diamond_righthat_L142:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L143
    mov byte ptr [edi + 78ch], al
write_large_diamond_righthat_L143:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L144
    mov byte ptr [edi + 78dh], al
write_large_diamond_righthat_L144:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L145
    mov byte ptr [edi + 50eh], al
write_large_diamond_righthat_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L146
    mov byte ptr [edi + 50fh], al
write_large_diamond_righthat_L146:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L147
    mov byte ptr [edi + 290h], al
write_large_diamond_righthat_L147:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L148
    mov byte ptr [edi + 291h], al
write_large_diamond_righthat_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L149
    mov byte ptr [edi + 12h], al
write_large_diamond_righthat_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L150
    mov byte ptr [edi + 13h], al
write_large_diamond_righthat_L150:
    inc esi
    add esi, 26h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L151
    mov byte ptr [edi + 1400h], al
write_large_diamond_righthat_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L152
    mov byte ptr [edi + 1401h], al
write_large_diamond_righthat_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L153
    mov byte ptr [edi + 1182h], al
write_large_diamond_righthat_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L154
    mov byte ptr [edi + 1183h], al
write_large_diamond_righthat_L154:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L155
    mov byte ptr [edi + 0f04h], al
write_large_diamond_righthat_L155:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L156
    mov byte ptr [edi + 0f05h], al
write_large_diamond_righthat_L156:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L157
    mov byte ptr [edi + 0c86h], al
write_large_diamond_righthat_L157:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L158
    mov byte ptr [edi + 0c87h], al
write_large_diamond_righthat_L158:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L159
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthat_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L160
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthat_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L161
    mov byte ptr [edi + 78ah], al
write_large_diamond_righthat_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L162
    mov byte ptr [edi + 78bh], al
write_large_diamond_righthat_L162:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L163
    mov byte ptr [edi + 50ch], al
write_large_diamond_righthat_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L164
    mov byte ptr [edi + 50dh], al
write_large_diamond_righthat_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L165
    mov byte ptr [edi + 28eh], al
write_large_diamond_righthat_L165:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L166
    mov byte ptr [edi + 28fh], al
write_large_diamond_righthat_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L167
    mov byte ptr [edi + 10h], al
write_large_diamond_righthat_L167:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L168
    mov byte ptr [edi + 11h], al
write_large_diamond_righthat_L168:
    inc esi
    add esi, 28h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L169
    mov byte ptr [edi + 1180h], al
write_large_diamond_righthat_L169:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L170
    mov byte ptr [edi + 1181h], al
write_large_diamond_righthat_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L171
    mov byte ptr [edi + 0f02h], al
write_large_diamond_righthat_L171:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L172
    mov byte ptr [edi + 0f03h], al
write_large_diamond_righthat_L172:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L173
    mov byte ptr [edi + 0c84h], al
write_large_diamond_righthat_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L174
    mov byte ptr [edi + 0c85h], al
write_large_diamond_righthat_L174:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L175
    mov byte ptr [edi + 0a06h], al
write_large_diamond_righthat_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L176
    mov byte ptr [edi + 0a07h], al
write_large_diamond_righthat_L176:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L177
    mov byte ptr [edi + 788h], al
write_large_diamond_righthat_L177:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L178
    mov byte ptr [edi + 789h], al
write_large_diamond_righthat_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L179
    mov byte ptr [edi + 50ah], al
write_large_diamond_righthat_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L180
    mov byte ptr [edi + 50bh], al
write_large_diamond_righthat_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L181
    mov byte ptr [edi + 28ch], al
write_large_diamond_righthat_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L182
    mov byte ptr [edi + 28dh], al
write_large_diamond_righthat_L182:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L183
    mov byte ptr [edi + 0eh], al
write_large_diamond_righthat_L183:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L184
    mov byte ptr [edi + 0fh], al
write_large_diamond_righthat_L184:
    inc esi
    add esi, 2ah
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L185
    mov byte ptr [edi + 0f00h], al
write_large_diamond_righthat_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L186
    mov byte ptr [edi + 0f01h], al
write_large_diamond_righthat_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L187
    mov byte ptr [edi + 0c82h], al
write_large_diamond_righthat_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L188
    mov byte ptr [edi + 0c83h], al
write_large_diamond_righthat_L188:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L189
    mov byte ptr [edi + 0a04h], al
write_large_diamond_righthat_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L190
    mov byte ptr [edi + 0a05h], al
write_large_diamond_righthat_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L191
    mov byte ptr [edi + 786h], al
write_large_diamond_righthat_L191:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L192
    mov byte ptr [edi + 787h], al
write_large_diamond_righthat_L192:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L193
    mov byte ptr [edi + 508h], al
write_large_diamond_righthat_L193:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L194
    mov byte ptr [edi + 509h], al
write_large_diamond_righthat_L194:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L195
    mov byte ptr [edi + 28ah], al
write_large_diamond_righthat_L195:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L196
    mov byte ptr [edi + 28bh], al
write_large_diamond_righthat_L196:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L197
    mov byte ptr [edi + 0ch], al
write_large_diamond_righthat_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L198
    mov byte ptr [edi + 0dh], al
write_large_diamond_righthat_L198:
    inc esi
    add esi, 2ch
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L199
    mov byte ptr [edi + 0c80h], al
write_large_diamond_righthat_L199:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L200
    mov byte ptr [edi + 0c81h], al
write_large_diamond_righthat_L200:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L201
    mov byte ptr [edi + 0a02h], al
write_large_diamond_righthat_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L202
    mov byte ptr [edi + 0a03h], al
write_large_diamond_righthat_L202:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L203
    mov byte ptr [edi + 784h], al
write_large_diamond_righthat_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L204
    mov byte ptr [edi + 785h], al
write_large_diamond_righthat_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L205
    mov byte ptr [edi + 506h], al
write_large_diamond_righthat_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L206
    mov byte ptr [edi + 507h], al
write_large_diamond_righthat_L206:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L207
    mov byte ptr [edi + 288h], al
write_large_diamond_righthat_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L208
    mov byte ptr [edi + 289h], al
write_large_diamond_righthat_L208:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L209
    mov byte ptr [edi + 0ah], al
write_large_diamond_righthat_L209:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L210
    mov byte ptr [edi + 0bh], al
write_large_diamond_righthat_L210:
    inc esi
    add esi, 2eh
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L211
    mov byte ptr [edi + 0a00h], al
write_large_diamond_righthat_L211:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L212
    mov byte ptr [edi + 0a01h], al
write_large_diamond_righthat_L212:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L213
    mov byte ptr [edi + 782h], al
write_large_diamond_righthat_L213:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L214
    mov byte ptr [edi + 783h], al
write_large_diamond_righthat_L214:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L215
    mov byte ptr [edi + 504h], al
write_large_diamond_righthat_L215:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L216
    mov byte ptr [edi + 505h], al
write_large_diamond_righthat_L216:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L217
    mov byte ptr [edi + 286h], al
write_large_diamond_righthat_L217:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L218
    mov byte ptr [edi + 287h], al
write_large_diamond_righthat_L218:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L219
    mov byte ptr [edi + 8], al
write_large_diamond_righthat_L219:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L220
    mov byte ptr [edi + 9], al
write_large_diamond_righthat_L220:
    inc esi
    add esi, 30h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L221
    mov byte ptr [edi + 780h], al
write_large_diamond_righthat_L221:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L222
    mov byte ptr [edi + 781h], al
write_large_diamond_righthat_L222:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L223
    mov byte ptr [edi + 502h], al
write_large_diamond_righthat_L223:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L224
    mov byte ptr [edi + 503h], al
write_large_diamond_righthat_L224:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L225
    mov byte ptr [edi + 284h], al
write_large_diamond_righthat_L225:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L226
    mov byte ptr [edi + 285h], al
write_large_diamond_righthat_L226:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L227
    mov byte ptr [edi + 6], al
write_large_diamond_righthat_L227:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L228
    mov byte ptr [edi + 7], al
write_large_diamond_righthat_L228:
    inc esi
    add esi, 32h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L229
    mov byte ptr [edi + 500h], al
write_large_diamond_righthat_L229:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L230
    mov byte ptr [edi + 501h], al
write_large_diamond_righthat_L230:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L231
    mov byte ptr [edi + 282h], al
write_large_diamond_righthat_L231:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L232
    mov byte ptr [edi + 283h], al
write_large_diamond_righthat_L232:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L233
    mov byte ptr [edi + 4], al
write_large_diamond_righthat_L233:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L234
    mov byte ptr [edi + 5], al
write_large_diamond_righthat_L234:
    inc esi
    add esi, 34h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L235
    mov byte ptr [edi + 280h], al
write_large_diamond_righthat_L235:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L236
    mov byte ptr [edi + 281h], al
write_large_diamond_righthat_L236:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L237
    mov byte ptr [edi + 2], al
write_large_diamond_righthat_L237:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L238
    mov byte ptr [edi + 3], al
write_large_diamond_righthat_L238:
    inc esi
    add esi, 36h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_large_diamond_righthat_L241
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L239
    mov byte ptr [edi], al
write_large_diamond_righthat_L239:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthat_L240
    mov byte ptr [edi + 1], al
write_large_diamond_righthat_L240:
    inc esi
write_large_diamond_righthat_L241:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_large_diamond_lefthalfhat
; ════════════════════════════════════════════════════════════
write_large_diamond_lefthalfhat_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 2], ebx
    mov ebx, edx
    mov ecx, 0
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
write_large_diamond_lefthalfhat_L1:
    cmp ebx, ecx
    jle near ptr write_large_diamond_lefthalfhat_L33
    sub edi, dword ptr [_screen_width]
    push edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L2
    mov byte ptr [edi + 2300h], al
write_large_diamond_lefthalfhat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L3
    mov byte ptr [edi + 2301h], al
write_large_diamond_lefthalfhat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L4
    mov byte ptr [edi + 2080h], al
write_large_diamond_lefthalfhat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L5
    mov byte ptr [edi + 2081h], al
write_large_diamond_lefthalfhat_L5:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L6
    mov byte ptr [edi + 1e00h], al
write_large_diamond_lefthalfhat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L7
    mov byte ptr [edi + 1e01h], al
write_large_diamond_lefthalfhat_L7:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L8
    mov byte ptr [edi + 1b80h], al
write_large_diamond_lefthalfhat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L9
    mov byte ptr [edi + 1b81h], al
write_large_diamond_lefthalfhat_L9:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L10
    mov byte ptr [edi + 1900h], al
write_large_diamond_lefthalfhat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L11
    mov byte ptr [edi + 1901h], al
write_large_diamond_lefthalfhat_L11:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L12
    mov byte ptr [edi + 1680h], al
write_large_diamond_lefthalfhat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L13
    mov byte ptr [edi + 1681h], al
write_large_diamond_lefthalfhat_L13:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L14
    mov byte ptr [edi + 1400h], al
write_large_diamond_lefthalfhat_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L15
    mov byte ptr [edi + 1401h], al
write_large_diamond_lefthalfhat_L15:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L16
    mov byte ptr [edi + 1180h], al
write_large_diamond_lefthalfhat_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L17
    mov byte ptr [edi + 1181h], al
write_large_diamond_lefthalfhat_L17:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L18
    mov byte ptr [edi + 0f00h], al
write_large_diamond_lefthalfhat_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L19
    mov byte ptr [edi + 0f01h], al
write_large_diamond_lefthalfhat_L19:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L20
    mov byte ptr [edi + 0c80h], al
write_large_diamond_lefthalfhat_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L21
    mov byte ptr [edi + 0c81h], al
write_large_diamond_lefthalfhat_L21:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L22
    mov byte ptr [edi + 0a00h], al
write_large_diamond_lefthalfhat_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L23
    mov byte ptr [edi + 0a01h], al
write_large_diamond_lefthalfhat_L23:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L24
    mov byte ptr [edi + 780h], al
write_large_diamond_lefthalfhat_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L25
    mov byte ptr [edi + 781h], al
write_large_diamond_lefthalfhat_L25:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L26
    mov byte ptr [edi + 500h], al
write_large_diamond_lefthalfhat_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L27
    mov byte ptr [edi + 501h], al
write_large_diamond_lefthalfhat_L27:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L28
    mov byte ptr [edi + 280h], al
write_large_diamond_lefthalfhat_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L29
    mov byte ptr [edi + 281h], al
write_large_diamond_lefthalfhat_L29:
    inc esi
    add edi, 2
    add esi, 2
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L32
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L30
    mov byte ptr [edi], al
write_large_diamond_lefthalfhat_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L31
    mov byte ptr [edi + 1], al
write_large_diamond_lefthalfhat_L31:
    inc esi
    add edi, 2
write_large_diamond_lefthalfhat_L32:
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_large_diamond_lefthalfhat_L1
    popad
    ret
write_large_diamond_lefthalfhat_L33:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L34
    mov byte ptr [edi + 2080h], al
write_large_diamond_lefthalfhat_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L35
    mov byte ptr [edi + 2081h], al
write_large_diamond_lefthalfhat_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L36
    mov byte ptr [edi + 1e02h], al
write_large_diamond_lefthalfhat_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L37
    mov byte ptr [edi + 1e03h], al
write_large_diamond_lefthalfhat_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L38
    mov byte ptr [edi + 1b84h], al
write_large_diamond_lefthalfhat_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L39
    mov byte ptr [edi + 1b85h], al
write_large_diamond_lefthalfhat_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L40
    mov byte ptr [edi + 1906h], al
write_large_diamond_lefthalfhat_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L41
    mov byte ptr [edi + 1907h], al
write_large_diamond_lefthalfhat_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L42
    mov byte ptr [edi + 1688h], al
write_large_diamond_lefthalfhat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L43
    mov byte ptr [edi + 1689h], al
write_large_diamond_lefthalfhat_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L44
    mov byte ptr [edi + 140ah], al
write_large_diamond_lefthalfhat_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L45
    mov byte ptr [edi + 140bh], al
write_large_diamond_lefthalfhat_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L46
    mov byte ptr [edi + 118ch], al
write_large_diamond_lefthalfhat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L47
    mov byte ptr [edi + 118dh], al
write_large_diamond_lefthalfhat_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L48
    mov byte ptr [edi + 0f0eh], al
write_large_diamond_lefthalfhat_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L49
    mov byte ptr [edi + 0f0fh], al
write_large_diamond_lefthalfhat_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L50
    mov byte ptr [edi + 0c90h], al
write_large_diamond_lefthalfhat_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L51
    mov byte ptr [edi + 0c91h], al
write_large_diamond_lefthalfhat_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L52
    mov byte ptr [edi + 0a12h], al
write_large_diamond_lefthalfhat_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L53
    mov byte ptr [edi + 0a13h], al
write_large_diamond_lefthalfhat_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L54
    mov byte ptr [edi + 794h], al
write_large_diamond_lefthalfhat_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L55
    mov byte ptr [edi + 795h], al
write_large_diamond_lefthalfhat_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L56
    mov byte ptr [edi + 516h], al
write_large_diamond_lefthalfhat_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L57
    mov byte ptr [edi + 517h], al
write_large_diamond_lefthalfhat_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L58
    mov byte ptr [edi + 298h], al
write_large_diamond_lefthalfhat_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L59
    mov byte ptr [edi + 299h], al
write_large_diamond_lefthalfhat_L59:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L62
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L60
    mov byte ptr [edi + 1ah], al
write_large_diamond_lefthalfhat_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L61
    mov byte ptr [edi + 1bh], al
write_large_diamond_lefthalfhat_L61:
    inc esi
write_large_diamond_lefthalfhat_L62:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 2
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L63
    mov byte ptr [edi + 1e00h], al
write_large_diamond_lefthalfhat_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L64
    mov byte ptr [edi + 1e01h], al
write_large_diamond_lefthalfhat_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L65
    mov byte ptr [edi + 1b82h], al
write_large_diamond_lefthalfhat_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L66
    mov byte ptr [edi + 1b83h], al
write_large_diamond_lefthalfhat_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L67
    mov byte ptr [edi + 1904h], al
write_large_diamond_lefthalfhat_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L68
    mov byte ptr [edi + 1905h], al
write_large_diamond_lefthalfhat_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L69
    mov byte ptr [edi + 1686h], al
write_large_diamond_lefthalfhat_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L70
    mov byte ptr [edi + 1687h], al
write_large_diamond_lefthalfhat_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L71
    mov byte ptr [edi + 1408h], al
write_large_diamond_lefthalfhat_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L72
    mov byte ptr [edi + 1409h], al
write_large_diamond_lefthalfhat_L72:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L73
    mov byte ptr [edi + 118ah], al
write_large_diamond_lefthalfhat_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L74
    mov byte ptr [edi + 118bh], al
write_large_diamond_lefthalfhat_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L75
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_lefthalfhat_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L76
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_lefthalfhat_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L77
    mov byte ptr [edi + 0c8eh], al
write_large_diamond_lefthalfhat_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L78
    mov byte ptr [edi + 0c8fh], al
write_large_diamond_lefthalfhat_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L79
    mov byte ptr [edi + 0a10h], al
write_large_diamond_lefthalfhat_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L80
    mov byte ptr [edi + 0a11h], al
write_large_diamond_lefthalfhat_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L81
    mov byte ptr [edi + 792h], al
write_large_diamond_lefthalfhat_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L82
    mov byte ptr [edi + 793h], al
write_large_diamond_lefthalfhat_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L83
    mov byte ptr [edi + 514h], al
write_large_diamond_lefthalfhat_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L84
    mov byte ptr [edi + 515h], al
write_large_diamond_lefthalfhat_L84:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L85
    mov byte ptr [edi + 296h], al
write_large_diamond_lefthalfhat_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L86
    mov byte ptr [edi + 297h], al
write_large_diamond_lefthalfhat_L86:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L89
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L87
    mov byte ptr [edi + 18h], al
write_large_diamond_lefthalfhat_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L88
    mov byte ptr [edi + 19h], al
write_large_diamond_lefthalfhat_L88:
    inc esi
write_large_diamond_lefthalfhat_L89:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 4
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L90
    mov byte ptr [edi + 1b80h], al
write_large_diamond_lefthalfhat_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L91
    mov byte ptr [edi + 1b81h], al
write_large_diamond_lefthalfhat_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L92
    mov byte ptr [edi + 1902h], al
write_large_diamond_lefthalfhat_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L93
    mov byte ptr [edi + 1903h], al
write_large_diamond_lefthalfhat_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L94
    mov byte ptr [edi + 1684h], al
write_large_diamond_lefthalfhat_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L95
    mov byte ptr [edi + 1685h], al
write_large_diamond_lefthalfhat_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L96
    mov byte ptr [edi + 1406h], al
write_large_diamond_lefthalfhat_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L97
    mov byte ptr [edi + 1407h], al
write_large_diamond_lefthalfhat_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L98
    mov byte ptr [edi + 1188h], al
write_large_diamond_lefthalfhat_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L99
    mov byte ptr [edi + 1189h], al
write_large_diamond_lefthalfhat_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L100
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_lefthalfhat_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L101
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_lefthalfhat_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L102
    mov byte ptr [edi + 0c8ch], al
write_large_diamond_lefthalfhat_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L103
    mov byte ptr [edi + 0c8dh], al
write_large_diamond_lefthalfhat_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L104
    mov byte ptr [edi + 0a0eh], al
write_large_diamond_lefthalfhat_L104:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L105
    mov byte ptr [edi + 0a0fh], al
write_large_diamond_lefthalfhat_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L106
    mov byte ptr [edi + 790h], al
write_large_diamond_lefthalfhat_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L107
    mov byte ptr [edi + 791h], al
write_large_diamond_lefthalfhat_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L108
    mov byte ptr [edi + 512h], al
write_large_diamond_lefthalfhat_L108:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L109
    mov byte ptr [edi + 513h], al
write_large_diamond_lefthalfhat_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L110
    mov byte ptr [edi + 294h], al
write_large_diamond_lefthalfhat_L110:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L111
    mov byte ptr [edi + 295h], al
write_large_diamond_lefthalfhat_L111:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L114
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L112
    mov byte ptr [edi + 16h], al
write_large_diamond_lefthalfhat_L112:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L113
    mov byte ptr [edi + 17h], al
write_large_diamond_lefthalfhat_L113:
    inc esi
write_large_diamond_lefthalfhat_L114:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 6
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L115
    mov byte ptr [edi + 1900h], al
write_large_diamond_lefthalfhat_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L116
    mov byte ptr [edi + 1901h], al
write_large_diamond_lefthalfhat_L116:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L117
    mov byte ptr [edi + 1682h], al
write_large_diamond_lefthalfhat_L117:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L118
    mov byte ptr [edi + 1683h], al
write_large_diamond_lefthalfhat_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L119
    mov byte ptr [edi + 1404h], al
write_large_diamond_lefthalfhat_L119:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L120
    mov byte ptr [edi + 1405h], al
write_large_diamond_lefthalfhat_L120:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L121
    mov byte ptr [edi + 1186h], al
write_large_diamond_lefthalfhat_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L122
    mov byte ptr [edi + 1187h], al
write_large_diamond_lefthalfhat_L122:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L123
    mov byte ptr [edi + 0f08h], al
write_large_diamond_lefthalfhat_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L124
    mov byte ptr [edi + 0f09h], al
write_large_diamond_lefthalfhat_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L125
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_lefthalfhat_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L126
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_lefthalfhat_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L127
    mov byte ptr [edi + 0a0ch], al
write_large_diamond_lefthalfhat_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L128
    mov byte ptr [edi + 0a0dh], al
write_large_diamond_lefthalfhat_L128:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L129
    mov byte ptr [edi + 78eh], al
write_large_diamond_lefthalfhat_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L130
    mov byte ptr [edi + 78fh], al
write_large_diamond_lefthalfhat_L130:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L131
    mov byte ptr [edi + 510h], al
write_large_diamond_lefthalfhat_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L132
    mov byte ptr [edi + 511h], al
write_large_diamond_lefthalfhat_L132:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L133
    mov byte ptr [edi + 292h], al
write_large_diamond_lefthalfhat_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L134
    mov byte ptr [edi + 293h], al
write_large_diamond_lefthalfhat_L134:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L137
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L135
    mov byte ptr [edi + 14h], al
write_large_diamond_lefthalfhat_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L136
    mov byte ptr [edi + 15h], al
write_large_diamond_lefthalfhat_L136:
    inc esi
write_large_diamond_lefthalfhat_L137:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 8
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L138
    mov byte ptr [edi + 1680h], al
write_large_diamond_lefthalfhat_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L139
    mov byte ptr [edi + 1681h], al
write_large_diamond_lefthalfhat_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L140
    mov byte ptr [edi + 1402h], al
write_large_diamond_lefthalfhat_L140:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L141
    mov byte ptr [edi + 1403h], al
write_large_diamond_lefthalfhat_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L142
    mov byte ptr [edi + 1184h], al
write_large_diamond_lefthalfhat_L142:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L143
    mov byte ptr [edi + 1185h], al
write_large_diamond_lefthalfhat_L143:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L144
    mov byte ptr [edi + 0f06h], al
write_large_diamond_lefthalfhat_L144:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L145
    mov byte ptr [edi + 0f07h], al
write_large_diamond_lefthalfhat_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L146
    mov byte ptr [edi + 0c88h], al
write_large_diamond_lefthalfhat_L146:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L147
    mov byte ptr [edi + 0c89h], al
write_large_diamond_lefthalfhat_L147:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L148
    mov byte ptr [edi + 0a0ah], al
write_large_diamond_lefthalfhat_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L149
    mov byte ptr [edi + 0a0bh], al
write_large_diamond_lefthalfhat_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L150
    mov byte ptr [edi + 78ch], al
write_large_diamond_lefthalfhat_L150:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L151
    mov byte ptr [edi + 78dh], al
write_large_diamond_lefthalfhat_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L152
    mov byte ptr [edi + 50eh], al
write_large_diamond_lefthalfhat_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L153
    mov byte ptr [edi + 50fh], al
write_large_diamond_lefthalfhat_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L154
    mov byte ptr [edi + 290h], al
write_large_diamond_lefthalfhat_L154:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L155
    mov byte ptr [edi + 291h], al
write_large_diamond_lefthalfhat_L155:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L158
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L156
    mov byte ptr [edi + 12h], al
write_large_diamond_lefthalfhat_L156:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L157
    mov byte ptr [edi + 13h], al
write_large_diamond_lefthalfhat_L157:
    inc esi
write_large_diamond_lefthalfhat_L158:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 0ah
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L159
    mov byte ptr [edi + 1400h], al
write_large_diamond_lefthalfhat_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L160
    mov byte ptr [edi + 1401h], al
write_large_diamond_lefthalfhat_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L161
    mov byte ptr [edi + 1182h], al
write_large_diamond_lefthalfhat_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L162
    mov byte ptr [edi + 1183h], al
write_large_diamond_lefthalfhat_L162:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L163
    mov byte ptr [edi + 0f04h], al
write_large_diamond_lefthalfhat_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L164
    mov byte ptr [edi + 0f05h], al
write_large_diamond_lefthalfhat_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L165
    mov byte ptr [edi + 0c86h], al
write_large_diamond_lefthalfhat_L165:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L166
    mov byte ptr [edi + 0c87h], al
write_large_diamond_lefthalfhat_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L167
    mov byte ptr [edi + 0a08h], al
write_large_diamond_lefthalfhat_L167:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L168
    mov byte ptr [edi + 0a09h], al
write_large_diamond_lefthalfhat_L168:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L169
    mov byte ptr [edi + 78ah], al
write_large_diamond_lefthalfhat_L169:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L170
    mov byte ptr [edi + 78bh], al
write_large_diamond_lefthalfhat_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L171
    mov byte ptr [edi + 50ch], al
write_large_diamond_lefthalfhat_L171:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L172
    mov byte ptr [edi + 50dh], al
write_large_diamond_lefthalfhat_L172:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L173
    mov byte ptr [edi + 28eh], al
write_large_diamond_lefthalfhat_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L174
    mov byte ptr [edi + 28fh], al
write_large_diamond_lefthalfhat_L174:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L177
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L175
    mov byte ptr [edi + 10h], al
write_large_diamond_lefthalfhat_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L176
    mov byte ptr [edi + 11h], al
write_large_diamond_lefthalfhat_L176:
    inc esi
write_large_diamond_lefthalfhat_L177:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 0ch
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L178
    mov byte ptr [edi + 1180h], al
write_large_diamond_lefthalfhat_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L179
    mov byte ptr [edi + 1181h], al
write_large_diamond_lefthalfhat_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L180
    mov byte ptr [edi + 0f02h], al
write_large_diamond_lefthalfhat_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L181
    mov byte ptr [edi + 0f03h], al
write_large_diamond_lefthalfhat_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L182
    mov byte ptr [edi + 0c84h], al
write_large_diamond_lefthalfhat_L182:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L183
    mov byte ptr [edi + 0c85h], al
write_large_diamond_lefthalfhat_L183:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L184
    mov byte ptr [edi + 0a06h], al
write_large_diamond_lefthalfhat_L184:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L185
    mov byte ptr [edi + 0a07h], al
write_large_diamond_lefthalfhat_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L186
    mov byte ptr [edi + 788h], al
write_large_diamond_lefthalfhat_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L187
    mov byte ptr [edi + 789h], al
write_large_diamond_lefthalfhat_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L188
    mov byte ptr [edi + 50ah], al
write_large_diamond_lefthalfhat_L188:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L189
    mov byte ptr [edi + 50bh], al
write_large_diamond_lefthalfhat_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L190
    mov byte ptr [edi + 28ch], al
write_large_diamond_lefthalfhat_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L191
    mov byte ptr [edi + 28dh], al
write_large_diamond_lefthalfhat_L191:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L194
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L192
    mov byte ptr [edi + 0eh], al
write_large_diamond_lefthalfhat_L192:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L193
    mov byte ptr [edi + 0fh], al
write_large_diamond_lefthalfhat_L193:
    inc esi
write_large_diamond_lefthalfhat_L194:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 0eh
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L195
    mov byte ptr [edi + 0f00h], al
write_large_diamond_lefthalfhat_L195:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L196
    mov byte ptr [edi + 0f01h], al
write_large_diamond_lefthalfhat_L196:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L197
    mov byte ptr [edi + 0c82h], al
write_large_diamond_lefthalfhat_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L198
    mov byte ptr [edi + 0c83h], al
write_large_diamond_lefthalfhat_L198:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L199
    mov byte ptr [edi + 0a04h], al
write_large_diamond_lefthalfhat_L199:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L200
    mov byte ptr [edi + 0a05h], al
write_large_diamond_lefthalfhat_L200:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L201
    mov byte ptr [edi + 786h], al
write_large_diamond_lefthalfhat_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L202
    mov byte ptr [edi + 787h], al
write_large_diamond_lefthalfhat_L202:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L203
    mov byte ptr [edi + 508h], al
write_large_diamond_lefthalfhat_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L204
    mov byte ptr [edi + 509h], al
write_large_diamond_lefthalfhat_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L205
    mov byte ptr [edi + 28ah], al
write_large_diamond_lefthalfhat_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L206
    mov byte ptr [edi + 28bh], al
write_large_diamond_lefthalfhat_L206:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L209
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L207
    mov byte ptr [edi + 0ch], al
write_large_diamond_lefthalfhat_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L208
    mov byte ptr [edi + 0dh], al
write_large_diamond_lefthalfhat_L208:
    inc esi
write_large_diamond_lefthalfhat_L209:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 10h
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L210
    mov byte ptr [edi + 0c80h], al
write_large_diamond_lefthalfhat_L210:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L211
    mov byte ptr [edi + 0c81h], al
write_large_diamond_lefthalfhat_L211:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L212
    mov byte ptr [edi + 0a02h], al
write_large_diamond_lefthalfhat_L212:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L213
    mov byte ptr [edi + 0a03h], al
write_large_diamond_lefthalfhat_L213:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L214
    mov byte ptr [edi + 784h], al
write_large_diamond_lefthalfhat_L214:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L215
    mov byte ptr [edi + 785h], al
write_large_diamond_lefthalfhat_L215:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L216
    mov byte ptr [edi + 506h], al
write_large_diamond_lefthalfhat_L216:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L217
    mov byte ptr [edi + 507h], al
write_large_diamond_lefthalfhat_L217:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L218
    mov byte ptr [edi + 288h], al
write_large_diamond_lefthalfhat_L218:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L219
    mov byte ptr [edi + 289h], al
write_large_diamond_lefthalfhat_L219:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L222
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L220
    mov byte ptr [edi + 0ah], al
write_large_diamond_lefthalfhat_L220:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L221
    mov byte ptr [edi + 0bh], al
write_large_diamond_lefthalfhat_L221:
    inc esi
write_large_diamond_lefthalfhat_L222:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 12h
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L223
    mov byte ptr [edi + 0a00h], al
write_large_diamond_lefthalfhat_L223:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L224
    mov byte ptr [edi + 0a01h], al
write_large_diamond_lefthalfhat_L224:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L225
    mov byte ptr [edi + 782h], al
write_large_diamond_lefthalfhat_L225:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L226
    mov byte ptr [edi + 783h], al
write_large_diamond_lefthalfhat_L226:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L227
    mov byte ptr [edi + 504h], al
write_large_diamond_lefthalfhat_L227:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L228
    mov byte ptr [edi + 505h], al
write_large_diamond_lefthalfhat_L228:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L229
    mov byte ptr [edi + 286h], al
write_large_diamond_lefthalfhat_L229:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L230
    mov byte ptr [edi + 287h], al
write_large_diamond_lefthalfhat_L230:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L233
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L231
    mov byte ptr [edi + 8], al
write_large_diamond_lefthalfhat_L231:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L232
    mov byte ptr [edi + 9], al
write_large_diamond_lefthalfhat_L232:
    inc esi
write_large_diamond_lefthalfhat_L233:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 14h
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L234
    mov byte ptr [edi + 780h], al
write_large_diamond_lefthalfhat_L234:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L235
    mov byte ptr [edi + 781h], al
write_large_diamond_lefthalfhat_L235:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L236
    mov byte ptr [edi + 502h], al
write_large_diamond_lefthalfhat_L236:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L237
    mov byte ptr [edi + 503h], al
write_large_diamond_lefthalfhat_L237:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L238
    mov byte ptr [edi + 284h], al
write_large_diamond_lefthalfhat_L238:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L239
    mov byte ptr [edi + 285h], al
write_large_diamond_lefthalfhat_L239:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L242
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L240
    mov byte ptr [edi + 6], al
write_large_diamond_lefthalfhat_L240:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L241
    mov byte ptr [edi + 7], al
write_large_diamond_lefthalfhat_L241:
    inc esi
write_large_diamond_lefthalfhat_L242:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_lefthalfhat_L257
    add esi, 16h
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L243
    mov byte ptr [edi + 500h], al
write_large_diamond_lefthalfhat_L243:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L244
    mov byte ptr [edi + 501h], al
write_large_diamond_lefthalfhat_L244:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L245
    mov byte ptr [edi + 282h], al
write_large_diamond_lefthalfhat_L245:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L246
    mov byte ptr [edi + 283h], al
write_large_diamond_lefthalfhat_L246:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L249
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L247
    mov byte ptr [edi + 4], al
write_large_diamond_lefthalfhat_L247:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L248
    mov byte ptr [edi + 5], al
write_large_diamond_lefthalfhat_L248:
    inc esi
write_large_diamond_lefthalfhat_L249:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_large_diamond_lefthalfhat_L257
    add esi, 18h
    add esi, dword ptr [_sndinit + 2]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L250
    mov byte ptr [edi + 280h], al
write_large_diamond_lefthalfhat_L250:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L251
    mov byte ptr [edi + 281h], al
write_large_diamond_lefthalfhat_L251:
    inc esi
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L254
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L252
    mov byte ptr [edi + 2], al
write_large_diamond_lefthalfhat_L252:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L253
    mov byte ptr [edi + 3], al
write_large_diamond_lefthalfhat_L253:
    inc esi
write_large_diamond_lefthalfhat_L254:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_large_diamond_lefthalfhat_L257
    add esi, 1ah
    add esi, dword ptr [_sndinit + 2]
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_lefthalfhat_L257
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L255
    mov byte ptr [edi], al
write_large_diamond_lefthalfhat_L255:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfhat_L256
    mov byte ptr [edi + 1], al
write_large_diamond_lefthalfhat_L256:
    inc esi
write_large_diamond_lefthalfhat_L257:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_large_diamond_righthalfhat
; ════════════════════════════════════════════════════════════
write_large_diamond_righthalfhat_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 2], ebx
    mov ebx, edx
    mov ecx, 0
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_righthalfhat_L1
    add edi, 1ch
write_large_diamond_righthalfhat_L1:
    cmp ebx, ecx
    jle near ptr write_large_diamond_righthalfhat_L33
    sub edi, dword ptr [_screen_width]
    push edi
    add esi, 2
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_righthalfhat_L4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L2
    mov byte ptr [edi], al
write_large_diamond_righthalfhat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L3
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfhat_L3:
    inc esi
    add edi, 2
    sub esi, 2
write_large_diamond_righthalfhat_L4:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L5
    mov byte ptr [edi + 280h], al
write_large_diamond_righthalfhat_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L6
    mov byte ptr [edi + 281h], al
write_large_diamond_righthalfhat_L6:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L7
    mov byte ptr [edi + 500h], al
write_large_diamond_righthalfhat_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L8
    mov byte ptr [edi + 501h], al
write_large_diamond_righthalfhat_L8:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L9
    mov byte ptr [edi + 780h], al
write_large_diamond_righthalfhat_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L10
    mov byte ptr [edi + 781h], al
write_large_diamond_righthalfhat_L10:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L11
    mov byte ptr [edi + 0a00h], al
write_large_diamond_righthalfhat_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L12
    mov byte ptr [edi + 0a01h], al
write_large_diamond_righthalfhat_L12:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L13
    mov byte ptr [edi + 0c80h], al
write_large_diamond_righthalfhat_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L14
    mov byte ptr [edi + 0c81h], al
write_large_diamond_righthalfhat_L14:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L15
    mov byte ptr [edi + 0f00h], al
write_large_diamond_righthalfhat_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L16
    mov byte ptr [edi + 0f01h], al
write_large_diamond_righthalfhat_L16:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L17
    mov byte ptr [edi + 1180h], al
write_large_diamond_righthalfhat_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L18
    mov byte ptr [edi + 1181h], al
write_large_diamond_righthalfhat_L18:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L19
    mov byte ptr [edi + 1400h], al
write_large_diamond_righthalfhat_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L20
    mov byte ptr [edi + 1401h], al
write_large_diamond_righthalfhat_L20:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L21
    mov byte ptr [edi + 1680h], al
write_large_diamond_righthalfhat_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L22
    mov byte ptr [edi + 1681h], al
write_large_diamond_righthalfhat_L22:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L23
    mov byte ptr [edi + 1900h], al
write_large_diamond_righthalfhat_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L24
    mov byte ptr [edi + 1901h], al
write_large_diamond_righthalfhat_L24:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L25
    mov byte ptr [edi + 1b80h], al
write_large_diamond_righthalfhat_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L26
    mov byte ptr [edi + 1b81h], al
write_large_diamond_righthalfhat_L26:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L27
    mov byte ptr [edi + 1e00h], al
write_large_diamond_righthalfhat_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L28
    mov byte ptr [edi + 1e01h], al
write_large_diamond_righthalfhat_L28:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L29
    mov byte ptr [edi + 2080h], al
write_large_diamond_righthalfhat_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L30
    mov byte ptr [edi + 2081h], al
write_large_diamond_righthalfhat_L30:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L31
    mov byte ptr [edi + 2300h], al
write_large_diamond_righthalfhat_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L32
    mov byte ptr [edi + 2301h], al
write_large_diamond_righthalfhat_L32:
    inc esi
    add edi, 2
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_large_diamond_righthalfhat_L1
    popad
    ret
write_large_diamond_righthalfhat_L33:
    add esi, 2
    cmp dword ptr [_sndinit + 2], 2
    je write_large_diamond_righthalfhat_L34
    add edi, 2
write_large_diamond_righthalfhat_L34:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L35
    mov byte ptr [edi], al
write_large_diamond_righthalfhat_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L36
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfhat_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L37
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfhat_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L38
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfhat_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L39
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfhat_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L40
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfhat_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L41
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfhat_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L42
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfhat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L43
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfhat_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L44
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfhat_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L45
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfhat_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L46
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfhat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L47
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfhat_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L48
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfhat_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L49
    mov byte ptr [edi + 118eh], al
write_large_diamond_righthalfhat_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L50
    mov byte ptr [edi + 118fh], al
write_large_diamond_righthalfhat_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L51
    mov byte ptr [edi + 1410h], al
write_large_diamond_righthalfhat_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L52
    mov byte ptr [edi + 1411h], al
write_large_diamond_righthalfhat_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L53
    mov byte ptr [edi + 1692h], al
write_large_diamond_righthalfhat_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L54
    mov byte ptr [edi + 1693h], al
write_large_diamond_righthalfhat_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L55
    mov byte ptr [edi + 1914h], al
write_large_diamond_righthalfhat_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L56
    mov byte ptr [edi + 1915h], al
write_large_diamond_righthalfhat_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L57
    mov byte ptr [edi + 1b96h], al
write_large_diamond_righthalfhat_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L58
    mov byte ptr [edi + 1b97h], al
write_large_diamond_righthalfhat_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L59
    mov byte ptr [edi + 1e18h], al
write_large_diamond_righthalfhat_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L60
    mov byte ptr [edi + 1e19h], al
write_large_diamond_righthalfhat_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L61
    mov byte ptr [edi + 209ah], al
write_large_diamond_righthalfhat_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L62
    mov byte ptr [edi + 209bh], al
write_large_diamond_righthalfhat_L62:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L63
    mov byte ptr [edi + 2], al
write_large_diamond_righthalfhat_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L64
    mov byte ptr [edi + 3], al
write_large_diamond_righthalfhat_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L65
    mov byte ptr [edi + 284h], al
write_large_diamond_righthalfhat_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L66
    mov byte ptr [edi + 285h], al
write_large_diamond_righthalfhat_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L67
    mov byte ptr [edi + 506h], al
write_large_diamond_righthalfhat_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L68
    mov byte ptr [edi + 507h], al
write_large_diamond_righthalfhat_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L69
    mov byte ptr [edi + 788h], al
write_large_diamond_righthalfhat_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L70
    mov byte ptr [edi + 789h], al
write_large_diamond_righthalfhat_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L71
    mov byte ptr [edi + 0a0ah], al
write_large_diamond_righthalfhat_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L72
    mov byte ptr [edi + 0a0bh], al
write_large_diamond_righthalfhat_L72:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L73
    mov byte ptr [edi + 0c8ch], al
write_large_diamond_righthalfhat_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L74
    mov byte ptr [edi + 0c8dh], al
write_large_diamond_righthalfhat_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L75
    mov byte ptr [edi + 0f0eh], al
write_large_diamond_righthalfhat_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L76
    mov byte ptr [edi + 0f0fh], al
write_large_diamond_righthalfhat_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L77
    mov byte ptr [edi + 1190h], al
write_large_diamond_righthalfhat_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L78
    mov byte ptr [edi + 1191h], al
write_large_diamond_righthalfhat_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L79
    mov byte ptr [edi + 1412h], al
write_large_diamond_righthalfhat_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L80
    mov byte ptr [edi + 1413h], al
write_large_diamond_righthalfhat_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L81
    mov byte ptr [edi + 1694h], al
write_large_diamond_righthalfhat_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L82
    mov byte ptr [edi + 1695h], al
write_large_diamond_righthalfhat_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L83
    mov byte ptr [edi + 1916h], al
write_large_diamond_righthalfhat_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L84
    mov byte ptr [edi + 1917h], al
write_large_diamond_righthalfhat_L84:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L85
    mov byte ptr [edi + 1b98h], al
write_large_diamond_righthalfhat_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L86
    mov byte ptr [edi + 1b99h], al
write_large_diamond_righthalfhat_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L87
    mov byte ptr [edi + 1e1ah], al
write_large_diamond_righthalfhat_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L88
    mov byte ptr [edi + 1e1bh], al
write_large_diamond_righthalfhat_L88:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L89
    mov byte ptr [edi + 4], al
write_large_diamond_righthalfhat_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L90
    mov byte ptr [edi + 5], al
write_large_diamond_righthalfhat_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L91
    mov byte ptr [edi + 286h], al
write_large_diamond_righthalfhat_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L92
    mov byte ptr [edi + 287h], al
write_large_diamond_righthalfhat_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L93
    mov byte ptr [edi + 508h], al
write_large_diamond_righthalfhat_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L94
    mov byte ptr [edi + 509h], al
write_large_diamond_righthalfhat_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L95
    mov byte ptr [edi + 78ah], al
write_large_diamond_righthalfhat_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L96
    mov byte ptr [edi + 78bh], al
write_large_diamond_righthalfhat_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L97
    mov byte ptr [edi + 0a0ch], al
write_large_diamond_righthalfhat_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L98
    mov byte ptr [edi + 0a0dh], al
write_large_diamond_righthalfhat_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L99
    mov byte ptr [edi + 0c8eh], al
write_large_diamond_righthalfhat_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L100
    mov byte ptr [edi + 0c8fh], al
write_large_diamond_righthalfhat_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L101
    mov byte ptr [edi + 0f10h], al
write_large_diamond_righthalfhat_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L102
    mov byte ptr [edi + 0f11h], al
write_large_diamond_righthalfhat_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L103
    mov byte ptr [edi + 1192h], al
write_large_diamond_righthalfhat_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L104
    mov byte ptr [edi + 1193h], al
write_large_diamond_righthalfhat_L104:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L105
    mov byte ptr [edi + 1414h], al
write_large_diamond_righthalfhat_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L106
    mov byte ptr [edi + 1415h], al
write_large_diamond_righthalfhat_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L107
    mov byte ptr [edi + 1696h], al
write_large_diamond_righthalfhat_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L108
    mov byte ptr [edi + 1697h], al
write_large_diamond_righthalfhat_L108:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L109
    mov byte ptr [edi + 1918h], al
write_large_diamond_righthalfhat_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L110
    mov byte ptr [edi + 1919h], al
write_large_diamond_righthalfhat_L110:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L111
    mov byte ptr [edi + 1b9ah], al
write_large_diamond_righthalfhat_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L112
    mov byte ptr [edi + 1b9bh], al
write_large_diamond_righthalfhat_L112:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 8
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L113
    mov byte ptr [edi + 6], al
write_large_diamond_righthalfhat_L113:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L114
    mov byte ptr [edi + 7], al
write_large_diamond_righthalfhat_L114:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L115
    mov byte ptr [edi + 288h], al
write_large_diamond_righthalfhat_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L116
    mov byte ptr [edi + 289h], al
write_large_diamond_righthalfhat_L116:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L117
    mov byte ptr [edi + 50ah], al
write_large_diamond_righthalfhat_L117:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L118
    mov byte ptr [edi + 50bh], al
write_large_diamond_righthalfhat_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L119
    mov byte ptr [edi + 78ch], al
write_large_diamond_righthalfhat_L119:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L120
    mov byte ptr [edi + 78dh], al
write_large_diamond_righthalfhat_L120:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L121
    mov byte ptr [edi + 0a0eh], al
write_large_diamond_righthalfhat_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L122
    mov byte ptr [edi + 0a0fh], al
write_large_diamond_righthalfhat_L122:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L123
    mov byte ptr [edi + 0c90h], al
write_large_diamond_righthalfhat_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L124
    mov byte ptr [edi + 0c91h], al
write_large_diamond_righthalfhat_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L125
    mov byte ptr [edi + 0f12h], al
write_large_diamond_righthalfhat_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L126
    mov byte ptr [edi + 0f13h], al
write_large_diamond_righthalfhat_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L127
    mov byte ptr [edi + 1194h], al
write_large_diamond_righthalfhat_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L128
    mov byte ptr [edi + 1195h], al
write_large_diamond_righthalfhat_L128:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L129
    mov byte ptr [edi + 1416h], al
write_large_diamond_righthalfhat_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L130
    mov byte ptr [edi + 1417h], al
write_large_diamond_righthalfhat_L130:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L131
    mov byte ptr [edi + 1698h], al
write_large_diamond_righthalfhat_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L132
    mov byte ptr [edi + 1699h], al
write_large_diamond_righthalfhat_L132:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L133
    mov byte ptr [edi + 191ah], al
write_large_diamond_righthalfhat_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L134
    mov byte ptr [edi + 191bh], al
write_large_diamond_righthalfhat_L134:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L135
    mov byte ptr [edi + 8], al
write_large_diamond_righthalfhat_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L136
    mov byte ptr [edi + 9], al
write_large_diamond_righthalfhat_L136:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L137
    mov byte ptr [edi + 28ah], al
write_large_diamond_righthalfhat_L137:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L138
    mov byte ptr [edi + 28bh], al
write_large_diamond_righthalfhat_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L139
    mov byte ptr [edi + 50ch], al
write_large_diamond_righthalfhat_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L140
    mov byte ptr [edi + 50dh], al
write_large_diamond_righthalfhat_L140:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L141
    mov byte ptr [edi + 78eh], al
write_large_diamond_righthalfhat_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L142
    mov byte ptr [edi + 78fh], al
write_large_diamond_righthalfhat_L142:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L143
    mov byte ptr [edi + 0a10h], al
write_large_diamond_righthalfhat_L143:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L144
    mov byte ptr [edi + 0a11h], al
write_large_diamond_righthalfhat_L144:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L145
    mov byte ptr [edi + 0c92h], al
write_large_diamond_righthalfhat_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L146
    mov byte ptr [edi + 0c93h], al
write_large_diamond_righthalfhat_L146:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L147
    mov byte ptr [edi + 0f14h], al
write_large_diamond_righthalfhat_L147:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L148
    mov byte ptr [edi + 0f15h], al
write_large_diamond_righthalfhat_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L149
    mov byte ptr [edi + 1196h], al
write_large_diamond_righthalfhat_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L150
    mov byte ptr [edi + 1197h], al
write_large_diamond_righthalfhat_L150:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L151
    mov byte ptr [edi + 1418h], al
write_large_diamond_righthalfhat_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L152
    mov byte ptr [edi + 1419h], al
write_large_diamond_righthalfhat_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L153
    mov byte ptr [edi + 169ah], al
write_large_diamond_righthalfhat_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L154
    mov byte ptr [edi + 169bh], al
write_large_diamond_righthalfhat_L154:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 0ch
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L155
    mov byte ptr [edi + 0ah], al
write_large_diamond_righthalfhat_L155:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L156
    mov byte ptr [edi + 0bh], al
write_large_diamond_righthalfhat_L156:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L157
    mov byte ptr [edi + 28ch], al
write_large_diamond_righthalfhat_L157:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L158
    mov byte ptr [edi + 28dh], al
write_large_diamond_righthalfhat_L158:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L159
    mov byte ptr [edi + 50eh], al
write_large_diamond_righthalfhat_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L160
    mov byte ptr [edi + 50fh], al
write_large_diamond_righthalfhat_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L161
    mov byte ptr [edi + 790h], al
write_large_diamond_righthalfhat_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L162
    mov byte ptr [edi + 791h], al
write_large_diamond_righthalfhat_L162:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L163
    mov byte ptr [edi + 0a12h], al
write_large_diamond_righthalfhat_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L164
    mov byte ptr [edi + 0a13h], al
write_large_diamond_righthalfhat_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L165
    mov byte ptr [edi + 0c94h], al
write_large_diamond_righthalfhat_L165:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L166
    mov byte ptr [edi + 0c95h], al
write_large_diamond_righthalfhat_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L167
    mov byte ptr [edi + 0f16h], al
write_large_diamond_righthalfhat_L167:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L168
    mov byte ptr [edi + 0f17h], al
write_large_diamond_righthalfhat_L168:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L169
    mov byte ptr [edi + 1198h], al
write_large_diamond_righthalfhat_L169:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L170
    mov byte ptr [edi + 1199h], al
write_large_diamond_righthalfhat_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L171
    mov byte ptr [edi + 141ah], al
write_large_diamond_righthalfhat_L171:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L172
    mov byte ptr [edi + 141bh], al
write_large_diamond_righthalfhat_L172:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L173
    mov byte ptr [edi + 0ch], al
write_large_diamond_righthalfhat_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L174
    mov byte ptr [edi + 0dh], al
write_large_diamond_righthalfhat_L174:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L175
    mov byte ptr [edi + 28eh], al
write_large_diamond_righthalfhat_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L176
    mov byte ptr [edi + 28fh], al
write_large_diamond_righthalfhat_L176:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L177
    mov byte ptr [edi + 510h], al
write_large_diamond_righthalfhat_L177:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L178
    mov byte ptr [edi + 511h], al
write_large_diamond_righthalfhat_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L179
    mov byte ptr [edi + 792h], al
write_large_diamond_righthalfhat_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L180
    mov byte ptr [edi + 793h], al
write_large_diamond_righthalfhat_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L181
    mov byte ptr [edi + 0a14h], al
write_large_diamond_righthalfhat_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L182
    mov byte ptr [edi + 0a15h], al
write_large_diamond_righthalfhat_L182:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L183
    mov byte ptr [edi + 0c96h], al
write_large_diamond_righthalfhat_L183:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L184
    mov byte ptr [edi + 0c97h], al
write_large_diamond_righthalfhat_L184:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L185
    mov byte ptr [edi + 0f18h], al
write_large_diamond_righthalfhat_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L186
    mov byte ptr [edi + 0f19h], al
write_large_diamond_righthalfhat_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L187
    mov byte ptr [edi + 119ah], al
write_large_diamond_righthalfhat_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L188
    mov byte ptr [edi + 119bh], al
write_large_diamond_righthalfhat_L188:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 10h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L189
    mov byte ptr [edi + 0eh], al
write_large_diamond_righthalfhat_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L190
    mov byte ptr [edi + 0fh], al
write_large_diamond_righthalfhat_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L191
    mov byte ptr [edi + 290h], al
write_large_diamond_righthalfhat_L191:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L192
    mov byte ptr [edi + 291h], al
write_large_diamond_righthalfhat_L192:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L193
    mov byte ptr [edi + 512h], al
write_large_diamond_righthalfhat_L193:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L194
    mov byte ptr [edi + 513h], al
write_large_diamond_righthalfhat_L194:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L195
    mov byte ptr [edi + 794h], al
write_large_diamond_righthalfhat_L195:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L196
    mov byte ptr [edi + 795h], al
write_large_diamond_righthalfhat_L196:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L197
    mov byte ptr [edi + 0a16h], al
write_large_diamond_righthalfhat_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L198
    mov byte ptr [edi + 0a17h], al
write_large_diamond_righthalfhat_L198:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L199
    mov byte ptr [edi + 0c98h], al
write_large_diamond_righthalfhat_L199:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L200
    mov byte ptr [edi + 0c99h], al
write_large_diamond_righthalfhat_L200:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L201
    mov byte ptr [edi + 0f1ah], al
write_large_diamond_righthalfhat_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L202
    mov byte ptr [edi + 0f1bh], al
write_large_diamond_righthalfhat_L202:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 12h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L203
    mov byte ptr [edi + 10h], al
write_large_diamond_righthalfhat_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L204
    mov byte ptr [edi + 11h], al
write_large_diamond_righthalfhat_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L205
    mov byte ptr [edi + 292h], al
write_large_diamond_righthalfhat_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L206
    mov byte ptr [edi + 293h], al
write_large_diamond_righthalfhat_L206:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L207
    mov byte ptr [edi + 514h], al
write_large_diamond_righthalfhat_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L208
    mov byte ptr [edi + 515h], al
write_large_diamond_righthalfhat_L208:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L209
    mov byte ptr [edi + 796h], al
write_large_diamond_righthalfhat_L209:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L210
    mov byte ptr [edi + 797h], al
write_large_diamond_righthalfhat_L210:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L211
    mov byte ptr [edi + 0a18h], al
write_large_diamond_righthalfhat_L211:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L212
    mov byte ptr [edi + 0a19h], al
write_large_diamond_righthalfhat_L212:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L213
    mov byte ptr [edi + 0c9ah], al
write_large_diamond_righthalfhat_L213:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L214
    mov byte ptr [edi + 0c9bh], al
write_large_diamond_righthalfhat_L214:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 14h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L215
    mov byte ptr [edi + 12h], al
write_large_diamond_righthalfhat_L215:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L216
    mov byte ptr [edi + 13h], al
write_large_diamond_righthalfhat_L216:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L217
    mov byte ptr [edi + 294h], al
write_large_diamond_righthalfhat_L217:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L218
    mov byte ptr [edi + 295h], al
write_large_diamond_righthalfhat_L218:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L219
    mov byte ptr [edi + 516h], al
write_large_diamond_righthalfhat_L219:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L220
    mov byte ptr [edi + 517h], al
write_large_diamond_righthalfhat_L220:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L221
    mov byte ptr [edi + 798h], al
write_large_diamond_righthalfhat_L221:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L222
    mov byte ptr [edi + 799h], al
write_large_diamond_righthalfhat_L222:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L223
    mov byte ptr [edi + 0a1ah], al
write_large_diamond_righthalfhat_L223:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L224
    mov byte ptr [edi + 0a1bh], al
write_large_diamond_righthalfhat_L224:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 16h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L225
    mov byte ptr [edi + 14h], al
write_large_diamond_righthalfhat_L225:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L226
    mov byte ptr [edi + 15h], al
write_large_diamond_righthalfhat_L226:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L227
    mov byte ptr [edi + 296h], al
write_large_diamond_righthalfhat_L227:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L228
    mov byte ptr [edi + 297h], al
write_large_diamond_righthalfhat_L228:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L229
    mov byte ptr [edi + 518h], al
write_large_diamond_righthalfhat_L229:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L230
    mov byte ptr [edi + 519h], al
write_large_diamond_righthalfhat_L230:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L231
    mov byte ptr [edi + 79ah], al
write_large_diamond_righthalfhat_L231:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L232
    mov byte ptr [edi + 79bh], al
write_large_diamond_righthalfhat_L232:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_large_diamond_righthalfhat_L245
    add esi, 18h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L233
    mov byte ptr [edi + 16h], al
write_large_diamond_righthalfhat_L233:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L234
    mov byte ptr [edi + 17h], al
write_large_diamond_righthalfhat_L234:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L235
    mov byte ptr [edi + 298h], al
write_large_diamond_righthalfhat_L235:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L236
    mov byte ptr [edi + 299h], al
write_large_diamond_righthalfhat_L236:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L237
    mov byte ptr [edi + 51ah], al
write_large_diamond_righthalfhat_L237:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L238
    mov byte ptr [edi + 51bh], al
write_large_diamond_righthalfhat_L238:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_large_diamond_righthalfhat_L245
    add esi, 1ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L239
    mov byte ptr [edi + 18h], al
write_large_diamond_righthalfhat_L239:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L240
    mov byte ptr [edi + 19h], al
write_large_diamond_righthalfhat_L240:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L241
    mov byte ptr [edi + 29ah], al
write_large_diamond_righthalfhat_L241:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L242
    mov byte ptr [edi + 29bh], al
write_large_diamond_righthalfhat_L242:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_large_diamond_righthalfhat_L245
    add esi, 1ch
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L243
    mov byte ptr [edi + 1ah], al
write_large_diamond_righthalfhat_L243:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfhat_L244
    mov byte ptr [edi + 1bh], al
write_large_diamond_righthalfhat_L244:
    inc esi
write_large_diamond_righthalfhat_L245:
    popad
    ret

_TEXT ENDS
END
