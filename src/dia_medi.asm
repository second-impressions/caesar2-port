.386p
.MODEL FLAT

PUBLIC place_i_medium_diamond_
PUBLIC place_i_medium_diamond_lefthalf_
PUBLIC place_i_medium_diamond_righthalf_
PUBLIC write_medium_diamond_hat_
PUBLIC write_medium_diamond_lefthat_
PUBLIC write_medium_diamond_righthat_
PUBLIC write_medium_diamond_lefthalfhat_
PUBLIC write_medium_diamond_righthalfhat_
PUBLIC write_medium_diamond_roof_
PUBLIC write_medium_diamond_leftroof_
PUBLIC write_medium_diamond_rightroof_
PUBLIC write_medium_diamond_righthalfroof_
PUBLIC write_medium_diamond_lefthalfroof_

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
; place_i_medium_diamond
; ════════════════════════════════════════════════════════════
place_i_medium_diamond_:
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
    jne place_i_medium_diamond_L1
    jmp near ptr place_i_medium_diamond_L2
place_i_medium_diamond_L1:
    mov ax, word ptr [esi]
    mov word ptr [edi + 0ch], ax
    mov eax, dword ptr [esi + 2]
    mov dword ptr [edi + 28ah], eax
    mov ax, word ptr [esi + 6]
    mov word ptr [edi + 28eh], ax
    mov eax, dword ptr [esi + 8]
    mov dword ptr [edi + 508h], eax
    mov eax, dword ptr [esi + 0ch]
    mov dword ptr [edi + 50ch], eax
    mov ax, word ptr [esi + 10h]
    mov word ptr [edi + 510h], ax
    mov eax, dword ptr [esi + 12h]
    mov dword ptr [edi + 786h], eax
    mov eax, dword ptr [esi + 16h]
    mov dword ptr [edi + 78ah], eax
    mov eax, dword ptr [esi + 1ah]
    mov dword ptr [edi + 78eh], eax
    mov ax, word ptr [esi + 1eh]
    mov word ptr [edi + 792h], ax
    mov eax, dword ptr [esi + 20h]
    mov dword ptr [edi + 0a04h], eax
    mov eax, dword ptr [esi + 24h]
    mov dword ptr [edi + 0a08h], eax
    mov eax, dword ptr [esi + 28h]
    mov dword ptr [edi + 0a0ch], eax
    mov eax, dword ptr [esi + 2ch]
    mov dword ptr [edi + 0a10h], eax
    mov ax, word ptr [esi + 30h]
    mov word ptr [edi + 0a14h], ax
    mov eax, dword ptr [esi + 32h]
    mov dword ptr [edi + 0c82h], eax
    mov eax, dword ptr [esi + 36h]
    mov dword ptr [edi + 0c86h], eax
    mov eax, dword ptr [esi + 3ah]
    mov dword ptr [edi + 0c8ah], eax
    mov eax, dword ptr [esi + 3eh]
    mov dword ptr [edi + 0c8eh], eax
    mov eax, dword ptr [esi + 42h]
    mov dword ptr [edi + 0c92h], eax
    mov ax, word ptr [esi + 46h]
    mov word ptr [edi + 0c96h], ax
    mov eax, dword ptr [esi + 48h]
    mov dword ptr [edi + 0f00h], eax
    mov eax, dword ptr [esi + 4ch]
    mov dword ptr [edi + 0f04h], eax
    mov eax, dword ptr [esi + 50h]
    mov dword ptr [edi + 0f08h], eax
    mov eax, dword ptr [esi + 54h]
    mov dword ptr [edi + 0f0ch], eax
    mov eax, dword ptr [esi + 58h]
    mov dword ptr [edi + 0f10h], eax
    mov eax, dword ptr [esi + 5ch]
    mov dword ptr [edi + 0f14h], eax
    mov ax, word ptr [esi + 60h]
    mov word ptr [edi + 0f18h], ax
    cmp ebx, 1
    jne place_i_medium_diamond_L2
    jmp near ptr place_i_medium_diamond_L3
place_i_medium_diamond_L2:
    mov eax, dword ptr [esi + 62h]
    mov dword ptr [edi + 1180h], eax
    mov eax, dword ptr [esi + 66h]
    mov dword ptr [edi + 1184h], eax
    mov eax, dword ptr [esi + 6ah]
    mov dword ptr [edi + 1188h], eax
    mov eax, dword ptr [esi + 6eh]
    mov dword ptr [edi + 118ch], eax
    mov eax, dword ptr [esi + 72h]
    mov dword ptr [edi + 1190h], eax
    mov eax, dword ptr [esi + 76h]
    mov dword ptr [edi + 1194h], eax
    mov ax, word ptr [esi + 7ah]
    mov word ptr [edi + 1198h], ax
    mov eax, dword ptr [esi + 7ch]
    mov dword ptr [edi + 1402h], eax
    mov eax, dword ptr [esi + 80h]
    mov dword ptr [edi + 1406h], eax
    mov eax, dword ptr [esi + 84h]
    mov dword ptr [edi + 140ah], eax
    mov eax, dword ptr [esi + 88h]
    mov dword ptr [edi + 140eh], eax
    mov eax, dword ptr [esi + 8ch]
    mov dword ptr [edi + 1412h], eax
    mov ax, word ptr [esi + 90h]
    mov word ptr [edi + 1416h], ax
    mov eax, dword ptr [esi + 92h]
    mov dword ptr [edi + 1684h], eax
    mov eax, dword ptr [esi + 96h]
    mov dword ptr [edi + 1688h], eax
    mov eax, dword ptr [esi + 9ah]
    mov dword ptr [edi + 168ch], eax
    mov eax, dword ptr [esi + 9eh]
    mov dword ptr [edi + 1690h], eax
    mov ax, word ptr [esi + 0a2h]
    mov word ptr [edi + 1694h], ax
    mov eax, dword ptr [esi + 0a4h]
    mov dword ptr [edi + 1906h], eax
    mov eax, dword ptr [esi + 0a8h]
    mov dword ptr [edi + 190ah], eax
    mov eax, dword ptr [esi + 0ach]
    mov dword ptr [edi + 190eh], eax
    mov ax, word ptr [esi + 0b0h]
    mov word ptr [edi + 1912h], ax
    mov eax, dword ptr [esi + 0b2h]
    mov dword ptr [edi + 1b88h], eax
    mov eax, dword ptr [esi + 0b6h]
    mov dword ptr [edi + 1b8ch], eax
    mov ax, word ptr [esi + 0bah]
    mov word ptr [edi + 1b90h], ax
    mov eax, dword ptr [esi + 0bch]
    mov dword ptr [edi + 1e0ah], eax
    mov ax, word ptr [esi + 0c0h]
    mov word ptr [edi + 1e0eh], ax
    mov ax, word ptr [esi + 0c2h]
    mov word ptr [edi + 208ch], ax
place_i_medium_diamond_L3:
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_i_medium_diamond_lefthalf
; ════════════════════════════════════════════════════════════
place_i_medium_diamond_lefthalf_:
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
    jne place_i_medium_diamond_lefthalf_L1
    jmp place_i_medium_diamond_lefthalf_L2
place_i_medium_diamond_lefthalf_L1:
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
place_i_medium_diamond_lefthalf_L2:
    mov eax, dword ptr [esi + 70h]
    mov dword ptr [edi + 1180h], eax
    mov eax, dword ptr [esi + 74h]
    mov dword ptr [edi + 1184h], eax
    mov eax, dword ptr [esi + 78h]
    mov dword ptr [edi + 1188h], eax
    mov eax, dword ptr [esi + 88h]
    mov dword ptr [edi + 1400h], eax
    mov eax, dword ptr [esi + 8ch]
    mov dword ptr [edi + 1404h], eax
    mov ax, word ptr [esi + 90h]
    mov word ptr [edi + 1408h], ax
    mov eax, dword ptr [esi + 9ch]
    mov dword ptr [edi + 1680h], eax
    mov eax, dword ptr [esi + 0a0h]
    mov dword ptr [edi + 1684h], eax
    mov eax, dword ptr [esi + 0ach]
    mov dword ptr [edi + 1900h], eax
    mov ax, word ptr [esi + 0b0h]
    mov word ptr [edi + 1904h], ax
    mov eax, dword ptr [esi + 0b8h]
    mov dword ptr [edi + 1b80h], eax
    mov ax, word ptr [esi + 0c0h]
    mov word ptr [edi + 1e00h], ax
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_i_medium_diamond_righthalf
; ════════════════════════════════════════════════════════════
place_i_medium_diamond_righthalf_:
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
    jne place_i_medium_diamond_righthalf_L1
    jmp place_i_medium_diamond_righthalf_L2
place_i_medium_diamond_righthalf_L1:
    mov ax, word ptr [esi + 2]
    mov word ptr [edi + 28ah], ax
    mov eax, dword ptr [esi + 8]
    mov dword ptr [edi + 508h], eax
    mov eax, dword ptr [esi + 12h]
    mov dword ptr [edi + 786h], eax
    mov ax, word ptr [esi + 16h]
    mov word ptr [edi + 78ah], ax
    mov eax, dword ptr [esi + 20h]
    mov dword ptr [edi + 0a04h], eax
    mov eax, dword ptr [esi + 24h]
    mov dword ptr [edi + 0a08h], eax
    mov eax, dword ptr [esi + 32h]
    mov dword ptr [edi + 0c82h], eax
    mov eax, dword ptr [esi + 36h]
    mov dword ptr [edi + 0c86h], eax
    mov ax, word ptr [esi + 3ah]
    mov word ptr [edi + 0c8ah], ax
    mov eax, dword ptr [esi + 48h]
    mov dword ptr [edi + 0f00h], eax
    mov eax, dword ptr [esi + 4ch]
    mov dword ptr [edi + 0f04h], eax
    mov eax, dword ptr [esi + 50h]
    mov dword ptr [edi + 0f08h], eax
place_i_medium_diamond_righthalf_L2:
    mov eax, dword ptr [esi + 62h]
    mov dword ptr [edi + 1180h], eax
    mov eax, dword ptr [esi + 66h]
    mov dword ptr [edi + 1184h], eax
    mov eax, dword ptr [esi + 6ah]
    mov dword ptr [edi + 1188h], eax
    mov eax, dword ptr [esi + 7ch]
    mov dword ptr [edi + 1402h], eax
    mov eax, dword ptr [esi + 80h]
    mov dword ptr [edi + 1406h], eax
    mov ax, word ptr [esi + 84h]
    mov word ptr [edi + 140ah], ax
    mov eax, dword ptr [esi + 92h]
    mov dword ptr [edi + 1684h], eax
    mov eax, dword ptr [esi + 96h]
    mov dword ptr [edi + 1688h], eax
    mov eax, dword ptr [esi + 0a4h]
    mov dword ptr [edi + 1906h], eax
    mov ax, word ptr [esi + 0a8h]
    mov word ptr [edi + 190ah], ax
    mov eax, dword ptr [esi + 0b2h]
    mov dword ptr [edi + 1b88h], eax
    mov ax, word ptr [esi + 0bch]
    mov word ptr [edi + 1e0ah], ax
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_hat
; ════════════════════════════════════════════════════════════
write_medium_diamond_hat_:
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
write_medium_diamond_hat_L1:
    cmp ebx, ecx
    jle near ptr write_medium_diamond_hat_L28
    sub edi, dword ptr [_screen_width]
    push edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L2
    mov byte ptr [edi + 0f00h], al
write_medium_diamond_hat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L3
    mov byte ptr [edi + 0f01h], al
write_medium_diamond_hat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L4
    mov byte ptr [edi + 0c80h], al
write_medium_diamond_hat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L5
    mov byte ptr [edi + 0c81h], al
write_medium_diamond_hat_L5:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L6
    mov byte ptr [edi + 0a00h], al
write_medium_diamond_hat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L7
    mov byte ptr [edi + 0a01h], al
write_medium_diamond_hat_L7:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L8
    mov byte ptr [edi + 780h], al
write_medium_diamond_hat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L9
    mov byte ptr [edi + 781h], al
write_medium_diamond_hat_L9:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L10
    mov byte ptr [edi + 500h], al
write_medium_diamond_hat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L11
    mov byte ptr [edi + 501h], al
write_medium_diamond_hat_L11:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L12
    mov byte ptr [edi + 280h], al
write_medium_diamond_hat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L13
    mov byte ptr [edi + 281h], al
write_medium_diamond_hat_L13:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L14
    mov byte ptr [edi], al
write_medium_diamond_hat_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L15
    mov byte ptr [edi + 1], al
write_medium_diamond_hat_L15:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L16
    mov byte ptr [edi + 280h], al
write_medium_diamond_hat_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L17
    mov byte ptr [edi + 281h], al
write_medium_diamond_hat_L17:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L18
    mov byte ptr [edi + 500h], al
write_medium_diamond_hat_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L19
    mov byte ptr [edi + 501h], al
write_medium_diamond_hat_L19:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L20
    mov byte ptr [edi + 780h], al
write_medium_diamond_hat_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L21
    mov byte ptr [edi + 781h], al
write_medium_diamond_hat_L21:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L22
    mov byte ptr [edi + 0a00h], al
write_medium_diamond_hat_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L23
    mov byte ptr [edi + 0a01h], al
write_medium_diamond_hat_L23:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L24
    mov byte ptr [edi + 0c80h], al
write_medium_diamond_hat_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L25
    mov byte ptr [edi + 0c81h], al
write_medium_diamond_hat_L25:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L26
    mov byte ptr [edi + 0f00h], al
write_medium_diamond_hat_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L27
    mov byte ptr [edi + 0f01h], al
write_medium_diamond_hat_L27:
    inc esi
    add edi, 2
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_medium_diamond_hat_L1
    popad
    ret
write_medium_diamond_hat_L28:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L29
    mov byte ptr [edi + 0c80h], al
write_medium_diamond_hat_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L30
    mov byte ptr [edi + 0c81h], al
write_medium_diamond_hat_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L31
    mov byte ptr [edi + 0a02h], al
write_medium_diamond_hat_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L32
    mov byte ptr [edi + 0a03h], al
write_medium_diamond_hat_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L33
    mov byte ptr [edi + 784h], al
write_medium_diamond_hat_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L34
    mov byte ptr [edi + 785h], al
write_medium_diamond_hat_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L35
    mov byte ptr [edi + 506h], al
write_medium_diamond_hat_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L36
    mov byte ptr [edi + 507h], al
write_medium_diamond_hat_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L37
    mov byte ptr [edi + 288h], al
write_medium_diamond_hat_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L38
    mov byte ptr [edi + 289h], al
write_medium_diamond_hat_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L39
    mov byte ptr [edi + 0ah], al
write_medium_diamond_hat_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L40
    mov byte ptr [edi + 0bh], al
write_medium_diamond_hat_L40:
    inc esi
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L41
    mov byte ptr [edi + 0eh], al
write_medium_diamond_hat_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L42
    mov byte ptr [edi + 0fh], al
write_medium_diamond_hat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L43
    mov byte ptr [edi + 290h], al
write_medium_diamond_hat_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L44
    mov byte ptr [edi + 291h], al
write_medium_diamond_hat_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L45
    mov byte ptr [edi + 512h], al
write_medium_diamond_hat_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L46
    mov byte ptr [edi + 513h], al
write_medium_diamond_hat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L47
    mov byte ptr [edi + 794h], al
write_medium_diamond_hat_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L48
    mov byte ptr [edi + 795h], al
write_medium_diamond_hat_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L49
    mov byte ptr [edi + 0a16h], al
write_medium_diamond_hat_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L50
    mov byte ptr [edi + 0a17h], al
write_medium_diamond_hat_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L51
    mov byte ptr [edi + 0c98h], al
write_medium_diamond_hat_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L52
    mov byte ptr [edi + 0c99h], al
write_medium_diamond_hat_L52:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_hat_L113
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L53
    mov byte ptr [edi + 0a00h], al
write_medium_diamond_hat_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L54
    mov byte ptr [edi + 0a01h], al
write_medium_diamond_hat_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L55
    mov byte ptr [edi + 782h], al
write_medium_diamond_hat_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L56
    mov byte ptr [edi + 783h], al
write_medium_diamond_hat_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L57
    mov byte ptr [edi + 504h], al
write_medium_diamond_hat_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L58
    mov byte ptr [edi + 505h], al
write_medium_diamond_hat_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L59
    mov byte ptr [edi + 286h], al
write_medium_diamond_hat_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L60
    mov byte ptr [edi + 287h], al
write_medium_diamond_hat_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L61
    mov byte ptr [edi + 8], al
write_medium_diamond_hat_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L62
    mov byte ptr [edi + 9], al
write_medium_diamond_hat_L62:
    inc esi
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L63
    mov byte ptr [edi + 10h], al
write_medium_diamond_hat_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L64
    mov byte ptr [edi + 11h], al
write_medium_diamond_hat_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L65
    mov byte ptr [edi + 292h], al
write_medium_diamond_hat_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L66
    mov byte ptr [edi + 293h], al
write_medium_diamond_hat_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L67
    mov byte ptr [edi + 514h], al
write_medium_diamond_hat_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L68
    mov byte ptr [edi + 515h], al
write_medium_diamond_hat_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L69
    mov byte ptr [edi + 796h], al
write_medium_diamond_hat_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L70
    mov byte ptr [edi + 797h], al
write_medium_diamond_hat_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L71
    mov byte ptr [edi + 0a18h], al
write_medium_diamond_hat_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L72
    mov byte ptr [edi + 0a19h], al
write_medium_diamond_hat_L72:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_hat_L113
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L73
    mov byte ptr [edi + 780h], al
write_medium_diamond_hat_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L74
    mov byte ptr [edi + 781h], al
write_medium_diamond_hat_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L75
    mov byte ptr [edi + 502h], al
write_medium_diamond_hat_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L76
    mov byte ptr [edi + 503h], al
write_medium_diamond_hat_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L77
    mov byte ptr [edi + 284h], al
write_medium_diamond_hat_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L78
    mov byte ptr [edi + 285h], al
write_medium_diamond_hat_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L79
    mov byte ptr [edi + 6], al
write_medium_diamond_hat_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L80
    mov byte ptr [edi + 7], al
write_medium_diamond_hat_L80:
    inc esi
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L81
    mov byte ptr [edi + 12h], al
write_medium_diamond_hat_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L82
    mov byte ptr [edi + 13h], al
write_medium_diamond_hat_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L83
    mov byte ptr [edi + 294h], al
write_medium_diamond_hat_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L84
    mov byte ptr [edi + 295h], al
write_medium_diamond_hat_L84:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L85
    mov byte ptr [edi + 516h], al
write_medium_diamond_hat_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L86
    mov byte ptr [edi + 517h], al
write_medium_diamond_hat_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L87
    mov byte ptr [edi + 798h], al
write_medium_diamond_hat_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L88
    mov byte ptr [edi + 799h], al
write_medium_diamond_hat_L88:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_hat_L113
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L89
    mov byte ptr [edi + 500h], al
write_medium_diamond_hat_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L90
    mov byte ptr [edi + 501h], al
write_medium_diamond_hat_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L91
    mov byte ptr [edi + 282h], al
write_medium_diamond_hat_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L92
    mov byte ptr [edi + 283h], al
write_medium_diamond_hat_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L93
    mov byte ptr [edi + 4], al
write_medium_diamond_hat_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L94
    mov byte ptr [edi + 5], al
write_medium_diamond_hat_L94:
    inc esi
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L95
    mov byte ptr [edi + 14h], al
write_medium_diamond_hat_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L96
    mov byte ptr [edi + 15h], al
write_medium_diamond_hat_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L97
    mov byte ptr [edi + 296h], al
write_medium_diamond_hat_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L98
    mov byte ptr [edi + 297h], al
write_medium_diamond_hat_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L99
    mov byte ptr [edi + 518h], al
write_medium_diamond_hat_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L100
    mov byte ptr [edi + 519h], al
write_medium_diamond_hat_L100:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_hat_L113
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L101
    mov byte ptr [edi + 280h], al
write_medium_diamond_hat_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L102
    mov byte ptr [edi + 281h], al
write_medium_diamond_hat_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L103
    mov byte ptr [edi + 2], al
write_medium_diamond_hat_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L104
    mov byte ptr [edi + 3], al
write_medium_diamond_hat_L104:
    inc esi
    add esi, 12h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L105
    mov byte ptr [edi + 16h], al
write_medium_diamond_hat_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L106
    mov byte ptr [edi + 17h], al
write_medium_diamond_hat_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L107
    mov byte ptr [edi + 298h], al
write_medium_diamond_hat_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L108
    mov byte ptr [edi + 299h], al
write_medium_diamond_hat_L108:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_medium_diamond_hat_L113
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L109
    mov byte ptr [edi], al
write_medium_diamond_hat_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L110
    mov byte ptr [edi + 1], al
write_medium_diamond_hat_L110:
    inc esi
    add esi, 16h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L111
    mov byte ptr [edi + 18h], al
write_medium_diamond_hat_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_hat_L112
    mov byte ptr [edi + 19h], al
write_medium_diamond_hat_L112:
    inc esi
write_medium_diamond_hat_L113:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_lefthat
; ════════════════════════════════════════════════════════════
write_medium_diamond_lefthat_:
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
write_medium_diamond_lefthat_L1:
    cmp ebx, ecx
    jle near ptr write_medium_diamond_lefthat_L14
    sub edi, dword ptr [_screen_width]
    push edi
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L2
    mov byte ptr [edi + 280h], al
write_medium_diamond_lefthat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L3
    mov byte ptr [edi + 281h], al
write_medium_diamond_lefthat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L4
    mov byte ptr [edi + 500h], al
write_medium_diamond_lefthat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L5
    mov byte ptr [edi + 501h], al
write_medium_diamond_lefthat_L5:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L6
    mov byte ptr [edi + 780h], al
write_medium_diamond_lefthat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L7
    mov byte ptr [edi + 781h], al
write_medium_diamond_lefthat_L7:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L8
    mov byte ptr [edi + 0a00h], al
write_medium_diamond_lefthat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L9
    mov byte ptr [edi + 0a01h], al
write_medium_diamond_lefthat_L9:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L10
    mov byte ptr [edi + 0c80h], al
write_medium_diamond_lefthat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L11
    mov byte ptr [edi + 0c81h], al
write_medium_diamond_lefthat_L11:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L12
    mov byte ptr [edi + 0f00h], al
write_medium_diamond_lefthat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L13
    mov byte ptr [edi + 0f01h], al
write_medium_diamond_lefthat_L13:
    inc esi
    add edi, 2
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_medium_diamond_lefthat_L1
    popad
    ret
write_medium_diamond_lefthat_L14:
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L15
    mov byte ptr [edi], al
write_medium_diamond_lefthat_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L16
    mov byte ptr [edi + 1], al
write_medium_diamond_lefthat_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L17
    mov byte ptr [edi + 282h], al
write_medium_diamond_lefthat_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L18
    mov byte ptr [edi + 283h], al
write_medium_diamond_lefthat_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L19
    mov byte ptr [edi + 504h], al
write_medium_diamond_lefthat_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L20
    mov byte ptr [edi + 505h], al
write_medium_diamond_lefthat_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L21
    mov byte ptr [edi + 786h], al
write_medium_diamond_lefthat_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L22
    mov byte ptr [edi + 787h], al
write_medium_diamond_lefthat_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L23
    mov byte ptr [edi + 0a08h], al
write_medium_diamond_lefthat_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L24
    mov byte ptr [edi + 0a09h], al
write_medium_diamond_lefthat_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L25
    mov byte ptr [edi + 0c8ah], al
write_medium_diamond_lefthat_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L26
    mov byte ptr [edi + 0c8bh], al
write_medium_diamond_lefthat_L26:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_lefthat_L57
    add esi, 10h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L27
    mov byte ptr [edi + 2], al
write_medium_diamond_lefthat_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L28
    mov byte ptr [edi + 3], al
write_medium_diamond_lefthat_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L29
    mov byte ptr [edi + 284h], al
write_medium_diamond_lefthat_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L30
    mov byte ptr [edi + 285h], al
write_medium_diamond_lefthat_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L31
    mov byte ptr [edi + 506h], al
write_medium_diamond_lefthat_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L32
    mov byte ptr [edi + 507h], al
write_medium_diamond_lefthat_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L33
    mov byte ptr [edi + 788h], al
write_medium_diamond_lefthat_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L34
    mov byte ptr [edi + 789h], al
write_medium_diamond_lefthat_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L35
    mov byte ptr [edi + 0a0ah], al
write_medium_diamond_lefthat_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L36
    mov byte ptr [edi + 0a0bh], al
write_medium_diamond_lefthat_L36:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_lefthat_L57
    add esi, 12h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L37
    mov byte ptr [edi + 4], al
write_medium_diamond_lefthat_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L38
    mov byte ptr [edi + 5], al
write_medium_diamond_lefthat_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L39
    mov byte ptr [edi + 286h], al
write_medium_diamond_lefthat_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L40
    mov byte ptr [edi + 287h], al
write_medium_diamond_lefthat_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L41
    mov byte ptr [edi + 508h], al
write_medium_diamond_lefthat_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L42
    mov byte ptr [edi + 509h], al
write_medium_diamond_lefthat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L43
    mov byte ptr [edi + 78ah], al
write_medium_diamond_lefthat_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L44
    mov byte ptr [edi + 78bh], al
write_medium_diamond_lefthat_L44:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_lefthat_L57
    add esi, 14h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L45
    mov byte ptr [edi + 6], al
write_medium_diamond_lefthat_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L46
    mov byte ptr [edi + 7], al
write_medium_diamond_lefthat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L47
    mov byte ptr [edi + 288h], al
write_medium_diamond_lefthat_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L48
    mov byte ptr [edi + 289h], al
write_medium_diamond_lefthat_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L49
    mov byte ptr [edi + 50ah], al
write_medium_diamond_lefthat_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L50
    mov byte ptr [edi + 50bh], al
write_medium_diamond_lefthat_L50:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_medium_diamond_lefthat_L57
    add esi, 16h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L51
    mov byte ptr [edi + 8], al
write_medium_diamond_lefthat_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L52
    mov byte ptr [edi + 9], al
write_medium_diamond_lefthat_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L53
    mov byte ptr [edi + 28ah], al
write_medium_diamond_lefthat_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L54
    mov byte ptr [edi + 28bh], al
write_medium_diamond_lefthat_L54:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_medium_diamond_lefthat_L57
    add esi, 18h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L55
    mov byte ptr [edi + 0ah], al
write_medium_diamond_lefthat_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthat_L56
    mov byte ptr [edi + 0bh], al
write_medium_diamond_lefthat_L56:
    inc esi
write_medium_diamond_lefthat_L57:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_righthat
; ════════════════════════════════════════════════════════════
write_medium_diamond_righthat_:
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
write_medium_diamond_righthat_L1:
    cmp ebx, ecx
    jle near ptr write_medium_diamond_righthat_L14
    sub edi, dword ptr [_screen_width]
    push edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L2
    mov byte ptr [edi + 0f00h], al
write_medium_diamond_righthat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L3
    mov byte ptr [edi + 0f01h], al
write_medium_diamond_righthat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L4
    mov byte ptr [edi + 0c80h], al
write_medium_diamond_righthat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L5
    mov byte ptr [edi + 0c81h], al
write_medium_diamond_righthat_L5:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L6
    mov byte ptr [edi + 0a00h], al
write_medium_diamond_righthat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L7
    mov byte ptr [edi + 0a01h], al
write_medium_diamond_righthat_L7:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L8
    mov byte ptr [edi + 780h], al
write_medium_diamond_righthat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L9
    mov byte ptr [edi + 781h], al
write_medium_diamond_righthat_L9:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L10
    mov byte ptr [edi + 500h], al
write_medium_diamond_righthat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L11
    mov byte ptr [edi + 501h], al
write_medium_diamond_righthat_L11:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L12
    mov byte ptr [edi + 280h], al
write_medium_diamond_righthat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L13
    mov byte ptr [edi + 281h], al
write_medium_diamond_righthat_L13:
    inc esi
    add edi, 2
    add esi, 0eh
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_medium_diamond_righthat_L1
    popad
    ret
write_medium_diamond_righthat_L14:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L15
    mov byte ptr [edi + 0c80h], al
write_medium_diamond_righthat_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L16
    mov byte ptr [edi + 0c81h], al
write_medium_diamond_righthat_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L17
    mov byte ptr [edi + 0a02h], al
write_medium_diamond_righthat_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L18
    mov byte ptr [edi + 0a03h], al
write_medium_diamond_righthat_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L19
    mov byte ptr [edi + 784h], al
write_medium_diamond_righthat_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L20
    mov byte ptr [edi + 785h], al
write_medium_diamond_righthat_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L21
    mov byte ptr [edi + 506h], al
write_medium_diamond_righthat_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L22
    mov byte ptr [edi + 507h], al
write_medium_diamond_righthat_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L23
    mov byte ptr [edi + 288h], al
write_medium_diamond_righthat_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L24
    mov byte ptr [edi + 289h], al
write_medium_diamond_righthat_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L25
    mov byte ptr [edi + 0ah], al
write_medium_diamond_righthat_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L26
    mov byte ptr [edi + 0bh], al
write_medium_diamond_righthat_L26:
    inc esi
    add esi, 0eh
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_righthat_L57
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L27
    mov byte ptr [edi + 0a00h], al
write_medium_diamond_righthat_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L28
    mov byte ptr [edi + 0a01h], al
write_medium_diamond_righthat_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L29
    mov byte ptr [edi + 782h], al
write_medium_diamond_righthat_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L30
    mov byte ptr [edi + 783h], al
write_medium_diamond_righthat_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L31
    mov byte ptr [edi + 504h], al
write_medium_diamond_righthat_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L32
    mov byte ptr [edi + 505h], al
write_medium_diamond_righthat_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L33
    mov byte ptr [edi + 286h], al
write_medium_diamond_righthat_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L34
    mov byte ptr [edi + 287h], al
write_medium_diamond_righthat_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L35
    mov byte ptr [edi + 8], al
write_medium_diamond_righthat_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L36
    mov byte ptr [edi + 9], al
write_medium_diamond_righthat_L36:
    inc esi
    add esi, 10h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_righthat_L57
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L37
    mov byte ptr [edi + 780h], al
write_medium_diamond_righthat_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L38
    mov byte ptr [edi + 781h], al
write_medium_diamond_righthat_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L39
    mov byte ptr [edi + 502h], al
write_medium_diamond_righthat_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L40
    mov byte ptr [edi + 503h], al
write_medium_diamond_righthat_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L41
    mov byte ptr [edi + 284h], al
write_medium_diamond_righthat_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L42
    mov byte ptr [edi + 285h], al
write_medium_diamond_righthat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L43
    mov byte ptr [edi + 3eh], al
write_medium_diamond_righthat_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L44
    mov byte ptr [edi + 3fh], al
write_medium_diamond_righthat_L44:
    inc esi
    add esi, 12h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_righthat_L57
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L45
    mov byte ptr [edi + 500h], al
write_medium_diamond_righthat_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L46
    mov byte ptr [edi + 501h], al
write_medium_diamond_righthat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L47
    mov byte ptr [edi + 282h], al
write_medium_diamond_righthat_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L48
    mov byte ptr [edi + 283h], al
write_medium_diamond_righthat_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L49
    mov byte ptr [edi + 4], al
write_medium_diamond_righthat_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L50
    mov byte ptr [edi + 5], al
write_medium_diamond_righthat_L50:
    inc esi
    add esi, 14h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_medium_diamond_righthat_L57
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L51
    mov byte ptr [edi + 280h], al
write_medium_diamond_righthat_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L52
    mov byte ptr [edi + 281h], al
write_medium_diamond_righthat_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L53
    mov byte ptr [edi + 2], al
write_medium_diamond_righthat_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L54
    mov byte ptr [edi + 3], al
write_medium_diamond_righthat_L54:
    inc esi
    add esi, 16h
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_medium_diamond_righthat_L57
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L55
    mov byte ptr [edi], al
write_medium_diamond_righthat_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthat_L56
    mov byte ptr [edi + 1], al
write_medium_diamond_righthat_L56:
    inc esi
write_medium_diamond_righthat_L57:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_lefthalfhat
; ════════════════════════════════════════════════════════════
write_medium_diamond_lefthalfhat_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 10], ebx
    mov ebx, edx
    mov ecx, 0
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
write_medium_diamond_lefthalfhat_L1:
    cmp ebx, ecx
    jle near ptr write_medium_diamond_lefthalfhat_L17
    sub edi, dword ptr [_screen_width]
    push edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L2
    mov byte ptr [edi + 0f00h], al
write_medium_diamond_lefthalfhat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L3
    mov byte ptr [edi + 0f01h], al
write_medium_diamond_lefthalfhat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L4
    mov byte ptr [edi + 0c80h], al
write_medium_diamond_lefthalfhat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L5
    mov byte ptr [edi + 0c81h], al
write_medium_diamond_lefthalfhat_L5:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L6
    mov byte ptr [edi + 0a00h], al
write_medium_diamond_lefthalfhat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L7
    mov byte ptr [edi + 0a01h], al
write_medium_diamond_lefthalfhat_L7:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L8
    mov byte ptr [edi + 780h], al
write_medium_diamond_lefthalfhat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L9
    mov byte ptr [edi + 781h], al
write_medium_diamond_lefthalfhat_L9:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L10
    mov byte ptr [edi + 500h], al
write_medium_diamond_lefthalfhat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L11
    mov byte ptr [edi + 501h], al
write_medium_diamond_lefthalfhat_L11:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L12
    mov byte ptr [edi + 280h], al
write_medium_diamond_lefthalfhat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L13
    mov byte ptr [edi + 281h], al
write_medium_diamond_lefthalfhat_L13:
    inc esi
    add edi, 2
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfhat_L16
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L14
    mov byte ptr [edi], al
write_medium_diamond_lefthalfhat_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L15
    mov byte ptr [edi + 1], al
write_medium_diamond_lefthalfhat_L15:
    inc esi
    add edi, 2
write_medium_diamond_lefthalfhat_L16:
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_medium_diamond_lefthalfhat_L1
    popad
    ret
write_medium_diamond_lefthalfhat_L17:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L18
    mov byte ptr [edi + 0c80h], al
write_medium_diamond_lefthalfhat_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L19
    mov byte ptr [edi + 0c81h], al
write_medium_diamond_lefthalfhat_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L20
    mov byte ptr [edi + 0a02h], al
write_medium_diamond_lefthalfhat_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L21
    mov byte ptr [edi + 0a03h], al
write_medium_diamond_lefthalfhat_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L22
    mov byte ptr [edi + 784h], al
write_medium_diamond_lefthalfhat_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L23
    mov byte ptr [edi + 785h], al
write_medium_diamond_lefthalfhat_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L24
    mov byte ptr [edi + 506h], al
write_medium_diamond_lefthalfhat_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L25
    mov byte ptr [edi + 507h], al
write_medium_diamond_lefthalfhat_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L26
    mov byte ptr [edi + 288h], al
write_medium_diamond_lefthalfhat_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L27
    mov byte ptr [edi + 289h], al
write_medium_diamond_lefthalfhat_L27:
    inc esi
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfhat_L30
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L28
    mov byte ptr [edi + 0ah], al
write_medium_diamond_lefthalfhat_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L29
    mov byte ptr [edi + 0bh], al
write_medium_diamond_lefthalfhat_L29:
    inc esi
write_medium_diamond_lefthalfhat_L30:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_lefthalfhat_L65
    add esi, 2
    add esi, dword ptr [_sndinit + 10]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L31
    mov byte ptr [edi + 0a00h], al
write_medium_diamond_lefthalfhat_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L32
    mov byte ptr [edi + 0a01h], al
write_medium_diamond_lefthalfhat_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L33
    mov byte ptr [edi + 782h], al
write_medium_diamond_lefthalfhat_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L34
    mov byte ptr [edi + 783h], al
write_medium_diamond_lefthalfhat_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L35
    mov byte ptr [edi + 504h], al
write_medium_diamond_lefthalfhat_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L36
    mov byte ptr [edi + 505h], al
write_medium_diamond_lefthalfhat_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L37
    mov byte ptr [edi + 286h], al
write_medium_diamond_lefthalfhat_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L38
    mov byte ptr [edi + 287h], al
write_medium_diamond_lefthalfhat_L38:
    inc esi
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfhat_L41
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L39
    mov byte ptr [edi + 8], al
write_medium_diamond_lefthalfhat_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L40
    mov byte ptr [edi + 9], al
write_medium_diamond_lefthalfhat_L40:
    inc esi
write_medium_diamond_lefthalfhat_L41:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_lefthalfhat_L65
    add esi, 4
    add esi, dword ptr [_sndinit + 10]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L42
    mov byte ptr [edi + 780h], al
write_medium_diamond_lefthalfhat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L43
    mov byte ptr [edi + 781h], al
write_medium_diamond_lefthalfhat_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L44
    mov byte ptr [edi + 502h], al
write_medium_diamond_lefthalfhat_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L45
    mov byte ptr [edi + 503h], al
write_medium_diamond_lefthalfhat_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L46
    mov byte ptr [edi + 284h], al
write_medium_diamond_lefthalfhat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L47
    mov byte ptr [edi + 285h], al
write_medium_diamond_lefthalfhat_L47:
    inc esi
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfhat_L50
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L48
    mov byte ptr [edi + 6], al
write_medium_diamond_lefthalfhat_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L49
    mov byte ptr [edi + 7], al
write_medium_diamond_lefthalfhat_L49:
    inc esi
write_medium_diamond_lefthalfhat_L50:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_lefthalfhat_L65
    add esi, 6
    add esi, dword ptr [_sndinit + 10]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L51
    mov byte ptr [edi + 500h], al
write_medium_diamond_lefthalfhat_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L52
    mov byte ptr [edi + 501h], al
write_medium_diamond_lefthalfhat_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L53
    mov byte ptr [edi + 282h], al
write_medium_diamond_lefthalfhat_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L54
    mov byte ptr [edi + 283h], al
write_medium_diamond_lefthalfhat_L54:
    inc esi
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfhat_L57
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L55
    mov byte ptr [edi + 4], al
write_medium_diamond_lefthalfhat_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L56
    mov byte ptr [edi + 5], al
write_medium_diamond_lefthalfhat_L56:
    inc esi
write_medium_diamond_lefthalfhat_L57:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_medium_diamond_lefthalfhat_L65
    add esi, 8
    add esi, dword ptr [_sndinit + 10]
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L58
    mov byte ptr [edi + 280h], al
write_medium_diamond_lefthalfhat_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L59
    mov byte ptr [edi + 281h], al
write_medium_diamond_lefthalfhat_L59:
    inc esi
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfhat_L62
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L60
    mov byte ptr [edi + 2], al
write_medium_diamond_lefthalfhat_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L61
    mov byte ptr [edi + 3], al
write_medium_diamond_lefthalfhat_L61:
    inc esi
write_medium_diamond_lefthalfhat_L62:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_medium_diamond_lefthalfhat_L65
    add esi, 0ah
    add esi, dword ptr [_sndinit + 10]
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfhat_L65
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L63
    mov byte ptr [edi], al
write_medium_diamond_lefthalfhat_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfhat_L64
    mov byte ptr [edi + 1], al
write_medium_diamond_lefthalfhat_L64:
    inc esi
write_medium_diamond_lefthalfhat_L65:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_righthalfhat
; ════════════════════════════════════════════════════════════
write_medium_diamond_righthalfhat_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 10], ebx
    mov ebx, edx
    mov ecx, 0
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfhat_L1
    add edi, 0ch
write_medium_diamond_righthalfhat_L1:
    cmp ebx, ecx
    jle near ptr write_medium_diamond_righthalfhat_L17
    sub edi, dword ptr [_screen_width]
    push edi
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfhat_L4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L2
    mov byte ptr [edi], al
write_medium_diamond_righthalfhat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L3
    mov byte ptr [edi + 1], al
write_medium_diamond_righthalfhat_L3:
    inc esi
    add edi, 2
    sub esi, 2
write_medium_diamond_righthalfhat_L4:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L5
    mov byte ptr [edi + 280h], al
write_medium_diamond_righthalfhat_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L6
    mov byte ptr [edi + 281h], al
write_medium_diamond_righthalfhat_L6:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L7
    mov byte ptr [edi + 500h], al
write_medium_diamond_righthalfhat_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L8
    mov byte ptr [edi + 501h], al
write_medium_diamond_righthalfhat_L8:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L9
    mov byte ptr [edi + 780h], al
write_medium_diamond_righthalfhat_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L10
    mov byte ptr [edi + 781h], al
write_medium_diamond_righthalfhat_L10:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L11
    mov byte ptr [edi + 0a00h], al
write_medium_diamond_righthalfhat_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L12
    mov byte ptr [edi + 0a01h], al
write_medium_diamond_righthalfhat_L12:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L13
    mov byte ptr [edi + 0c80h], al
write_medium_diamond_righthalfhat_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L14
    mov byte ptr [edi + 0c81h], al
write_medium_diamond_righthalfhat_L14:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L15
    mov byte ptr [edi + 0f00h], al
write_medium_diamond_righthalfhat_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L16
    mov byte ptr [edi + 0f01h], al
write_medium_diamond_righthalfhat_L16:
    inc esi
    add edi, 2
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_medium_diamond_righthalfhat_L1
    popad
    ret
write_medium_diamond_righthalfhat_L17:
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfhat_L18
    add edi, 2
write_medium_diamond_righthalfhat_L18:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L19
    mov byte ptr [edi], al
write_medium_diamond_righthalfhat_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L20
    mov byte ptr [edi + 1], al
write_medium_diamond_righthalfhat_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L21
    mov byte ptr [edi + 282h], al
write_medium_diamond_righthalfhat_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L22
    mov byte ptr [edi + 283h], al
write_medium_diamond_righthalfhat_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L23
    mov byte ptr [edi + 504h], al
write_medium_diamond_righthalfhat_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L24
    mov byte ptr [edi + 505h], al
write_medium_diamond_righthalfhat_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L25
    mov byte ptr [edi + 786h], al
write_medium_diamond_righthalfhat_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L26
    mov byte ptr [edi + 787h], al
write_medium_diamond_righthalfhat_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L27
    mov byte ptr [edi + 0a08h], al
write_medium_diamond_righthalfhat_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L28
    mov byte ptr [edi + 0a09h], al
write_medium_diamond_righthalfhat_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L29
    mov byte ptr [edi + 0c8ah], al
write_medium_diamond_righthalfhat_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L30
    mov byte ptr [edi + 0c8bh], al
write_medium_diamond_righthalfhat_L30:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_righthalfhat_L61
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L31
    mov byte ptr [edi + 2], al
write_medium_diamond_righthalfhat_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L32
    mov byte ptr [edi + 3], al
write_medium_diamond_righthalfhat_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L33
    mov byte ptr [edi + 284h], al
write_medium_diamond_righthalfhat_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L34
    mov byte ptr [edi + 285h], al
write_medium_diamond_righthalfhat_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L35
    mov byte ptr [edi + 506h], al
write_medium_diamond_righthalfhat_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L36
    mov byte ptr [edi + 507h], al
write_medium_diamond_righthalfhat_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L37
    mov byte ptr [edi + 788h], al
write_medium_diamond_righthalfhat_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L38
    mov byte ptr [edi + 789h], al
write_medium_diamond_righthalfhat_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L39
    mov byte ptr [edi + 0a0ah], al
write_medium_diamond_righthalfhat_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L40
    mov byte ptr [edi + 0a0bh], al
write_medium_diamond_righthalfhat_L40:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_righthalfhat_L61
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L41
    mov byte ptr [edi + 4], al
write_medium_diamond_righthalfhat_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L42
    mov byte ptr [edi + 5], al
write_medium_diamond_righthalfhat_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L43
    mov byte ptr [edi + 286h], al
write_medium_diamond_righthalfhat_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L44
    mov byte ptr [edi + 287h], al
write_medium_diamond_righthalfhat_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L45
    mov byte ptr [edi + 508h], al
write_medium_diamond_righthalfhat_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L46
    mov byte ptr [edi + 509h], al
write_medium_diamond_righthalfhat_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L47
    mov byte ptr [edi + 78ah], al
write_medium_diamond_righthalfhat_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L48
    mov byte ptr [edi + 78bh], al
write_medium_diamond_righthalfhat_L48:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge near ptr write_medium_diamond_righthalfhat_L61
    add esi, 8
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L49
    mov byte ptr [edi + 6], al
write_medium_diamond_righthalfhat_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L50
    mov byte ptr [edi + 7], al
write_medium_diamond_righthalfhat_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L51
    mov byte ptr [edi + 288h], al
write_medium_diamond_righthalfhat_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L52
    mov byte ptr [edi + 289h], al
write_medium_diamond_righthalfhat_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L53
    mov byte ptr [edi + 50ah], al
write_medium_diamond_righthalfhat_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L54
    mov byte ptr [edi + 50bh], al
write_medium_diamond_righthalfhat_L54:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_medium_diamond_righthalfhat_L61
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L55
    mov byte ptr [edi + 8], al
write_medium_diamond_righthalfhat_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L56
    mov byte ptr [edi + 9], al
write_medium_diamond_righthalfhat_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L57
    mov byte ptr [edi + 28ah], al
write_medium_diamond_righthalfhat_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L58
    mov byte ptr [edi + 28bh], al
write_medium_diamond_righthalfhat_L58:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_medium_diamond_righthalfhat_L61
    add esi, 0ch
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L59
    mov byte ptr [edi + 0ah], al
write_medium_diamond_righthalfhat_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfhat_L60
    mov byte ptr [edi + 0bh], al
write_medium_diamond_righthalfhat_L60:
    inc esi
write_medium_diamond_righthalfhat_L61:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_roof
; ════════════════════════════════════════════════════════════
write_medium_diamond_roof_:
    pushad
    mov esi, eax
    mov ecx, dword ptr [_y_length]
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    add esi, 0ch
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L1
    mov byte ptr [edi + 0ch], al
write_medium_diamond_roof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L2
    mov byte ptr [edi + 0dh], al
write_medium_diamond_roof_L2:
    inc esi
    add esi, 0ch
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_roof_L100
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L3
    mov byte ptr [edi + 28ah], al
write_medium_diamond_roof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L4
    mov byte ptr [edi + 28bh], al
write_medium_diamond_roof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L5
    mov byte ptr [edi + 0ch], al
write_medium_diamond_roof_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L6
    mov byte ptr [edi + 0dh], al
write_medium_diamond_roof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L7
    mov byte ptr [edi + 28eh], al
write_medium_diamond_roof_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L8
    mov byte ptr [edi + 28fh], al
write_medium_diamond_roof_L8:
    inc esi
    add esi, 0ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_roof_L100
    add esi, 8
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L9
    mov byte ptr [edi + 508h], al
write_medium_diamond_roof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L10
    mov byte ptr [edi + 509h], al
write_medium_diamond_roof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L11
    mov byte ptr [edi + 28ah], al
write_medium_diamond_roof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L12
    mov byte ptr [edi + 28bh], al
write_medium_diamond_roof_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L13
    mov byte ptr [edi + 0ch], al
write_medium_diamond_roof_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L14
    mov byte ptr [edi + 0dh], al
write_medium_diamond_roof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L15
    mov byte ptr [edi + 28eh], al
write_medium_diamond_roof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L16
    mov byte ptr [edi + 28fh], al
write_medium_diamond_roof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L17
    mov byte ptr [edi + 510h], al
write_medium_diamond_roof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L18
    mov byte ptr [edi + 511h], al
write_medium_diamond_roof_L18:
    inc esi
    add esi, 8
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_roof_L100
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L19
    mov byte ptr [edi + 786h], al
write_medium_diamond_roof_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L20
    mov byte ptr [edi + 787h], al
write_medium_diamond_roof_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L21
    mov byte ptr [edi + 508h], al
write_medium_diamond_roof_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L22
    mov byte ptr [edi + 509h], al
write_medium_diamond_roof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L23
    mov byte ptr [edi + 28ah], al
write_medium_diamond_roof_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L24
    mov byte ptr [edi + 28bh], al
write_medium_diamond_roof_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L25
    mov byte ptr [edi + 0ch], al
write_medium_diamond_roof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L26
    mov byte ptr [edi + 0dh], al
write_medium_diamond_roof_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L27
    mov byte ptr [edi + 28eh], al
write_medium_diamond_roof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L28
    mov byte ptr [edi + 28fh], al
write_medium_diamond_roof_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L29
    mov byte ptr [edi + 510h], al
write_medium_diamond_roof_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L30
    mov byte ptr [edi + 511h], al
write_medium_diamond_roof_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L31
    mov byte ptr [edi + 792h], al
write_medium_diamond_roof_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L32
    mov byte ptr [edi + 793h], al
write_medium_diamond_roof_L32:
    inc esi
    add esi, 6
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_roof_L100
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L33
    mov byte ptr [edi + 0a04h], al
write_medium_diamond_roof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L34
    mov byte ptr [edi + 0a05h], al
write_medium_diamond_roof_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L35
    mov byte ptr [edi + 786h], al
write_medium_diamond_roof_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L36
    mov byte ptr [edi + 787h], al
write_medium_diamond_roof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L37
    mov byte ptr [edi + 508h], al
write_medium_diamond_roof_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L38
    mov byte ptr [edi + 509h], al
write_medium_diamond_roof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L39
    mov byte ptr [edi + 28ah], al
write_medium_diamond_roof_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L40
    mov byte ptr [edi + 28bh], al
write_medium_diamond_roof_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L41
    mov byte ptr [edi + 0ch], al
write_medium_diamond_roof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L42
    mov byte ptr [edi + 0dh], al
write_medium_diamond_roof_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L43
    mov byte ptr [edi + 28eh], al
write_medium_diamond_roof_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L44
    mov byte ptr [edi + 28fh], al
write_medium_diamond_roof_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L45
    mov byte ptr [edi + 510h], al
write_medium_diamond_roof_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L46
    mov byte ptr [edi + 511h], al
write_medium_diamond_roof_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L47
    mov byte ptr [edi + 792h], al
write_medium_diamond_roof_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L48
    mov byte ptr [edi + 793h], al
write_medium_diamond_roof_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L49
    mov byte ptr [edi + 0a14h], al
write_medium_diamond_roof_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L50
    mov byte ptr [edi + 0a15h], al
write_medium_diamond_roof_L50:
    inc esi
    add esi, 4
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_roof_L100
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L51
    mov byte ptr [edi + 0c82h], al
write_medium_diamond_roof_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L52
    mov byte ptr [edi + 0c83h], al
write_medium_diamond_roof_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L53
    mov byte ptr [edi + 0a04h], al
write_medium_diamond_roof_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L54
    mov byte ptr [edi + 0a05h], al
write_medium_diamond_roof_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L55
    mov byte ptr [edi + 786h], al
write_medium_diamond_roof_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L56
    mov byte ptr [edi + 787h], al
write_medium_diamond_roof_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L57
    mov byte ptr [edi + 508h], al
write_medium_diamond_roof_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L58
    mov byte ptr [edi + 509h], al
write_medium_diamond_roof_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L59
    mov byte ptr [edi + 28ah], al
write_medium_diamond_roof_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L60
    mov byte ptr [edi + 28bh], al
write_medium_diamond_roof_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L61
    mov byte ptr [edi + 0ch], al
write_medium_diamond_roof_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L62
    mov byte ptr [edi + 0dh], al
write_medium_diamond_roof_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L63
    mov byte ptr [edi + 28eh], al
write_medium_diamond_roof_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L64
    mov byte ptr [edi + 28fh], al
write_medium_diamond_roof_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L65
    mov byte ptr [edi + 510h], al
write_medium_diamond_roof_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L66
    mov byte ptr [edi + 511h], al
write_medium_diamond_roof_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L67
    mov byte ptr [edi + 792h], al
write_medium_diamond_roof_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L68
    mov byte ptr [edi + 793h], al
write_medium_diamond_roof_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L69
    mov byte ptr [edi + 0a14h], al
write_medium_diamond_roof_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L70
    mov byte ptr [edi + 0a15h], al
write_medium_diamond_roof_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L71
    mov byte ptr [edi + 0c96h], al
write_medium_diamond_roof_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L72
    mov byte ptr [edi + 0c97h], al
write_medium_diamond_roof_L72:
    inc esi
    add esi, 2
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_roof_L100
write_medium_diamond_roof_L73:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L74
    mov byte ptr [edi + 0f00h], al
write_medium_diamond_roof_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L75
    mov byte ptr [edi + 0f01h], al
write_medium_diamond_roof_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L76
    mov byte ptr [edi + 0c82h], al
write_medium_diamond_roof_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L77
    mov byte ptr [edi + 0c83h], al
write_medium_diamond_roof_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L78
    mov byte ptr [edi + 0a04h], al
write_medium_diamond_roof_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L79
    mov byte ptr [edi + 0a05h], al
write_medium_diamond_roof_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L80
    mov byte ptr [edi + 786h], al
write_medium_diamond_roof_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L81
    mov byte ptr [edi + 787h], al
write_medium_diamond_roof_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L82
    mov byte ptr [edi + 508h], al
write_medium_diamond_roof_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L83
    mov byte ptr [edi + 509h], al
write_medium_diamond_roof_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L84
    mov byte ptr [edi + 28ah], al
write_medium_diamond_roof_L84:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L85
    mov byte ptr [edi + 28bh], al
write_medium_diamond_roof_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L86
    mov byte ptr [edi + 0ch], al
write_medium_diamond_roof_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L87
    mov byte ptr [edi + 0dh], al
write_medium_diamond_roof_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L88
    mov byte ptr [edi + 28eh], al
write_medium_diamond_roof_L88:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L89
    mov byte ptr [edi + 28fh], al
write_medium_diamond_roof_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L90
    mov byte ptr [edi + 510h], al
write_medium_diamond_roof_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L91
    mov byte ptr [edi + 511h], al
write_medium_diamond_roof_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L92
    mov byte ptr [edi + 792h], al
write_medium_diamond_roof_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L93
    mov byte ptr [edi + 793h], al
write_medium_diamond_roof_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L94
    mov byte ptr [edi + 0a14h], al
write_medium_diamond_roof_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L95
    mov byte ptr [edi + 0a15h], al
write_medium_diamond_roof_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L96
    mov byte ptr [edi + 0c96h], al
write_medium_diamond_roof_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L97
    mov byte ptr [edi + 0c97h], al
write_medium_diamond_roof_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L98
    mov byte ptr [edi + 0f18h], al
write_medium_diamond_roof_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_roof_L99
    mov byte ptr [edi + 0f19h], al
write_medium_diamond_roof_L99:
    inc esi
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_medium_diamond_roof_L73
write_medium_diamond_roof_L100:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_leftroof
; ════════════════════════════════════════════════════════════
write_medium_diamond_leftroof_:
    pushad
    mov esi, eax
    mov ecx, dword ptr [_y_length]
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    add esi, 1ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_leftroof_L44
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L1
    mov byte ptr [edi + 280h], al
write_medium_diamond_leftroof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L2
    mov byte ptr [edi + 281h], al
write_medium_diamond_leftroof_L2:
    inc esi
    add esi, 0ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_leftroof_L44
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L3
    mov byte ptr [edi + 280h], al
write_medium_diamond_leftroof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L4
    mov byte ptr [edi + 281h], al
write_medium_diamond_leftroof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L5
    mov byte ptr [edi + 502h], al
write_medium_diamond_leftroof_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L6
    mov byte ptr [edi + 503h], al
write_medium_diamond_leftroof_L6:
    inc esi
    add esi, 8
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_leftroof_L44
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L7
    mov byte ptr [edi + 280h], al
write_medium_diamond_leftroof_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L8
    mov byte ptr [edi + 281h], al
write_medium_diamond_leftroof_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L9
    mov byte ptr [edi + 502h], al
write_medium_diamond_leftroof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L10
    mov byte ptr [edi + 503h], al
write_medium_diamond_leftroof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L11
    mov byte ptr [edi + 784h], al
write_medium_diamond_leftroof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L12
    mov byte ptr [edi + 785h], al
write_medium_diamond_leftroof_L12:
    inc esi
    add esi, 6
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_leftroof_L44
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L13
    mov byte ptr [edi + 280h], al
write_medium_diamond_leftroof_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L14
    mov byte ptr [edi + 281h], al
write_medium_diamond_leftroof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L15
    mov byte ptr [edi + 502h], al
write_medium_diamond_leftroof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L16
    mov byte ptr [edi + 503h], al
write_medium_diamond_leftroof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L17
    mov byte ptr [edi + 784h], al
write_medium_diamond_leftroof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L18
    mov byte ptr [edi + 785h], al
write_medium_diamond_leftroof_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L19
    mov byte ptr [edi + 0a06h], al
write_medium_diamond_leftroof_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L20
    mov byte ptr [edi + 0a07h], al
write_medium_diamond_leftroof_L20:
    inc esi
    add esi, 4
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_leftroof_L44
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L21
    mov byte ptr [edi + 280h], al
write_medium_diamond_leftroof_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L22
    mov byte ptr [edi + 281h], al
write_medium_diamond_leftroof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L23
    mov byte ptr [edi + 502h], al
write_medium_diamond_leftroof_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L24
    mov byte ptr [edi + 503h], al
write_medium_diamond_leftroof_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L25
    mov byte ptr [edi + 784h], al
write_medium_diamond_leftroof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L26
    mov byte ptr [edi + 785h], al
write_medium_diamond_leftroof_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L27
    mov byte ptr [edi + 0a06h], al
write_medium_diamond_leftroof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L28
    mov byte ptr [edi + 0a07h], al
write_medium_diamond_leftroof_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L29
    mov byte ptr [edi + 0c88h], al
write_medium_diamond_leftroof_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L30
    mov byte ptr [edi + 0c89h], al
write_medium_diamond_leftroof_L30:
    inc esi
    add esi, 2
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_leftroof_L44
write_medium_diamond_leftroof_L31:
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L32
    mov byte ptr [edi + 280h], al
write_medium_diamond_leftroof_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L33
    mov byte ptr [edi + 281h], al
write_medium_diamond_leftroof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L34
    mov byte ptr [edi + 502h], al
write_medium_diamond_leftroof_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L35
    mov byte ptr [edi + 503h], al
write_medium_diamond_leftroof_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L36
    mov byte ptr [edi + 784h], al
write_medium_diamond_leftroof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L37
    mov byte ptr [edi + 785h], al
write_medium_diamond_leftroof_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L38
    mov byte ptr [edi + 0a06h], al
write_medium_diamond_leftroof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L39
    mov byte ptr [edi + 0a07h], al
write_medium_diamond_leftroof_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L40
    mov byte ptr [edi + 0c88h], al
write_medium_diamond_leftroof_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L41
    mov byte ptr [edi + 0c89h], al
write_medium_diamond_leftroof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L42
    mov byte ptr [edi + 0f0ah], al
write_medium_diamond_leftroof_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_leftroof_L43
    mov byte ptr [edi + 0f0bh], al
write_medium_diamond_leftroof_L43:
    inc esi
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_medium_diamond_leftroof_L31
write_medium_diamond_leftroof_L44:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_rightroof
; ════════════════════════════════════════════════════════════
write_medium_diamond_rightroof_:
    pushad
    mov esi, eax
    mov ecx, dword ptr [_y_length]
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    add esi, 1ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_rightroof_L44
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L1
    mov byte ptr [edi + 28ah], al
write_medium_diamond_rightroof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L2
    mov byte ptr [edi + 28bh], al
write_medium_diamond_rightroof_L2:
    inc esi
    add esi, 0eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_rightroof_L44
    add esi, 8
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L3
    mov byte ptr [edi + 508h], al
write_medium_diamond_rightroof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L4
    mov byte ptr [edi + 509h], al
write_medium_diamond_rightroof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L5
    mov byte ptr [edi + 28ah], al
write_medium_diamond_rightroof_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L6
    mov byte ptr [edi + 28bh], al
write_medium_diamond_rightroof_L6:
    inc esi
    add esi, 0eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_rightroof_L44
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L7
    mov byte ptr [edi + 786h], al
write_medium_diamond_rightroof_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L8
    mov byte ptr [edi + 787h], al
write_medium_diamond_rightroof_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L9
    mov byte ptr [edi + 508h], al
write_medium_diamond_rightroof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L10
    mov byte ptr [edi + 509h], al
write_medium_diamond_rightroof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L11
    mov byte ptr [edi + 28ah], al
write_medium_diamond_rightroof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L12
    mov byte ptr [edi + 28bh], al
write_medium_diamond_rightroof_L12:
    inc esi
    add esi, 0eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_rightroof_L44
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L13
    mov byte ptr [edi + 0a04h], al
write_medium_diamond_rightroof_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L14
    mov byte ptr [edi + 0a05h], al
write_medium_diamond_rightroof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L15
    mov byte ptr [edi + 786h], al
write_medium_diamond_rightroof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L16
    mov byte ptr [edi + 787h], al
write_medium_diamond_rightroof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L17
    mov byte ptr [edi + 508h], al
write_medium_diamond_rightroof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L18
    mov byte ptr [edi + 509h], al
write_medium_diamond_rightroof_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L19
    mov byte ptr [edi + 28ah], al
write_medium_diamond_rightroof_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L20
    mov byte ptr [edi + 28bh], al
write_medium_diamond_rightroof_L20:
    inc esi
    add esi, 0eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_rightroof_L44
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L21
    mov byte ptr [edi + 0c82h], al
write_medium_diamond_rightroof_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L22
    mov byte ptr [edi + 0c83h], al
write_medium_diamond_rightroof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L23
    mov byte ptr [edi + 0a04h], al
write_medium_diamond_rightroof_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L24
    mov byte ptr [edi + 0a05h], al
write_medium_diamond_rightroof_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L25
    mov byte ptr [edi + 786h], al
write_medium_diamond_rightroof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L26
    mov byte ptr [edi + 787h], al
write_medium_diamond_rightroof_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L27
    mov byte ptr [edi + 508h], al
write_medium_diamond_rightroof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L28
    mov byte ptr [edi + 509h], al
write_medium_diamond_rightroof_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L29
    mov byte ptr [edi + 28ah], al
write_medium_diamond_rightroof_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L30
    mov byte ptr [edi + 28bh], al
write_medium_diamond_rightroof_L30:
    inc esi
    add esi, 0eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_rightroof_L44
write_medium_diamond_rightroof_L31:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L32
    mov byte ptr [edi + 0f00h], al
write_medium_diamond_rightroof_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L33
    mov byte ptr [edi + 0f01h], al
write_medium_diamond_rightroof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L34
    mov byte ptr [edi + 0c82h], al
write_medium_diamond_rightroof_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L35
    mov byte ptr [edi + 0c83h], al
write_medium_diamond_rightroof_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L36
    mov byte ptr [edi + 0a04h], al
write_medium_diamond_rightroof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L37
    mov byte ptr [edi + 0a05h], al
write_medium_diamond_rightroof_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L38
    mov byte ptr [edi + 786h], al
write_medium_diamond_rightroof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L39
    mov byte ptr [edi + 787h], al
write_medium_diamond_rightroof_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L40
    mov byte ptr [edi + 508h], al
write_medium_diamond_rightroof_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L41
    mov byte ptr [edi + 509h], al
write_medium_diamond_rightroof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L42
    mov byte ptr [edi + 28ah], al
write_medium_diamond_rightroof_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_rightroof_L43
    mov byte ptr [edi + 28bh], al
write_medium_diamond_rightroof_L43:
    inc esi
    add esi, 0eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_medium_diamond_rightroof_L31
write_medium_diamond_rightroof_L44:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_righthalfroof
; ════════════════════════════════════════════════════════════
write_medium_diamond_righthalfroof_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 10], edx
    mov ecx, dword ptr [_y_length]
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp dword ptr [_sndinit + 10], 2
    jne write_medium_diamond_righthalfroof_L1
    sub edi, 2
write_medium_diamond_righthalfroof_L1:
    cmp dword ptr [_sndinit + 10], 0
    jne write_medium_diamond_righthalfroof_L2
    add edi, 0ch
write_medium_diamond_righthalfroof_L2:
    add esi, 0eh
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfroof_L5
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L3
    mov byte ptr [edi], al
write_medium_diamond_righthalfroof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L4
    mov byte ptr [edi + 1], al
write_medium_diamond_righthalfroof_L4:
    inc esi
write_medium_diamond_righthalfroof_L5:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_righthalfroof_L67
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfroof_L8
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L6
    mov byte ptr [edi], al
write_medium_diamond_righthalfroof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L7
    mov byte ptr [edi + 1], al
write_medium_diamond_righthalfroof_L7:
    inc esi
write_medium_diamond_righthalfroof_L8:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L9
    mov byte ptr [edi + 282h], al
write_medium_diamond_righthalfroof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L10
    mov byte ptr [edi + 283h], al
write_medium_diamond_righthalfroof_L10:
    inc esi
    add esi, 0ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_righthalfroof_L67
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfroof_L13
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L11
    mov byte ptr [edi], al
write_medium_diamond_righthalfroof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L12
    mov byte ptr [edi + 1], al
write_medium_diamond_righthalfroof_L12:
    inc esi
write_medium_diamond_righthalfroof_L13:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L14
    mov byte ptr [edi + 282h], al
write_medium_diamond_righthalfroof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L15
    mov byte ptr [edi + 283h], al
write_medium_diamond_righthalfroof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L16
    mov byte ptr [edi + 504h], al
write_medium_diamond_righthalfroof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L17
    mov byte ptr [edi + 505h], al
write_medium_diamond_righthalfroof_L17:
    inc esi
    add esi, 8
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_righthalfroof_L67
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfroof_L20
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L18
    mov byte ptr [edi], al
write_medium_diamond_righthalfroof_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L19
    mov byte ptr [edi + 1], al
write_medium_diamond_righthalfroof_L19:
    inc esi
write_medium_diamond_righthalfroof_L20:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L21
    mov byte ptr [edi + 282h], al
write_medium_diamond_righthalfroof_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L22
    mov byte ptr [edi + 283h], al
write_medium_diamond_righthalfroof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L23
    mov byte ptr [edi + 504h], al
write_medium_diamond_righthalfroof_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L24
    mov byte ptr [edi + 505h], al
write_medium_diamond_righthalfroof_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L25
    mov byte ptr [edi + 786h], al
write_medium_diamond_righthalfroof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L26
    mov byte ptr [edi + 787h], al
write_medium_diamond_righthalfroof_L26:
    inc esi
    add esi, 6
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_righthalfroof_L67
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfroof_L29
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L27
    mov byte ptr [edi], al
write_medium_diamond_righthalfroof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L28
    mov byte ptr [edi + 1], al
write_medium_diamond_righthalfroof_L28:
    inc esi
write_medium_diamond_righthalfroof_L29:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L30
    mov byte ptr [edi + 282h], al
write_medium_diamond_righthalfroof_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L31
    mov byte ptr [edi + 283h], al
write_medium_diamond_righthalfroof_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L32
    mov byte ptr [edi + 504h], al
write_medium_diamond_righthalfroof_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L33
    mov byte ptr [edi + 505h], al
write_medium_diamond_righthalfroof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L34
    mov byte ptr [edi + 786h], al
write_medium_diamond_righthalfroof_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L35
    mov byte ptr [edi + 787h], al
write_medium_diamond_righthalfroof_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L36
    mov byte ptr [edi + 0a08h], al
write_medium_diamond_righthalfroof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L37
    mov byte ptr [edi + 0a09h], al
write_medium_diamond_righthalfroof_L37:
    inc esi
    add esi, 4
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_righthalfroof_L67
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfroof_L40
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L38
    mov byte ptr [edi], al
write_medium_diamond_righthalfroof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L39
    mov byte ptr [edi + 1], al
write_medium_diamond_righthalfroof_L39:
    inc esi
write_medium_diamond_righthalfroof_L40:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L41
    mov byte ptr [edi + 282h], al
write_medium_diamond_righthalfroof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L42
    mov byte ptr [edi + 283h], al
write_medium_diamond_righthalfroof_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L43
    mov byte ptr [edi + 504h], al
write_medium_diamond_righthalfroof_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L44
    mov byte ptr [edi + 505h], al
write_medium_diamond_righthalfroof_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L45
    mov byte ptr [edi + 786h], al
write_medium_diamond_righthalfroof_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L46
    mov byte ptr [edi + 787h], al
write_medium_diamond_righthalfroof_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L47
    mov byte ptr [edi + 0a08h], al
write_medium_diamond_righthalfroof_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L48
    mov byte ptr [edi + 0a09h], al
write_medium_diamond_righthalfroof_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L49
    mov byte ptr [edi + 0c8ah], al
write_medium_diamond_righthalfroof_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L50
    mov byte ptr [edi + 0c8bh], al
write_medium_diamond_righthalfroof_L50:
    inc esi
    add esi, 2
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_righthalfroof_L67
write_medium_diamond_righthalfroof_L51:
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_righthalfroof_L54
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L52
    mov byte ptr [edi], al
write_medium_diamond_righthalfroof_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L53
    mov byte ptr [edi + 1], al
write_medium_diamond_righthalfroof_L53:
    inc esi
write_medium_diamond_righthalfroof_L54:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L55
    mov byte ptr [edi + 282h], al
write_medium_diamond_righthalfroof_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L56
    mov byte ptr [edi + 283h], al
write_medium_diamond_righthalfroof_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L57
    mov byte ptr [edi + 504h], al
write_medium_diamond_righthalfroof_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L58
    mov byte ptr [edi + 505h], al
write_medium_diamond_righthalfroof_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L59
    mov byte ptr [edi + 786h], al
write_medium_diamond_righthalfroof_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L60
    mov byte ptr [edi + 787h], al
write_medium_diamond_righthalfroof_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L61
    mov byte ptr [edi + 0a08h], al
write_medium_diamond_righthalfroof_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L62
    mov byte ptr [edi + 0a09h], al
write_medium_diamond_righthalfroof_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L63
    mov byte ptr [edi + 0c8ah], al
write_medium_diamond_righthalfroof_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L64
    mov byte ptr [edi + 0c8bh], al
write_medium_diamond_righthalfroof_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L65
    mov byte ptr [edi + 0f0ch], al
write_medium_diamond_righthalfroof_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_righthalfroof_L66
    mov byte ptr [edi + 0f0dh], al
write_medium_diamond_righthalfroof_L66:
    inc esi
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_medium_diamond_righthalfroof_L51
write_medium_diamond_righthalfroof_L67:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_medium_diamond_lefthalfroof
; ════════════════════════════════════════════════════════════
write_medium_diamond_lefthalfroof_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 10], edx
    mov ecx, dword ptr [_y_length]
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    add esi, 0eh
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfroof_L3
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L1
    mov byte ptr [edi + 0ch], al
write_medium_diamond_lefthalfroof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L2
    mov byte ptr [edi + 0dh], al
write_medium_diamond_lefthalfroof_L2:
    inc esi
write_medium_diamond_lefthalfroof_L3:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_lefthalfroof_L65
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L4
    mov byte ptr [edi + 28ah], al
write_medium_diamond_lefthalfroof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L5
    mov byte ptr [edi + 28bh], al
write_medium_diamond_lefthalfroof_L5:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfroof_L8
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L6
    mov byte ptr [edi + 0ch], al
write_medium_diamond_lefthalfroof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L7
    mov byte ptr [edi + 0dh], al
write_medium_diamond_lefthalfroof_L7:
    inc esi
write_medium_diamond_lefthalfroof_L8:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_lefthalfroof_L65
    add esi, 8
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L9
    mov byte ptr [edi + 508h], al
write_medium_diamond_lefthalfroof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L10
    mov byte ptr [edi + 509h], al
write_medium_diamond_lefthalfroof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L11
    mov byte ptr [edi + 28ah], al
write_medium_diamond_lefthalfroof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L12
    mov byte ptr [edi + 28bh], al
write_medium_diamond_lefthalfroof_L12:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfroof_L15
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L13
    mov byte ptr [edi + 0ch], al
write_medium_diamond_lefthalfroof_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L14
    mov byte ptr [edi + 0dh], al
write_medium_diamond_lefthalfroof_L14:
    inc esi
write_medium_diamond_lefthalfroof_L15:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_lefthalfroof_L65
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L16
    mov byte ptr [edi + 786h], al
write_medium_diamond_lefthalfroof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L17
    mov byte ptr [edi + 787h], al
write_medium_diamond_lefthalfroof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L18
    mov byte ptr [edi + 508h], al
write_medium_diamond_lefthalfroof_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L19
    mov byte ptr [edi + 509h], al
write_medium_diamond_lefthalfroof_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L20
    mov byte ptr [edi + 28ah], al
write_medium_diamond_lefthalfroof_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L21
    mov byte ptr [edi + 28bh], al
write_medium_diamond_lefthalfroof_L21:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfroof_L24
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L22
    mov byte ptr [edi + 0ch], al
write_medium_diamond_lefthalfroof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L23
    mov byte ptr [edi + 0dh], al
write_medium_diamond_lefthalfroof_L23:
    inc esi
write_medium_diamond_lefthalfroof_L24:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_lefthalfroof_L65
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L25
    mov byte ptr [edi + 0a04h], al
write_medium_diamond_lefthalfroof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L26
    mov byte ptr [edi + 0a05h], al
write_medium_diamond_lefthalfroof_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L27
    mov byte ptr [edi + 786h], al
write_medium_diamond_lefthalfroof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L28
    mov byte ptr [edi + 787h], al
write_medium_diamond_lefthalfroof_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L29
    mov byte ptr [edi + 508h], al
write_medium_diamond_lefthalfroof_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L30
    mov byte ptr [edi + 509h], al
write_medium_diamond_lefthalfroof_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L31
    mov byte ptr [edi + 28ah], al
write_medium_diamond_lefthalfroof_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L32
    mov byte ptr [edi + 28bh], al
write_medium_diamond_lefthalfroof_L32:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfroof_L35
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L33
    mov byte ptr [edi + 0ch], al
write_medium_diamond_lefthalfroof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L34
    mov byte ptr [edi + 0dh], al
write_medium_diamond_lefthalfroof_L34:
    inc esi
write_medium_diamond_lefthalfroof_L35:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_lefthalfroof_L65
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L36
    mov byte ptr [edi + 0c82h], al
write_medium_diamond_lefthalfroof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L37
    mov byte ptr [edi + 0c83h], al
write_medium_diamond_lefthalfroof_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L38
    mov byte ptr [edi + 0a04h], al
write_medium_diamond_lefthalfroof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L39
    mov byte ptr [edi + 0a05h], al
write_medium_diamond_lefthalfroof_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L40
    mov byte ptr [edi + 786h], al
write_medium_diamond_lefthalfroof_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L41
    mov byte ptr [edi + 787h], al
write_medium_diamond_lefthalfroof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L42
    mov byte ptr [edi + 508h], al
write_medium_diamond_lefthalfroof_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L43
    mov byte ptr [edi + 509h], al
write_medium_diamond_lefthalfroof_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L44
    mov byte ptr [edi + 28ah], al
write_medium_diamond_lefthalfroof_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L45
    mov byte ptr [edi + 28bh], al
write_medium_diamond_lefthalfroof_L45:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfroof_L48
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L46
    mov byte ptr [edi + 0ch], al
write_medium_diamond_lefthalfroof_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L47
    mov byte ptr [edi + 0dh], al
write_medium_diamond_lefthalfroof_L47:
    inc esi
write_medium_diamond_lefthalfroof_L48:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_medium_diamond_lefthalfroof_L65
write_medium_diamond_lefthalfroof_L49:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L50
    mov byte ptr [edi + 0f00h], al
write_medium_diamond_lefthalfroof_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L51
    mov byte ptr [edi + 0f01h], al
write_medium_diamond_lefthalfroof_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L52
    mov byte ptr [edi + 0c82h], al
write_medium_diamond_lefthalfroof_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L53
    mov byte ptr [edi + 0c83h], al
write_medium_diamond_lefthalfroof_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L54
    mov byte ptr [edi + 0a04h], al
write_medium_diamond_lefthalfroof_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L55
    mov byte ptr [edi + 0a05h], al
write_medium_diamond_lefthalfroof_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L56
    mov byte ptr [edi + 786h], al
write_medium_diamond_lefthalfroof_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L57
    mov byte ptr [edi + 787h], al
write_medium_diamond_lefthalfroof_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L58
    mov byte ptr [edi + 508h], al
write_medium_diamond_lefthalfroof_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L59
    mov byte ptr [edi + 509h], al
write_medium_diamond_lefthalfroof_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L60
    mov byte ptr [edi + 28ah], al
write_medium_diamond_lefthalfroof_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L61
    mov byte ptr [edi + 28bh], al
write_medium_diamond_lefthalfroof_L61:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 10], 2
    je write_medium_diamond_lefthalfroof_L64
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L62
    mov byte ptr [edi + 0ch], al
write_medium_diamond_lefthalfroof_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_medium_diamond_lefthalfroof_L63
    mov byte ptr [edi + 0dh], al
write_medium_diamond_lefthalfroof_L63:
    inc esi
write_medium_diamond_lefthalfroof_L64:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_medium_diamond_lefthalfroof_L49
write_medium_diamond_lefthalfroof_L65:
    popad
    ret

_TEXT ENDS
END
