.386p
.MODEL FLAT

PUBLIC write_i_large_diamond_ptr_
PUBLIC write_i_large_diamond_ptr_left_
PUBLIC write_i_large_diamond_ptr_right_
PUBLIC write_i_medium_diamond_ptr_
PUBLIC write_i_medium_diamond_ptr_left_
PUBLIC write_i_medium_diamond_ptr_right_
PUBLIC write_i_small_diamond_ptr_
PUBLIC write_i_small_diamond_ptr_left_
PUBLIC write_i_small_diamond_ptr_right_

EXTRN _internal_screen: BYTE
EXTRN _lib_para1: BYTE
EXTRN _lib_para2: BYTE
EXTRN _screen_width: BYTE

_TEXT SEGMENT BYTE PUBLIC USE32 'CODE'

; ════════════════════════════════════════════════════════════
; write_i_large_diamond_ptr
; ════════════════════════════════════════════════════════════
write_i_large_diamond_ptr_:
    pushad
    mov ecx, eax
    shl eax, 8
    add ecx, eax
    mov ebx, edx
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_lib_para1]
    mov eax, dword ptr [_lib_para2]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp ebx, 2
    jne write_i_large_diamond_ptr_L1
    jmp near ptr write_i_large_diamond_ptr_L2
write_i_large_diamond_ptr_L1:
    mov word ptr [edi + 1ch], cx
    mov word ptr [edi + 29ah], cx
    mov word ptr [edi + 29eh], cx
    mov word ptr [edi + 518h], cx
    mov word ptr [edi + 520h], cx
    mov word ptr [edi + 796h], cx
    mov word ptr [edi + 7a2h], cx
    mov word ptr [edi + 0a14h], cx
    mov word ptr [edi + 0a24h], cx
    mov word ptr [edi + 0c92h], cx
    mov word ptr [edi + 0ca6h], cx
    mov word ptr [edi + 0f10h], cx
    mov word ptr [edi + 0f28h], cx
    mov word ptr [edi + 118eh], cx
    mov word ptr [edi + 11aah], cx
    mov word ptr [edi + 140ch], cx
    mov word ptr [edi + 142ch], cx
    mov word ptr [edi + 168ah], cx
    mov word ptr [edi + 16aeh], cx
    mov word ptr [edi + 1908h], cx
    mov word ptr [edi + 1930h], cx
    mov word ptr [edi + 1b86h], cx
    mov word ptr [edi + 1bb2h], cx
    mov word ptr [edi + 1e04h], cx
    mov word ptr [edi + 1e34h], cx
    mov word ptr [edi + 2082h], cx
    mov word ptr [edi + 20b6h], cx
    mov word ptr [edi + 2300h], cx
    mov word ptr [edi + 2338h], cx
    cmp ebx, 1
    jne write_i_large_diamond_ptr_L2
    jmp near ptr write_i_large_diamond_ptr_L3
write_i_large_diamond_ptr_L2:
    mov word ptr [edi + 2580h], cx
    mov word ptr [edi + 25b8h], cx
    mov word ptr [edi + 2802h], cx
    mov word ptr [edi + 2836h], cx
    mov word ptr [edi + 2a84h], cx
    mov word ptr [edi + 2ab4h], cx
    mov word ptr [edi + 2d06h], cx
    mov word ptr [edi + 2d32h], cx
    mov word ptr [edi + 2f88h], cx
    mov word ptr [edi + 2fb0h], cx
    mov word ptr [edi + 320ah], cx
    mov word ptr [edi + 322eh], cx
    mov word ptr [edi + 348ch], cx
    mov word ptr [edi + 34ach], cx
    mov word ptr [edi + 370eh], cx
    mov word ptr [edi + 372ah], cx
    mov word ptr [edi + 3990h], cx
    mov word ptr [edi + 39a8h], cx
    mov word ptr [edi + 3c12h], cx
    mov word ptr [edi + 3c26h], cx
    mov word ptr [edi + 3e94h], cx
    mov word ptr [edi + 3ea4h], cx
    mov word ptr [edi + 4116h], cx
    mov word ptr [edi + 4122h], cx
    mov word ptr [edi + 4398h], cx
    mov word ptr [edi + 43a0h], cx
    mov word ptr [edi + 461ah], cx
    mov word ptr [edi + 461eh], cx
    mov word ptr [edi + 489ch], cx
write_i_large_diamond_ptr_L3:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_large_diamond_ptr_left
; ════════════════════════════════════════════════════════════
write_i_large_diamond_ptr_left_:
    pushad
    cmp edx, 0
    jne near ptr write_i_large_diamond_ptr_left_L1
    mov ecx, eax
    shl eax, 8
    add ecx, eax
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_lib_para1]
    mov eax, dword ptr [_lib_para2]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov word ptr [edi + 29eh], cx
    mov word ptr [edi + 520h], cx
    mov word ptr [edi + 7a2h], cx
    mov word ptr [edi + 0a24h], cx
    mov word ptr [edi + 0ca6h], cx
    mov word ptr [edi + 0f28h], cx
    mov word ptr [edi + 11aah], cx
    mov word ptr [edi + 142ch], cx
    mov word ptr [edi + 16aeh], cx
    mov word ptr [edi + 1930h], cx
    mov word ptr [edi + 1bb2h], cx
    mov word ptr [edi + 1e34h], cx
    mov word ptr [edi + 20b6h], cx
    mov word ptr [edi + 2338h], cx
    mov word ptr [edi + 25b8h], cx
    mov word ptr [edi + 2836h], cx
    mov word ptr [edi + 2ab4h], cx
    mov word ptr [edi + 2d32h], cx
    mov word ptr [edi + 2fb0h], cx
    mov word ptr [edi + 322eh], cx
    mov word ptr [edi + 34ach], cx
    mov word ptr [edi + 372ah], cx
    mov word ptr [edi + 39a8h], cx
    mov word ptr [edi + 3c26h], cx
    mov word ptr [edi + 3ea4h], cx
    mov word ptr [edi + 4122h], cx
    mov word ptr [edi + 43a0h], cx
    mov word ptr [edi + 461eh], cx
write_i_large_diamond_ptr_left_L1:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_large_diamond_ptr_right
; ════════════════════════════════════════════════════════════
write_i_large_diamond_ptr_right_:
    pushad
    cmp edx, 0
    jne near ptr write_i_large_diamond_ptr_right_L1
    mov ecx, eax
    shl eax, 8
    add ecx, eax
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_lib_para1]
    mov eax, dword ptr [_lib_para2]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov word ptr [edi + 29ah], cx
    mov word ptr [edi + 518h], cx
    mov word ptr [edi + 796h], cx
    mov word ptr [edi + 0a14h], cx
    mov word ptr [edi + 0c92h], cx
    mov word ptr [edi + 0f10h], cx
    mov word ptr [edi + 118eh], cx
    mov word ptr [edi + 140ch], cx
    mov word ptr [edi + 168ah], cx
    mov word ptr [edi + 1908h], cx
    mov word ptr [edi + 1b86h], cx
    mov word ptr [edi + 1e04h], cx
    mov word ptr [edi + 2082h], cx
    mov word ptr [edi + 2300h], cx
    mov word ptr [edi + 2580h], cx
    mov word ptr [edi + 2802h], cx
    mov word ptr [edi + 2a84h], cx
    mov word ptr [edi + 2d06h], cx
    mov word ptr [edi + 2f88h], cx
    mov word ptr [edi + 320ah], cx
    mov word ptr [edi + 348ch], cx
    mov word ptr [edi + 370eh], cx
    mov word ptr [edi + 3990h], cx
    mov word ptr [edi + 3c12h], cx
    mov word ptr [edi + 3e94h], cx
    mov word ptr [edi + 4116h], cx
    mov word ptr [edi + 4398h], cx
    mov word ptr [edi + 461ah], cx
write_i_large_diamond_ptr_right_L1:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_medium_diamond_ptr
; ════════════════════════════════════════════════════════════
write_i_medium_diamond_ptr_:
    pushad
    mov ecx, eax
    shl eax, 8
    add ecx, eax
    mov ebx, edx
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_lib_para1]
    mov eax, dword ptr [_lib_para2]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp ebx, 2
    jne write_i_medium_diamond_ptr_L1
    jmp write_i_medium_diamond_ptr_L2
write_i_medium_diamond_ptr_L1:
    mov word ptr [edi + 0ch], cx
    mov word ptr [edi + 28ah], cx
    mov word ptr [edi + 28eh], cx
    mov word ptr [edi + 508h], cx
    mov word ptr [edi + 510h], cx
    mov word ptr [edi + 786h], cx
    mov word ptr [edi + 792h], cx
    mov word ptr [edi + 0a04h], cx
    mov word ptr [edi + 0a14h], cx
    mov word ptr [edi + 0c82h], cx
    mov word ptr [edi + 0c96h], cx
    mov word ptr [edi + 0f00h], cx
    mov word ptr [edi + 0f18h], cx
    cmp ebx, 1
    jne write_i_medium_diamond_ptr_L2
    jmp write_i_medium_diamond_ptr_L3
write_i_medium_diamond_ptr_L2:
    mov word ptr [edi + 1180h], cx
    mov word ptr [edi + 1198h], cx
    mov word ptr [edi + 1402h], cx
    mov word ptr [edi + 1416h], cx
    mov word ptr [edi + 1684h], cx
    mov word ptr [edi + 1694h], cx
    mov word ptr [edi + 1906h], cx
    mov word ptr [edi + 1912h], cx
    mov word ptr [edi + 1b88h], cx
    mov word ptr [edi + 1b90h], cx
    mov word ptr [edi + 1e0ah], cx
    mov word ptr [edi + 1e0eh], cx
    mov word ptr [edi + 208ch], cx
write_i_medium_diamond_ptr_L3:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_medium_diamond_ptr_left
; ════════════════════════════════════════════════════════════
write_i_medium_diamond_ptr_left_:
    pushad
    cmp edx, 0
    jne write_i_medium_diamond_ptr_left_L1
    mov ecx, eax
    shl eax, 8
    add ecx, eax
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_lib_para1]
    mov eax, dword ptr [_lib_para2]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov word ptr [edi + 28eh], cx
    mov word ptr [edi + 510h], cx
    mov word ptr [edi + 792h], cx
    mov word ptr [edi + 0a14h], cx
    mov word ptr [edi + 0c96h], cx
    mov word ptr [edi + 0f18h], cx
    mov word ptr [edi + 1198h], cx
    mov word ptr [edi + 1416h], cx
    mov word ptr [edi + 1694h], cx
    mov word ptr [edi + 1912h], cx
    mov word ptr [edi + 1b90h], cx
    mov word ptr [edi + 1e0eh], cx
write_i_medium_diamond_ptr_left_L1:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_medium_diamond_ptr_right
; ════════════════════════════════════════════════════════════
write_i_medium_diamond_ptr_right_:
    pushad
    cmp edx, 0
    jne write_i_medium_diamond_ptr_right_L1
    mov ecx, eax
    shl eax, 8
    add ecx, eax
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_lib_para1]
    mov eax, dword ptr [_lib_para2]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov word ptr [edi + 28ah], cx
    mov word ptr [edi + 508h], cx
    mov word ptr [edi + 786h], cx
    mov word ptr [edi + 0a04h], cx
    mov word ptr [edi + 0c82h], cx
    mov word ptr [edi + 0f00h], cx
    mov word ptr [edi + 1180h], cx
    mov word ptr [edi + 1402h], cx
    mov word ptr [edi + 1684h], cx
    mov word ptr [edi + 1906h], cx
    mov word ptr [edi + 1b88h], cx
    mov word ptr [edi + 1e0ah], cx
write_i_medium_diamond_ptr_right_L1:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_small_diamond_ptr
; ════════════════════════════════════════════════════════════
write_i_small_diamond_ptr_:
    pushad
    mov ecx, eax
    shl eax, 8
    add ecx, eax
    mov ebx, edx
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_lib_para1]
    mov eax, dword ptr [_lib_para2]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp ebx, 2
    jne write_i_small_diamond_ptr_L1
    jmp write_i_small_diamond_ptr_L2
write_i_small_diamond_ptr_L1:
    mov word ptr [edi + 4], cx
    mov word ptr [edi + 282h], cx
    mov word ptr [edi + 286h], cx
    mov word ptr [edi + 500h], cx
    mov word ptr [edi + 508h], cx
    cmp ebx, 1
    jne write_i_small_diamond_ptr_L2
    jmp write_i_small_diamond_ptr_L3
write_i_small_diamond_ptr_L2:
    mov word ptr [edi + 780h], cx
    mov word ptr [edi + 788h], cx
    mov word ptr [edi + 0a02h], cx
    mov word ptr [edi + 0a06h], cx
    mov word ptr [edi + 0c84h], cx
write_i_small_diamond_ptr_L3:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_small_diamond_ptr_left
; ════════════════════════════════════════════════════════════
write_i_small_diamond_ptr_left_:
    pushad
    cmp edx, 0
    jne write_i_small_diamond_ptr_left_L1
    mov ecx, eax
    shl eax, 8
    add ecx, eax
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_lib_para1]
    mov eax, dword ptr [_lib_para2]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov word ptr [edi + 286h], cx
    mov word ptr [edi + 508h], cx
    mov word ptr [edi + 788h], cx
    mov word ptr [edi + 0a06h], cx
write_i_small_diamond_ptr_left_L1:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_i_small_diamond_ptr_right
; ════════════════════════════════════════════════════════════
write_i_small_diamond_ptr_right_:
    pushad
    cmp edx, 0
    jne write_i_small_diamond_ptr_right_L1
    mov ecx, eax
    shl eax, 8
    add ecx, eax
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_lib_para1]
    mov eax, dword ptr [_lib_para2]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    mov word ptr [edi + 282h], cx
    mov word ptr [edi + 500h], cx
    mov word ptr [edi + 780h], cx
    mov word ptr [edi + 0a02h], cx
write_i_small_diamond_ptr_right_L1:
    popad
    ret

_TEXT ENDS
END
