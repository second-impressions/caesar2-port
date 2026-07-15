.386p
.MODEL FLAT

PUBLIC cls_256x_
PUBLIC show_point_256x_
PUBLIC copy_screen_256x_
PUBLIC convert_and_copy_to_256xscreen_
PUBLIC copy_to_256xscreen_
PUBLIC copy_from_256xscreen_
PUBLIC compress_
PUBLIC depress_
PUBLIC call_address_
PUBLIC wvbl1_
PUBLIC set_bank_
PUBLIC copy_to_640_480_screen_
PUBLIC copy_
PUBLIC show_internal_point_
PUBLIC show_internal_2point_
PUBLIC show_internal_2x8_
PUBLIC show_internal_4point_
PUBLIC xor_internal_2point_
PUBLIC place_2x2_block_
PUBLIC place_4x4_block_
PUBLIC place_6x6_block_
PUBLIC place_8x8_block_
PUBLIC show_fast_rect_
PUBLIC copy_mouse_to_screen_
PUBLIC _lib_ret1
PUBLIC _lib_ret2
PUBLIC _lib_ret3
PUBLIC _lib_ret4
PUBLIC _lib_para1
PUBLIC _lib_para2
PUBLIC _lib_para3
PUBLIC _lib_para4

EXTRN _cscreen: BYTE
EXTRN _granularity: BYTE
EXTRN _internal_screen: BYTE
EXTRN _screen_width: BYTE
EXTRN _sprite_bank: BYTE
EXTRN _sprite_bank_ofset: BYTE
EXTRN _sprite_height: BYTE
EXTRN _sprite_next_bank_count: BYTE
EXTRN _sprite_start: BYTE
EXTRN _sprite_width: BYTE
EXTRN _x_length: BYTE
EXTRN _x_wrap: BYTE

_DATA SEGMENT DWORD PUBLIC USE32 'DATA'
_lib_ret1  DD 1
_lib_ret2  DD 1
_lib_ret3  DD 1
_lib_ret4  DD 1
_lib_para1 DD 1
_lib_para2 DD 1
_lib_para3 DD 1
_lib_para4 DD 1, 1, 1
_DATA ENDS

_TEXT SEGMENT BYTE PUBLIC USE32 'CODE'

; ════════════════════════════════════════════════════════════
; cls_256x
; ════════════════════════════════════════════════════════════
cls_256x_:
    pushad
    mov ebp, esp
    shr edx, 4
    mov ecx, edx
    mov edi, 0a0000h
    add edi, eax
    mov dx, 3c4h
    mov ax, 0f02h
    out dx, ax
    mov eax, 0
    rep stosd
    mov esp, ebp
    popad
    ret

; ════════════════════════════════════════════════════════════
; show_point_256x
; ════════════════════════════════════════════════════════════
show_point_256x_:
    pushad
    mov ebp, esp
    mov edi, 0a0000h
    add edi, dword ptr [_cscreen]
    mov ecx, eax
    shr eax, 2
    add edi, eax
    mov eax, edx
    mov edx, 50h
    mul edx
    add edi, eax
    mov dx, 3c4h
    mov ax, 102h
    and cx, 3
    shl ah, cl
    out dx, ax
    mov byte ptr [edi], bl
    mov esp, ebp
    popad
    ret

; ════════════════════════════════════════════════════════════
; copy_screen_256x
; ════════════════════════════════════════════════════════════
copy_screen_256x_:
    pushad
    mov ebp, esp
    mov esi, 0a0000h
    add esi, eax
    mov edi, 0a0000h
    add edi, edx
    mov bl, 1
    mov bh, 0
copy_screen_256x_L1:
    mov ax, 102h
    mov ah, bl
    mov dx, 3c4h
    out dx, ax
    mov ax, 104h
    mov ah, bh
    mov dx, 3ceh
    out dx, ax
    push esi
    push edi
    mov ecx, 0fa0h
    rep movsd
    pop edi
    pop esi
    add bh, 1
    shl bl, 1
    cmp bl, 8
    jle copy_screen_256x_L1
    mov esp, ebp
    popad
    ret

; ════════════════════════════════════════════════════════════
; convert_and_copy_to_256xscreen
; ════════════════════════════════════════════════════════════
convert_and_copy_to_256xscreen_:
    pushad
    mov ebp, esp
    mov esi, eax
    mov edi, 0a0000h
    add edi, edx
    mov bl, 1
convert_and_copy_to_256xscreen_L1:
    mov ax, 102h
    mov ah, bl
    mov dx, 3c4h
    out dx, ax
    push edi
    push esi
    mov ecx, 7d0h
convert_and_copy_to_256xscreen_L2:
    mov al, byte ptr [esi]
    mov byte ptr [edi], al
    mov al, byte ptr [esi + 4]
    mov byte ptr [edi + 1], al
    mov al, byte ptr [esi + 8]
    mov byte ptr [edi + 2], al
    mov al, byte ptr [esi + 0ch]
    mov byte ptr [edi + 3], al
    mov al, byte ptr [esi + 10h]
    mov byte ptr [edi + 4], al
    mov al, byte ptr [esi + 14h]
    mov byte ptr [edi + 5], al
    mov al, byte ptr [esi + 18h]
    mov byte ptr [edi + 6], al
    mov al, byte ptr [esi + 1ch]
    mov byte ptr [edi + 7], al
    add esi, 20h
    add edi, 8
    sub ecx, 1
    cmp ecx, 0
    jg convert_and_copy_to_256xscreen_L2
    pop esi
    pop edi
    add esi, 1
    shl bl, 1
    cmp bl, 8
    jle convert_and_copy_to_256xscreen_L1
    mov esp, ebp
    popad
    ret

; ════════════════════════════════════════════════════════════
; copy_to_256xscreen
; ════════════════════════════════════════════════════════════
copy_to_256xscreen_:
    pushad
    mov ebp, esp
    mov esi, eax
    mov edi, 0a0000h
    add edi, edx
    mov bl, 1
copy_to_256xscreen_L1:
    mov ax, 102h
    mov ah, bl
    mov dx, 3c4h
    out dx, ax
    push edi
    mov ecx, 0fa0h
    rep movsd
    pop edi
    shl bl, 1
    cmp bl, 8
    jle copy_to_256xscreen_L1
    mov esp, ebp
    popad
    ret

; ════════════════════════════════════════════════════════════
; copy_from_256xscreen
; ════════════════════════════════════════════════════════════
copy_from_256xscreen_:
    pushad
    mov ebp, esp
    mov esi, 0a0000h
    add esi, eax
    mov edi, edx
    mov bh, 0
copy_from_256xscreen_L1:
    mov ax, 104h
    mov ah, bh
    mov dx, 3ceh
    out dx, ax
    push esi
    mov ecx, 0fa0h
    rep movsd
    pop esi
    add bh, 1
    cmp bh, 3
    jle copy_from_256xscreen_L1
    mov esp, ebp
    popad
    ret
copy_from_256xscreen_L2:
    mov ecx, 0
    add edx, 2
    push esi
copy_from_256xscreen_L3:
    mov al, byte ptr [esi]
    cmp byte ptr [esi + 1], al
    jne copy_from_256xscreen_L4
    cmp byte ptr [esi + 2], al
    jne copy_from_256xscreen_L4
    jmp copy_from_256xscreen_L5
copy_from_256xscreen_L4:
    inc esi
    inc ecx
    add edx, 1
    sub ebx, 1
    cmp ebx, 0
    jle copy_from_256xscreen_L5
    cmp ecx, 7d00h
    jl copy_from_256xscreen_L3
copy_from_256xscreen_L5:
    pop esi
    mov eax, ecx
    sub eax, 1
    or ax, 8000h
    mov word ptr [edi], ax
    inc edi
    inc edi
    rep movsb
    ret
copy_from_256xscreen_L6:
    mov ecx, 0
    add edx, 3
    mov al, byte ptr [esi]
copy_from_256xscreen_L7:
    cmp byte ptr [esi], al
    jne copy_from_256xscreen_L8
    inc esi
    inc ecx
    sub ebx, 1
    cmp ebx, 0
    jle copy_from_256xscreen_L8
    cmp ecx, 7d00h
    jl copy_from_256xscreen_L7
copy_from_256xscreen_L8:
    mov byte ptr [edi + 2], al
    mov eax, ecx
    sub eax, 1
    mov word ptr [edi], ax
    add edi, 3
    ret

; ════════════════════════════════════════════════════════════
; compress
; ════════════════════════════════════════════════════════════
compress_:
    pushad
    mov ebp, esp
    mov esi, eax
    mov edi, edx
    mov dword ptr [edi + 4], ebx
    push edi
    add edi, 8
    mov edx, 8
compress_L1:
    cmp ebx, 0
    jle compress_L4
    mov al, byte ptr [esi]
    cmp byte ptr [esi + 1], al
    jne compress_L2
    cmp byte ptr [esi + 2], al
    jne compress_L2
    jmp compress_L3
compress_L2:
    call copy_from_256xscreen_L2
    jmp compress_L1
compress_L3:
    call copy_from_256xscreen_L6
    jmp compress_L1
compress_L4:
    pop edi
    mov dword ptr [edi], edx
    mov dword ptr [_lib_para4 + 8], edx
    mov esp, ebp
    popad
    mov eax, dword ptr [_lib_para4 + 8]
    ret

; ════════════════════════════════════════════════════════════
; depress
; ════════════════════════════════════════════════════════════
depress_:
    pushad
    mov ebp, esp
    mov esi, eax
    mov edi, edx
    mov edx, 0
    mov ebx, dword ptr [esi + 4]
    add esi, 8
depress_L1:
    cmp ebx, 0
    jle depress_L3
    mov ax, word ptr [esi]
    and ax, 8000h
    cmp ax, 0
    je depress_L2
    mov cx, word ptr [esi]
    and ecx, 7fffh
    inc ecx
    add edx, ecx
    add esi, 2
    sub ebx, ecx
    rep movsb
    jmp depress_L1
depress_L2:
    mov cx, word ptr [esi]
    mov al, byte ptr [esi + 2]
    and ecx, 7fffh
    inc ecx
    add edx, ecx
    add esi, 3
    sub ebx, ecx
    rep stosb
    jmp depress_L1
depress_L3:
    mov dword ptr [_lib_para4 + 8], edx
    mov esp, ebp
    popad
    mov eax, dword ptr [_lib_para4 + 8]
    ret

; ════════════════════════════════════════════════════════════
; call_address
; ════════════════════════════════════════════════════════════
call_address_:
    pushad
    mov ebp, esp
    call eax
    mov esp, ebp
    popad
    ret

; ════════════════════════════════════════════════════════════
; wvbl1
; ════════════════════════════════════════════════════════════
wvbl1_:
    push edx
    push eax
    mov dx, 3dah
wvbl1_L1:
    in al, dx
    and al, 8
    jne wvbl1_L1
wvbl1_L2:
    in al, dx
    and al, 8
    je wvbl1_L2
    pop eax
    pop edx
    ret

; ════════════════════════════════════════════════════════════
; set_bank
; ════════════════════════════════════════════════════════════
set_bank_:
    cmp dword ptr [_lib_para4 + 4], eax
    je set_bank_L3
    pushad
    mov ebp, esp
    mov dword ptr [_lib_para4 + 4], eax
    mov ecx, dword ptr [_granularity]
    shl eax, cl
    mov edx, eax
    mov eax, 4f05h
    mov ebx, 0
    int 10h
    and eax, 0ffffh
    cmp ax, 4fh
    je set_bank_L1
    mov eax, 0
    jmp set_bank_L2
set_bank_L1:
    mov eax, 1
set_bank_L2:
    mov esp, ebp
    popad
set_bank_L3:
    ret

; ════════════════════════════════════════════════════════════
; copy_to_640_480_screen
; ════════════════════════════════════════════════════════════
copy_to_640_480_screen_:
    pushad
    mov ebp, esp
    mov esi, eax
    mov eax, 0
copy_to_640_480_screen_L1:
    call set_bank_
    mov edi, 0a0000h
    mov ecx, 4000h
    rep movsd
    add eax, 1
    cmp eax, 3
    jle copy_to_640_480_screen_L1
    call set_bank_
    mov edi, 0a0000h
    mov ecx, 2c00h
    rep movsd
    mov esp, ebp
    popad
    ret

; ════════════════════════════════════════════════════════════
; copy
; ════════════════════════════════════════════════════════════
copy_:
    pushad
    mov esi, eax
    mov edi, edx
    mov ecx, ebx
copy_L1:
    mov eax, dword ptr [esi]
    mov dword ptr [edi], eax
    mov eax, dword ptr [esi + 4]
    mov dword ptr [edi + 4], eax
    mov eax, dword ptr [esi + 8]
    mov dword ptr [edi + 8], eax
    mov eax, dword ptr [esi + 0ch]
    mov dword ptr [edi + 0ch], eax
    mov eax, dword ptr [esi + 10h]
    mov dword ptr [edi + 10h], eax
    mov eax, dword ptr [esi + 14h]
    mov dword ptr [edi + 14h], eax
    mov eax, dword ptr [esi + 18h]
    mov dword ptr [edi + 18h], eax
    mov eax, dword ptr [esi + 1ch]
    mov dword ptr [edi + 1ch], eax
    add esi, 20h
    add edi, 20h
    sub ecx, 20h
    cmp ecx, 0
    jg copy_L1
    popad
    ret

; ════════════════════════════════════════════════════════════
; show_internal_point
; ════════════════════════════════════════════════════════════
show_internal_point_:
    push edi
    mov edi, dword ptr [_internal_screen]
    add edi, eax
    mov eax, edx
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov byte ptr [edi], bl
    pop edi
    ret

; ════════════════════════════════════════════════════════════
; show_internal_2point
; ════════════════════════════════════════════════════════════
show_internal_2point_:
    push edi
    mov edi, dword ptr [_internal_screen]
    add edi, eax
    mov eax, edx
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    pop edi
    ret

; ════════════════════════════════════════════════════════════
; show_internal_2x8
; ════════════════════════════════════════════════════════════
show_internal_2x8_:
    push edi
    mov edi, dword ptr [_internal_screen]
    add edi, eax
    mov eax, edx
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    add edi, 27fh
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    add edi, 27fh
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    add edi, 27fh
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    add edi, 27fh
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    add edi, 27fh
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    add edi, 27fh
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    add edi, 27fh
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    pop edi
    ret

; ════════════════════════════════════════════════════════════
; show_internal_4point
; ════════════════════════════════════════════════════════════
show_internal_4point_:
    push edi
    mov edi, dword ptr [_internal_screen]
    add edi, eax
    mov eax, edx
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    inc edi
    mov byte ptr [edi], bl
    pop edi
    ret

; ════════════════════════════════════════════════════════════
; xor_internal_2point
; ════════════════════════════════════════════════════════════
xor_internal_2point_:
    push edi
    mov edi, dword ptr [_internal_screen]
    add edi, eax
    mov eax, edx
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov al, byte ptr [edi]
    cmp al, 0
    jne xor_internal_2point_L1
    mov byte ptr [edi], bl
xor_internal_2point_L1:
    inc edi
    mov al, byte ptr [edi]
    cmp al, 0
    jne xor_internal_2point_L2
    mov byte ptr [edi], bl
xor_internal_2point_L2:
    pop edi
    ret

; ════════════════════════════════════════════════════════════
; place_2x2_block
; ════════════════════════════════════════════════════════════
place_2x2_block_:
    push edi
    push esi
    mov esi, eax
    mov edi, dword ptr [_internal_screen]
    add edi, edx
    movsw
    add edi, 27eh
    movsw
    pop esi
    pop edi
    ret

; ════════════════════════════════════════════════════════════
; place_4x4_block
; ════════════════════════════════════════════════════════════
place_4x4_block_:
    push edi
    push esi
    mov esi, eax
    mov edi, dword ptr [_internal_screen]
    add edi, edx
    movsd
    add edi, 27ch
    movsd
    add edi, 27ch
    movsd
    add edi, 27ch
    movsd
    pop esi
    pop edi
    ret

; ════════════════════════════════════════════════════════════
; place_6x6_block
; ════════════════════════════════════════════════════════════
place_6x6_block_:
    push edi
    push esi
    mov esi, eax
    mov edi, dword ptr [_internal_screen]
    add edi, edx
    movsd
    movsw
    add edi, 27ah
    movsd
    movsw
    add edi, 27ah
    movsd
    movsw
    add edi, 27ah
    movsd
    movsw
    add edi, 27ah
    movsd
    movsw
    add edi, 27ah
    movsd
    movsw
    pop esi
    pop edi
    ret

; ════════════════════════════════════════════════════════════
; place_8x8_block
; ════════════════════════════════════════════════════════════
place_8x8_block_:
    push edi
    push esi
    mov esi, eax
    mov edi, dword ptr [_internal_screen]
    add edi, edx
    movsd
    movsd
    add edi, 278h
    movsd
    movsd
    add edi, 278h
    movsd
    movsd
    add edi, 278h
    movsd
    movsd
    add edi, 278h
    movsd
    movsd
    add edi, 278h
    movsd
    movsd
    add edi, 278h
    movsd
    movsd
    add edi, 278h
    movsd
    movsd
    pop esi
    pop edi
    ret

; ════════════════════════════════════════════════════════════
; show_fast_rect
; ════════════════════════════════════════════════════════════
show_fast_rect_:
    pushad
    mov edi, dword ptr [_internal_screen]
    add edi, eax
    mov eax, edx
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov ecx, ebx
    shl ebx, 8
    add bl, cl
    shl ebx, 8
    add bl, cl
    shl ebx, 8
    add bl, cl
    mov edx, dword ptr [_sprite_height]
show_fast_rect_L1:
    push edi
    mov ecx, dword ptr [_sprite_width]
show_fast_rect_L2:
    mov dword ptr [edi], ebx
    add edi, 4
    mov dword ptr [edi], ebx
    add edi, 4
    mov dword ptr [edi], ebx
    add edi, 4
    mov dword ptr [edi], ebx
    add edi, 4
    dec ecx
    jg show_fast_rect_L2
    pop edi
    add edi, dword ptr [_screen_width]
    dec edx
    jg show_fast_rect_L1
    popad
    ret

; ════════════════════════════════════════════════════════════
; copy_mouse_to_screen
; ════════════════════════════════════════════════════════════
copy_mouse_to_screen_:
    pushad
    mov esi, eax
    add esi, dword ptr [_sprite_start]
    mov eax, dword ptr [_sprite_bank]
    call set_bank_
    mov edi, 0a0000h
    add edi, dword ptr [_sprite_bank_ofset]
    mov edx, dword ptr [_sprite_height]
copy_mouse_to_screen_L1:
    mov ecx, dword ptr [_sprite_width]
copy_mouse_to_screen_L2:
    mov al, byte ptr [esi]
    cmp al, 0
    je copy_mouse_to_screen_L3
    mov byte ptr [edi], al
copy_mouse_to_screen_L3:
    sub dword ptr [_sprite_next_bank_count], 1
    cmp dword ptr [_sprite_next_bank_count], 0
    jg copy_mouse_to_screen_L4
    mov eax, dword ptr [_sprite_bank]
    add eax, 1
    call set_bank_
    mov dword ptr [_sprite_next_bank_count], 8000h
copy_mouse_to_screen_L4:
    inc esi
    inc edi
    dec ecx
    jg copy_mouse_to_screen_L2
    add esi, dword ptr [_x_length]
    mov eax, dword ptr [_x_wrap]
    add edi, eax
    sub dword ptr [_sprite_next_bank_count], eax
    cmp dword ptr [_sprite_next_bank_count], 0
    jg copy_mouse_to_screen_L5
    mov eax, dword ptr [_sprite_bank]
    add eax, 1
    call set_bank_
    mov dword ptr [_sprite_next_bank_count], 8000h
copy_mouse_to_screen_L5:
    dec edx
    jg copy_mouse_to_screen_L1
    popad
    ret

_TEXT ENDS
END
