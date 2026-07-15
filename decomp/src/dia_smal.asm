.386p
.MODEL FLAT

PUBLIC place_i_small_diamond_
PUBLIC place_i_small_diamond_lefthalf_
PUBLIC place_i_small_diamond_righthalf_
PUBLIC write_small_diamond_hat_
PUBLIC write_small_diamond_lefthat_
PUBLIC write_small_diamond_righthat_
PUBLIC write_small_diamond_lefthalfhat_
PUBLIC write_small_diamond_righthalfhat_
PUBLIC write_small_diamond_roof_
PUBLIC write_small_diamond_leftroof_
PUBLIC write_small_diamond_rightroof_
PUBLIC write_small_diamond_righthalfroof_
PUBLIC write_small_diamond_lefthalfroof_

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
; place_i_small_diamond
; ════════════════════════════════════════════════════════════
place_i_small_diamond_:
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
    jne place_i_small_diamond_L1
    jmp place_i_small_diamond_L2
place_i_small_diamond_L1:
    mov ax, word ptr [esi]
    mov word ptr [edi + 4], ax
    mov eax, dword ptr [esi + 2]
    mov dword ptr [edi + 282h], eax
    mov ax, word ptr [esi + 6]
    mov word ptr [edi + 286h], ax
    mov eax, dword ptr [esi + 8]
    mov dword ptr [edi + 500h], eax
    mov eax, dword ptr [esi + 0ch]
    mov dword ptr [edi + 504h], eax
    mov ax, word ptr [esi + 10h]
    mov word ptr [edi + 508h], ax
    cmp ebx, 1
    jne place_i_small_diamond_L2
    jmp place_i_small_diamond_L3
place_i_small_diamond_L2:
    mov eax, dword ptr [esi + 12h]
    mov dword ptr [edi + 780h], eax
    mov eax, dword ptr [esi + 16h]
    mov dword ptr [edi + 784h], eax
    mov ax, word ptr [esi + 1ah]
    mov word ptr [edi + 788h], ax
    mov eax, dword ptr [esi + 1ch]
    mov dword ptr [edi + 0a02h], eax
    mov ax, word ptr [esi + 20h]
    mov word ptr [edi + 0a06h], ax
    mov ax, word ptr [esi + 22h]
    mov word ptr [edi + 0c84h], ax
place_i_small_diamond_L3:
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_i_small_diamond_lefthalf
; ════════════════════════════════════════════════════════════
place_i_small_diamond_lefthalf_:
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
    mov ax, word ptr [esi + 6]
    mov word ptr [edi + 280h], ax
    mov eax, dword ptr [esi + 0eh]
    mov dword ptr [edi + 500h], eax
    mov eax, dword ptr [esi + 18h]
    mov dword ptr [edi + 780h], eax
    mov ax, word ptr [esi + 20h]
    mov word ptr [edi + 0a00h], ax
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_i_small_diamond_righthalf
; ════════════════════════════════════════════════════════════
place_i_small_diamond_righthalf_:
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
    mov ax, word ptr [esi + 2]
    mov word ptr [edi + 282h], ax
    mov eax, dword ptr [esi + 8]
    mov dword ptr [edi + 500h], eax
    mov eax, dword ptr [esi + 12h]
    mov dword ptr [edi + 780h], eax
    mov ax, word ptr [esi + 1ch]
    mov word ptr [edi + 0a02h], ax
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_hat
; ════════════════════════════════════════════════════════════
write_small_diamond_hat_:
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
write_small_diamond_hat_L1:
    cmp ebx, ecx
    jle near ptr write_small_diamond_hat_L12
    sub edi, dword ptr [_screen_width]
    push edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L2
    mov byte ptr [edi + 500h], al
write_small_diamond_hat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L3
    mov byte ptr [edi + 501h], al
write_small_diamond_hat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L4
    mov byte ptr [edi + 280h], al
write_small_diamond_hat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L5
    mov byte ptr [edi + 281h], al
write_small_diamond_hat_L5:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L6
    mov byte ptr [edi], al
write_small_diamond_hat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L7
    mov byte ptr [edi + 1], al
write_small_diamond_hat_L7:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L8
    mov byte ptr [edi + 280h], al
write_small_diamond_hat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L9
    mov byte ptr [edi + 281h], al
write_small_diamond_hat_L9:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L10
    mov byte ptr [edi + 500h], al
write_small_diamond_hat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L11
    mov byte ptr [edi + 501h], al
write_small_diamond_hat_L11:
    inc esi
    add edi, 2
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl near ptr write_small_diamond_hat_L1
    popad
    ret
write_small_diamond_hat_L12:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L13
    mov byte ptr [edi + 280h], al
write_small_diamond_hat_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L14
    mov byte ptr [edi + 281h], al
write_small_diamond_hat_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L15
    mov byte ptr [edi + 2], al
write_small_diamond_hat_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L16
    mov byte ptr [edi + 3], al
write_small_diamond_hat_L16:
    inc esi
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L17
    mov byte ptr [edi + 6], al
write_small_diamond_hat_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L18
    mov byte ptr [edi + 7], al
write_small_diamond_hat_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L19
    mov byte ptr [edi + 288h], al
write_small_diamond_hat_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L20
    mov byte ptr [edi + 289h], al
write_small_diamond_hat_L20:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_small_diamond_hat_L25
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L21
    mov byte ptr [edi], al
write_small_diamond_hat_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L22
    mov byte ptr [edi + 1], al
write_small_diamond_hat_L22:
    inc esi
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L23
    mov byte ptr [edi + 8], al
write_small_diamond_hat_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_hat_L24
    mov byte ptr [edi + 9], al
write_small_diamond_hat_L24:
    inc esi
write_small_diamond_hat_L25:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_lefthat
; ════════════════════════════════════════════════════════════
write_small_diamond_lefthat_:
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
write_small_diamond_lefthat_L1:
    cmp ebx, ecx
    jle write_small_diamond_lefthat_L6
    sub edi, dword ptr [_screen_width]
    push edi
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L2
    mov byte ptr [edi + 280h], al
write_small_diamond_lefthat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L3
    mov byte ptr [edi + 281h], al
write_small_diamond_lefthat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L4
    mov byte ptr [edi + 500h], al
write_small_diamond_lefthat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L5
    mov byte ptr [edi + 501h], al
write_small_diamond_lefthat_L5:
    inc esi
    add edi, 2
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl write_small_diamond_lefthat_L1
    popad
    ret
write_small_diamond_lefthat_L6:
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L7
    mov byte ptr [edi], al
write_small_diamond_lefthat_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L8
    mov byte ptr [edi + 1], al
write_small_diamond_lefthat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L9
    mov byte ptr [edi + 282h], al
write_small_diamond_lefthat_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L10
    mov byte ptr [edi + 283h], al
write_small_diamond_lefthat_L10:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_small_diamond_lefthat_L13
    add esi, 8
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L11
    mov byte ptr [edi + 2], al
write_small_diamond_lefthat_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthat_L12
    mov byte ptr [edi + 3], al
write_small_diamond_lefthat_L12:
    inc esi
write_small_diamond_lefthat_L13:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_righthat
; ════════════════════════════════════════════════════════════
write_small_diamond_righthat_:
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
write_small_diamond_righthat_L1:
    cmp ebx, ecx
    jle write_small_diamond_righthat_L6
    sub edi, dword ptr [_screen_width]
    push edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L2
    mov byte ptr [edi + 500h], al
write_small_diamond_righthat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L3
    mov byte ptr [edi + 501h], al
write_small_diamond_righthat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L4
    mov byte ptr [edi + 280h], al
write_small_diamond_righthat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L5
    mov byte ptr [edi + 281h], al
write_small_diamond_righthat_L5:
    inc esi
    add edi, 2
    add esi, 6
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl write_small_diamond_righthat_L1
    popad
    ret
write_small_diamond_righthat_L6:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L7
    mov byte ptr [edi + 280h], al
write_small_diamond_righthat_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L8
    mov byte ptr [edi + 281h], al
write_small_diamond_righthat_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L9
    mov byte ptr [edi + 2], al
write_small_diamond_righthat_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L10
    mov byte ptr [edi + 3], al
write_small_diamond_righthat_L10:
    inc esi
    add esi, 6
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_small_diamond_righthat_L13
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L11
    mov byte ptr [edi], al
write_small_diamond_righthat_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthat_L12
    mov byte ptr [edi + 1], al
write_small_diamond_righthat_L12:
    inc esi
write_small_diamond_righthat_L13:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_lefthalfhat
; ════════════════════════════════════════════════════════════
write_small_diamond_lefthalfhat_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 14], ebx
    mov ebx, edx
    mov ecx, 0
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
write_small_diamond_lefthalfhat_L1:
    cmp ebx, ecx
    jle write_small_diamond_lefthalfhat_L9
    sub edi, dword ptr [_screen_width]
    push edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L2
    mov byte ptr [edi + 500h], al
write_small_diamond_lefthalfhat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L3
    mov byte ptr [edi + 501h], al
write_small_diamond_lefthalfhat_L3:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L4
    mov byte ptr [edi + 280h], al
write_small_diamond_lefthalfhat_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L5
    mov byte ptr [edi + 281h], al
write_small_diamond_lefthalfhat_L5:
    inc esi
    add edi, 2
    add esi, 2
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_lefthalfhat_L8
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L6
    mov byte ptr [edi], al
write_small_diamond_lefthalfhat_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L7
    mov byte ptr [edi + 1], al
write_small_diamond_lefthalfhat_L7:
    inc esi
    add edi, 2
write_small_diamond_lefthalfhat_L8:
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl write_small_diamond_lefthalfhat_L1
    popad
    ret
write_small_diamond_lefthalfhat_L9:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L10
    mov byte ptr [edi + 280h], al
write_small_diamond_lefthalfhat_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L11
    mov byte ptr [edi + 281h], al
write_small_diamond_lefthalfhat_L11:
    inc esi
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_lefthalfhat_L14
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L12
    mov byte ptr [edi + 2], al
write_small_diamond_lefthalfhat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L13
    mov byte ptr [edi + 3], al
write_small_diamond_lefthalfhat_L13:
    inc esi
write_small_diamond_lefthalfhat_L14:
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_small_diamond_lefthalfhat_L17
    add esi, 2
    add esi, dword ptr [_sndinit + 14]
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_lefthalfhat_L17
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L15
    mov byte ptr [edi], al
write_small_diamond_lefthalfhat_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfhat_L16
    mov byte ptr [edi + 1], al
write_small_diamond_lefthalfhat_L16:
    inc esi
write_small_diamond_lefthalfhat_L17:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_righthalfhat
; ════════════════════════════════════════════════════════════
write_small_diamond_righthalfhat_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 14], ebx
    mov ebx, edx
    mov ecx, 0
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_righthalfhat_L1
    add edi, 4
write_small_diamond_righthalfhat_L1:
    cmp ebx, ecx
    jle write_small_diamond_righthalfhat_L9
    sub edi, dword ptr [_screen_width]
    push edi
    add esi, 2
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_righthalfhat_L4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L2
    mov byte ptr [edi], al
write_small_diamond_righthalfhat_L2:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L3
    mov byte ptr [edi + 1], al
write_small_diamond_righthalfhat_L3:
    inc esi
    add edi, 2
    sub esi, 2
write_small_diamond_righthalfhat_L4:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L5
    mov byte ptr [edi + 280h], al
write_small_diamond_righthalfhat_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L6
    mov byte ptr [edi + 281h], al
write_small_diamond_righthalfhat_L6:
    inc esi
    add edi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L7
    mov byte ptr [edi + 500h], al
write_small_diamond_righthalfhat_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L8
    mov byte ptr [edi + 501h], al
write_small_diamond_righthalfhat_L8:
    inc esi
    add edi, 2
    pop edi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jl write_small_diamond_righthalfhat_L1
    popad
    ret
write_small_diamond_righthalfhat_L9:
    add esi, 2
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_righthalfhat_L10
    add edi, 2
write_small_diamond_righthalfhat_L10:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L11
    mov byte ptr [edi], al
write_small_diamond_righthalfhat_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L12
    mov byte ptr [edi + 1], al
write_small_diamond_righthalfhat_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L13
    mov byte ptr [edi + 282h], al
write_small_diamond_righthalfhat_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L14
    mov byte ptr [edi + 283h], al
write_small_diamond_righthalfhat_L14:
    inc esi
    inc ecx
    cmp ecx, dword ptr [_y_length]
    jge write_small_diamond_righthalfhat_L17
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L15
    mov byte ptr [edi + 2], al
write_small_diamond_righthalfhat_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfhat_L16
    mov byte ptr [edi + 3], al
write_small_diamond_righthalfhat_L16:
    inc esi
write_small_diamond_righthalfhat_L17:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_roof
; ════════════════════════════════════════════════════════════
write_small_diamond_roof_:
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
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L1
    mov byte ptr [edi + 4], al
write_small_diamond_roof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L2
    mov byte ptr [edi + 5], al
write_small_diamond_roof_L2:
    inc esi
    add esi, 4
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_small_diamond_roof_L20
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L3
    mov byte ptr [edi + 282h], al
write_small_diamond_roof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L4
    mov byte ptr [edi + 283h], al
write_small_diamond_roof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L5
    mov byte ptr [edi + 4], al
write_small_diamond_roof_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L6
    mov byte ptr [edi + 5], al
write_small_diamond_roof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L7
    mov byte ptr [edi + 286h], al
write_small_diamond_roof_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L8
    mov byte ptr [edi + 287h], al
write_small_diamond_roof_L8:
    inc esi
    add esi, 2
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_small_diamond_roof_L20
write_small_diamond_roof_L9:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L10
    mov byte ptr [edi + 500h], al
write_small_diamond_roof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L11
    mov byte ptr [edi + 501h], al
write_small_diamond_roof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L12
    mov byte ptr [edi + 282h], al
write_small_diamond_roof_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L13
    mov byte ptr [edi + 283h], al
write_small_diamond_roof_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L14
    mov byte ptr [edi + 4], al
write_small_diamond_roof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L15
    mov byte ptr [edi + 5], al
write_small_diamond_roof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L16
    mov byte ptr [edi + 286h], al
write_small_diamond_roof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L17
    mov byte ptr [edi + 287h], al
write_small_diamond_roof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L18
    mov byte ptr [edi + 508h], al
write_small_diamond_roof_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_roof_L19
    mov byte ptr [edi + 509h], al
write_small_diamond_roof_L19:
    inc esi
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_small_diamond_roof_L9
write_small_diamond_roof_L20:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_leftroof
; ════════════════════════════════════════════════════════════
write_small_diamond_leftroof_:
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
    add esi, 0ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle write_small_diamond_leftroof_L8
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_leftroof_L1
    mov byte ptr [edi + 280h], al
write_small_diamond_leftroof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_leftroof_L2
    mov byte ptr [edi + 281h], al
write_small_diamond_leftroof_L2:
    inc esi
    add esi, 2
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle write_small_diamond_leftroof_L8
write_small_diamond_leftroof_L3:
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_leftroof_L4
    mov byte ptr [edi + 280h], al
write_small_diamond_leftroof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_leftroof_L5
    mov byte ptr [edi + 281h], al
write_small_diamond_leftroof_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_leftroof_L6
    mov byte ptr [edi + 502h], al
write_small_diamond_leftroof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_leftroof_L7
    mov byte ptr [edi + 503h], al
write_small_diamond_leftroof_L7:
    inc esi
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg write_small_diamond_leftroof_L3
write_small_diamond_leftroof_L8:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_rightroof
; ════════════════════════════════════════════════════════════
write_small_diamond_rightroof_:
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
    add esi, 0ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle write_small_diamond_rightroof_L8
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_rightroof_L1
    mov byte ptr [edi + 282h], al
write_small_diamond_rightroof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_rightroof_L2
    mov byte ptr [edi + 283h], al
write_small_diamond_rightroof_L2:
    inc esi
    add esi, 6
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle write_small_diamond_rightroof_L8
write_small_diamond_rightroof_L3:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_rightroof_L4
    mov byte ptr [edi + 500h], al
write_small_diamond_rightroof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_rightroof_L5
    mov byte ptr [edi + 501h], al
write_small_diamond_rightroof_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_rightroof_L6
    mov byte ptr [edi + 282h], al
write_small_diamond_rightroof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_rightroof_L7
    mov byte ptr [edi + 283h], al
write_small_diamond_rightroof_L7:
    inc esi
    add esi, 6
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg write_small_diamond_rightroof_L3
write_small_diamond_rightroof_L8:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_righthalfroof
; ════════════════════════════════════════════════════════════
write_small_diamond_righthalfroof_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 14], edx
    mov ecx, dword ptr [_y_length]
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp dword ptr [_sndinit + 14], 2
    jne write_small_diamond_righthalfroof_L1
    sub edi, 2
write_small_diamond_righthalfroof_L1:
    cmp dword ptr [_sndinit + 14], 0
    jne write_small_diamond_righthalfroof_L2
    add edi, 4
write_small_diamond_righthalfroof_L2:
    add esi, 6
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_righthalfroof_L5
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L3
    mov byte ptr [edi], al
write_small_diamond_righthalfroof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L4
    mov byte ptr [edi + 1], al
write_small_diamond_righthalfroof_L4:
    inc esi
write_small_diamond_righthalfroof_L5:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_small_diamond_righthalfroof_L19
    add esi, 2
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_righthalfroof_L8
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L6
    mov byte ptr [edi], al
write_small_diamond_righthalfroof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L7
    mov byte ptr [edi + 1], al
write_small_diamond_righthalfroof_L7:
    inc esi
write_small_diamond_righthalfroof_L8:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L9
    mov byte ptr [edi + 282h], al
write_small_diamond_righthalfroof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L10
    mov byte ptr [edi + 283h], al
write_small_diamond_righthalfroof_L10:
    inc esi
    add esi, 2
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle write_small_diamond_righthalfroof_L19
write_small_diamond_righthalfroof_L11:
    add esi, 2
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_righthalfroof_L14
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L12
    mov byte ptr [edi], al
write_small_diamond_righthalfroof_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L13
    mov byte ptr [edi + 1], al
write_small_diamond_righthalfroof_L13:
    inc esi
write_small_diamond_righthalfroof_L14:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L15
    mov byte ptr [edi + 282h], al
write_small_diamond_righthalfroof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L16
    mov byte ptr [edi + 283h], al
write_small_diamond_righthalfroof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L17
    mov byte ptr [edi + 504h], al
write_small_diamond_righthalfroof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_righthalfroof_L18
    mov byte ptr [edi + 505h], al
write_small_diamond_righthalfroof_L18:
    inc esi
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg write_small_diamond_righthalfroof_L11
write_small_diamond_righthalfroof_L19:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_small_diamond_lefthalfroof
; ════════════════════════════════════════════════════════════
write_small_diamond_lefthalfroof_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 14], edx
    mov ecx, dword ptr [_y_length]
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    add esi, 6
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_lefthalfroof_L3
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L1
    mov byte ptr [edi + 4], al
write_small_diamond_lefthalfroof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L2
    mov byte ptr [edi + 5], al
write_small_diamond_lefthalfroof_L2:
    inc esi
write_small_diamond_lefthalfroof_L3:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_small_diamond_lefthalfroof_L17
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L4
    mov byte ptr [edi + 282h], al
write_small_diamond_lefthalfroof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L5
    mov byte ptr [edi + 283h], al
write_small_diamond_lefthalfroof_L5:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_lefthalfroof_L8
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L6
    mov byte ptr [edi + 4], al
write_small_diamond_lefthalfroof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L7
    mov byte ptr [edi + 5], al
write_small_diamond_lefthalfroof_L7:
    inc esi
write_small_diamond_lefthalfroof_L8:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle write_small_diamond_lefthalfroof_L17
write_small_diamond_lefthalfroof_L9:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L10
    mov byte ptr [edi + 500h], al
write_small_diamond_lefthalfroof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L11
    mov byte ptr [edi + 501h], al
write_small_diamond_lefthalfroof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L12
    mov byte ptr [edi + 282h], al
write_small_diamond_lefthalfroof_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L13
    mov byte ptr [edi + 283h], al
write_small_diamond_lefthalfroof_L13:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 14], 2
    je write_small_diamond_lefthalfroof_L16
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L14
    mov byte ptr [edi + 4], al
write_small_diamond_lefthalfroof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_small_diamond_lefthalfroof_L15
    mov byte ptr [edi + 5], al
write_small_diamond_lefthalfroof_L15:
    inc esi
write_small_diamond_lefthalfroof_L16:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg write_small_diamond_lefthalfroof_L9
write_small_diamond_lefthalfroof_L17:
    popad
    ret

_TEXT ENDS
END
