.386p
.MODEL FLAT

PUBLIC write_i_font_
PUBLIC write_i_left_font_
PUBLIC write_i_right_font_
PUBLIC place_i_sprite_
PUBLIC write_i_sprite_
PUBLIC write_i_left_sprite_
PUBLIC write_i_right_sprite_
PUBLIC place_16x16_block_
PUBLIC place_24x24_block_
PUBLIC place_32x32_block_
PUBLIC refresh_16x16_block_
PUBLIC refresh_16x16_partblock_
PUBLIC pick_up_mouse_background_
PUBLIC put_down_mouse_background_

EXTRN _font_style: BYTE
EXTRN _internal_screen: BYTE
EXTRN _screen_width: BYTE
EXTRN _sprite_colour: BYTE
EXTRN _sprite_height: BYTE
EXTRN _sprite_image_no: BYTE
EXTRN _sprite_start: BYTE
EXTRN _sprite_width: BYTE
EXTRN _sprite_x: BYTE
EXTRN _sprite_y: BYTE
EXTRN _x_length: BYTE
EXTRN _x_ofset: BYTE
EXTRN _x_wrap: BYTE
EXTRN _y_length: BYTE

_TEXT SEGMENT BYTE PUBLIC USE32 'CODE'

; ════════════════════════════════════════════════════════════
; write_i_font
; ════════════════════════════════════════════════════════════
write_i_font_:
    pushad
    mov esi, eax
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp dword ptr [_font_style], 1
    je write_i_font_L4
    mov ebx, dword ptr [_sprite_colour]
    mov edx, dword ptr [_y_length]
write_i_font_L1:
    mov ecx, dword ptr [_sprite_width]
write_i_font_L2:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_font_L3
    mov byte ptr [edi], bl
write_i_font_L3:
    inc esi
    inc edi
    dec ecx
    jg write_i_font_L2
    add edi, dword ptr [_x_wrap]
    dec edx
    jg write_i_font_L1
    popad
    ret
write_i_font_L4:
    mov edx, dword ptr [_y_length]
write_i_font_L5:
    mov ecx, dword ptr [_sprite_width]
write_i_font_L6:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_font_L7
    mov byte ptr [edi], al
write_i_font_L7:
    inc esi
    inc edi
    dec ecx
    jg write_i_font_L6
    add edi, dword ptr [_x_wrap]
    dec edx
    jg write_i_font_L5
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_left_font
; ════════════════════════════════════════════════════════════
write_i_left_font_:
    pushad
    mov esi, eax
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov edx, dword ptr [_y_length]
    mov ebx, dword ptr [_sprite_colour]
write_i_left_font_L1:
    mov ecx, dword ptr [_x_length]
write_i_left_font_L2:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_left_font_L3
    mov byte ptr [edi], bl
write_i_left_font_L3:
    inc esi
    inc edi
    dec ecx
    jg write_i_left_font_L2
    add esi, dword ptr [_x_ofset]
    add edi, dword ptr [_x_wrap]
    dec edx
    jg write_i_left_font_L1
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_right_font
; ════════════════════════════════════════════════════════════
write_i_right_font_:
    pushad
    mov esi, eax
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov edx, dword ptr [_y_length]
    mov ebx, dword ptr [_sprite_colour]
write_i_right_font_L1:
    mov ecx, dword ptr [_x_length]
write_i_right_font_L2:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_right_font_L3
    mov byte ptr [edi], bl
write_i_right_font_L3:
    inc esi
    inc edi
    dec ecx
    jg write_i_right_font_L2
    add esi, dword ptr [_x_ofset]
    add edi, dword ptr [_x_wrap]
    dec edx
    jg write_i_right_font_L1
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_i_sprite
; ════════════════════════════════════════════════════════════
place_i_sprite_:
    pushad
    mov esi, eax
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov eax, dword ptr [_sprite_width]
    and eax, 3
    je place_i_sprite_L2
    mov edx, dword ptr [_sprite_height]
place_i_sprite_L1:
    mov ecx, dword ptr [_sprite_width]
    rep movsb
    add edi, dword ptr [_x_wrap]
    dec edx
    jg place_i_sprite_L1
    jmp place_i_sprite_L4
place_i_sprite_L2:
    mov edx, dword ptr [_sprite_height]
place_i_sprite_L3:
    mov ecx, dword ptr [_sprite_width]
    shr ecx, 2
    rep movsd
    add edi, dword ptr [_x_wrap]
    dec edx
    jg place_i_sprite_L3
place_i_sprite_L4:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_sprite
; ════════════════════════════════════════════════════════════
write_i_sprite_:
    pushad
    mov esi, eax
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov edx, dword ptr [_y_length]
write_i_sprite_L1:
    mov ecx, dword ptr [_sprite_width]
    mov eax, ecx
    and eax, 3
    je write_i_sprite_L4
write_i_sprite_L2:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_sprite_L3
    mov byte ptr [edi], al
write_i_sprite_L3:
    inc esi
    inc edi
    dec ecx
    jg write_i_sprite_L2
    add edi, dword ptr [_x_wrap]
    dec edx
    jg write_i_sprite_L1
    jmp write_i_sprite_L9
write_i_sprite_L4:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_sprite_L5
    mov byte ptr [edi], al
write_i_sprite_L5:
    inc esi
    inc edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_sprite_L6
    mov byte ptr [edi], al
write_i_sprite_L6:
    inc esi
    inc edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_sprite_L7
    mov byte ptr [edi], al
write_i_sprite_L7:
    inc esi
    inc edi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_sprite_L8
    mov byte ptr [edi], al
write_i_sprite_L8:
    inc esi
    inc edi
    sub ecx, 4
    jg write_i_sprite_L2
    add edi, dword ptr [_x_wrap]
    dec edx
    jg write_i_sprite_L1
write_i_sprite_L9:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_left_sprite
; ════════════════════════════════════════════════════════════
write_i_left_sprite_:
    pushad
    mov esi, eax
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov edx, dword ptr [_y_length]
    mov ebx, dword ptr [_x_ofset]
write_i_left_sprite_L1:
    mov ecx, dword ptr [_x_length]
write_i_left_sprite_L2:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_left_sprite_L3
    mov byte ptr [edi], al
write_i_left_sprite_L3:
    inc esi
    inc edi
    dec ecx
    jg write_i_left_sprite_L2
    add esi, ebx
    add edi, dword ptr [_x_wrap]
    dec edx
    jg write_i_left_sprite_L1
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_right_sprite
; ════════════════════════════════════════════════════════════
write_i_right_sprite_:
    pushad
    mov esi, eax
    add esi, dword ptr [_sprite_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov edx, dword ptr [_y_length]
    mov ebx, dword ptr [_x_ofset]
write_i_right_sprite_L1:
    mov ecx, dword ptr [_x_length]
write_i_right_sprite_L2:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_i_right_sprite_L3
    mov byte ptr [edi], al
write_i_right_sprite_L3:
    inc esi
    inc edi
    dec ecx
    jg write_i_right_sprite_L2
    add esi, ebx
    add edi, dword ptr [_x_wrap]
    dec edx
    jg write_i_right_sprite_L1
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_16x16_block
; ════════════════════════════════════════════════════════════
place_16x16_block_:
    pushad
    mov esi, eax
    mov eax, dword ptr [_sprite_image_no]
    shl eax, 4
    add eax, 8
    mov ebx, 0
    mov bl, byte ptr [esi + eax + 5]
    shl ebx, 8
    mov bl, byte ptr [esi + eax + 4]
    add esi, ebx
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    mov ecx, 4
    rep movsd
    add edi, 270h
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_24x24_block
; ════════════════════════════════════════════════════════════
place_24x24_block_:
    pushad
    mov esi, eax
    mov eax, dword ptr [_sprite_image_no]
    shl eax, 4
    add eax, 8
    mov ebx, 0
    mov bl, byte ptr [esi + eax + 5]
    shl ebx, 8
    mov bl, byte ptr [esi + eax + 4]
    add esi, ebx
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    popad
    ret

; ════════════════════════════════════════════════════════════
; place_32x32_block
; ════════════════════════════════════════════════════════════
place_32x32_block_:
    pushad
    mov esi, eax
    mov eax, dword ptr [_sprite_image_no]
    shl eax, 4
    add eax, 8
    mov ebx, 0
    mov bl, byte ptr [esi + eax + 6]
    shl ebx, 8
    shl ebx, 8
    mov bh, byte ptr [esi + eax + 5]
    mov bl, byte ptr [esi + eax + 4]
    add esi, ebx
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    mov ecx, 8
    rep movsd
    add edi, 260h
    popad
    ret

; ════════════════════════════════════════════════════════════
; refresh_16x16_block
; ════════════════════════════════════════════════════════════
refresh_16x16_block_:
    pushad
    mov esi, dword ptr [_internal_screen]
    add esi, eax
    mov edi, 0a0000h
    add edi, edx
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    popad
    ret

; ════════════════════════════════════════════════════════════
; refresh_16x16_partblock
; ════════════════════════════════════════════════════════════
refresh_16x16_partblock_:
    pushad
    mov esi, dword ptr [_internal_screen]
    add esi, eax
    mov edi, 0a0000h
    add edi, edx
refresh_16x16_partblock_L1:
    cmp ebx, 0
    jle refresh_16x16_partblock_L2
    dec ebx
    mov ecx, 4
    rep movsd
    add esi, 270h
    add edi, 270h
    jmp refresh_16x16_partblock_L1
refresh_16x16_partblock_L2:
    popad
    ret

; ════════════════════════════════════════════════════════════
; pick_up_mouse_background
; ════════════════════════════════════════════════════════════
pick_up_mouse_background_:
    pushad
    mov edi, eax
    mov esi, dword ptr [_internal_screen]
    add esi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add esi, eax
    mov eax, 3
pick_up_mouse_background_L1:
    mov ecx, 6
    rep movsd
    add esi, 268h
    mov ecx, 6
    rep movsd
    add esi, 268h
    mov ecx, 6
    rep movsd
    add esi, 268h
    mov ecx, 6
    rep movsd
    add esi, 268h
    mov ecx, 6
    rep movsd
    add esi, 268h
    mov ecx, 6
    rep movsd
    add esi, 268h
    mov ecx, 6
    rep movsd
    add esi, 268h
    mov ecx, 6
    rep movsd
    add esi, 268h
    dec eax
    jg pick_up_mouse_background_L1
    popad
    ret

; ════════════════════════════════════════════════════════════
; put_down_mouse_background
; ════════════════════════════════════════════════════════════
put_down_mouse_background_:
    pushad
    mov esi, eax
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov eax, 3
put_down_mouse_background_L1:
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    mov ecx, 6
    rep movsd
    add edi, 268h
    dec eax
    jg put_down_mouse_background_L1
    popad
    ret

_TEXT ENDS
END
