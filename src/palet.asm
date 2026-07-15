.386p
.MODEL FLAT

PUBLIC _PaletteSet

_TEXT SEGMENT BYTE PUBLIC USE32 'CODE'

; ════════════════════════════════════════════════════════════
; _PaletteSet
; ════════════════════════════════════════════════════════════
_PaletteSet:
    push ebp
    db 08Bh, 0ECh    ; mov ebp, esp
    push eax
    push edx
    push ecx
    push ebx
    push esi
    mov esi, dword ptr [ebp + 8]
    mov ecx, 100h
    db 033h, 0DBh    ; xor ebx, ebx
    pushfd
    cli
    cld
    mov dx, 3c9h
_PaletteSetL1:
    dec dx
    db 08Ah, 0C3h    ; mov al, bl
    out dx, al
    inc dx
    lodsb
    out dx, al
    lodsb
    out dx, al
    lodsb
    out dx, al
    mov bh, 1
    inc bl
    loop _PaletteSetL1
    popfd
    sti
    pop esi
    pop ebx
    pop ecx
    pop edx
    pop eax
    pop ebp
    ret

_TEXT ENDS
END
