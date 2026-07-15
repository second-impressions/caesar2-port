.386p
.MODEL FLAT

PUBLIC write_large_diamond_roof_
PUBLIC write_large_diamond_leftroof_
PUBLIC write_large_diamond_rightroof_
PUBLIC write_large_diamond_righthalfroof_
PUBLIC write_large_diamond_lefthalfroof_

EXTRN _internal_screen: BYTE
EXTRN _screen_width: BYTE
EXTRN _sndinit: BYTE
EXTRN _sprite_hat_start: BYTE
EXTRN _sprite_x: BYTE
EXTRN _sprite_y: BYTE
EXTRN _y_length: BYTE

_TEXT SEGMENT BYTE PUBLIC USE32 'CODE'

; ════════════════════════════════════════════════════════════
; write_large_diamond_roof
; ════════════════════════════════════════════════════════════
write_large_diamond_roof_:
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
    add esi, 1ch
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L1
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L2
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L2:
    inc esi
    add esi, 1ch
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 1ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L3
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L4
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L5
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L6
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L7
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L8
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L8:
    inc esi
    add esi, 1ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 18h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L9
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L10
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L11
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L12
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L12:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L13
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L14
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L15
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L16
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L17
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L18
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L18:
    inc esi
    add esi, 18h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 16h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L19
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L20
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L21
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L22
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L23
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L24
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L25
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L26
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L27
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L28
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L29
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L30
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L31
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L32
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L32:
    inc esi
    add esi, 16h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 14h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L33
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L34
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L35
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L36
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L37
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L38
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L39
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L40
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L41
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L42
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L43
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L44
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L45
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L46
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L47
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L48
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L49
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L50
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L50:
    inc esi
    add esi, 14h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 12h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L51
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L52
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L53
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L54
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L55
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L56
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L57
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L58
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L59
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L60
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L61
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L62
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L63
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L64
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L65
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L66
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L67
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L68
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L69
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L70
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L71
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L72
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L72:
    inc esi
    add esi, 12h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 10h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L73
    mov byte ptr [edi + 0f10h], al
write_large_diamond_roof_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L74
    mov byte ptr [edi + 0f11h], al
write_large_diamond_roof_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L75
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L76
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L77
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L78
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L79
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L80
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L81
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L82
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L83
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L84
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L84:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L85
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L86
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L87
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L88
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L88:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L89
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L90
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L91
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L92
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L93
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L94
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L95
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L96
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L97
    mov byte ptr [edi + 0f28h], al
write_large_diamond_roof_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L98
    mov byte ptr [edi + 0f29h], al
write_large_diamond_roof_L98:
    inc esi
    add esi, 10h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L99
    mov byte ptr [edi + 118eh], al
write_large_diamond_roof_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L100
    mov byte ptr [edi + 118fh], al
write_large_diamond_roof_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L101
    mov byte ptr [edi + 0f10h], al
write_large_diamond_roof_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L102
    mov byte ptr [edi + 0f11h], al
write_large_diamond_roof_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L103
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L104
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L104:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L105
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L106
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L107
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L108
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L108:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L109
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L110
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L110:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L111
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L112
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L112:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L113
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L113:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L114
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L114:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L115
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L116
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L116:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L117
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L117:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L118
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L119
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L119:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L120
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L120:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L121
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L122
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L122:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L123
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L124
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L125
    mov byte ptr [edi + 0f28h], al
write_large_diamond_roof_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L126
    mov byte ptr [edi + 0f29h], al
write_large_diamond_roof_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L127
    mov byte ptr [edi + 11aah], al
write_large_diamond_roof_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L128
    mov byte ptr [edi + 11abh], al
write_large_diamond_roof_L128:
    inc esi
    add esi, 0eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 0ch
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L129
    mov byte ptr [edi + 140ch], al
write_large_diamond_roof_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L130
    mov byte ptr [edi + 140dh], al
write_large_diamond_roof_L130:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L131
    mov byte ptr [edi + 118eh], al
write_large_diamond_roof_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L132
    mov byte ptr [edi + 118fh], al
write_large_diamond_roof_L132:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L133
    mov byte ptr [edi + 0f10h], al
write_large_diamond_roof_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L134
    mov byte ptr [edi + 0f11h], al
write_large_diamond_roof_L134:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L135
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L136
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L136:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L137
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L137:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L138
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L139
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L140
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L140:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L141
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L142
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L142:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L143
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L143:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L144
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L144:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L145
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L146
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L146:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L147
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L147:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L148
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L149
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L150
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L150:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L151
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L152
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L153
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L154
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L154:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L155
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L155:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L156
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L156:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L157
    mov byte ptr [edi + 0f28h], al
write_large_diamond_roof_L157:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L158
    mov byte ptr [edi + 0f29h], al
write_large_diamond_roof_L158:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L159
    mov byte ptr [edi + 11aah], al
write_large_diamond_roof_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L160
    mov byte ptr [edi + 11abh], al
write_large_diamond_roof_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L161
    mov byte ptr [edi + 142ch], al
write_large_diamond_roof_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L162
    mov byte ptr [edi + 142dh], al
write_large_diamond_roof_L162:
    inc esi
    add esi, 0ch
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L163
    mov byte ptr [edi + 168ah], al
write_large_diamond_roof_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L164
    mov byte ptr [edi + 168bh], al
write_large_diamond_roof_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L165
    mov byte ptr [edi + 140ch], al
write_large_diamond_roof_L165:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L166
    mov byte ptr [edi + 140dh], al
write_large_diamond_roof_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L167
    mov byte ptr [edi + 118eh], al
write_large_diamond_roof_L167:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L168
    mov byte ptr [edi + 118fh], al
write_large_diamond_roof_L168:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L169
    mov byte ptr [edi + 0f10h], al
write_large_diamond_roof_L169:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L170
    mov byte ptr [edi + 0f11h], al
write_large_diamond_roof_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L171
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L171:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L172
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L172:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L173
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L174
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L174:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L175
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L176
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L176:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L177
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L177:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L178
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L179
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L180
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L181
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L182
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L182:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L183
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L183:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L184
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L184:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L185
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L186
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L187
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L188
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L188:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L189
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L190
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L191
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L191:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L192
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L192:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L193
    mov byte ptr [edi + 0f28h], al
write_large_diamond_roof_L193:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L194
    mov byte ptr [edi + 0f29h], al
write_large_diamond_roof_L194:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L195
    mov byte ptr [edi + 11aah], al
write_large_diamond_roof_L195:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L196
    mov byte ptr [edi + 11abh], al
write_large_diamond_roof_L196:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L197
    mov byte ptr [edi + 142ch], al
write_large_diamond_roof_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L198
    mov byte ptr [edi + 142dh], al
write_large_diamond_roof_L198:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L199
    mov byte ptr [edi + 16aeh], al
write_large_diamond_roof_L199:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L200
    mov byte ptr [edi + 16afh], al
write_large_diamond_roof_L200:
    inc esi
    add esi, 0ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 8
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L201
    mov byte ptr [edi + 1908h], al
write_large_diamond_roof_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L202
    mov byte ptr [edi + 1909h], al
write_large_diamond_roof_L202:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L203
    mov byte ptr [edi + 168ah], al
write_large_diamond_roof_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L204
    mov byte ptr [edi + 168bh], al
write_large_diamond_roof_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L205
    mov byte ptr [edi + 140ch], al
write_large_diamond_roof_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L206
    mov byte ptr [edi + 140dh], al
write_large_diamond_roof_L206:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L207
    mov byte ptr [edi + 118eh], al
write_large_diamond_roof_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L208
    mov byte ptr [edi + 118fh], al
write_large_diamond_roof_L208:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L209
    mov byte ptr [edi + 0f10h], al
write_large_diamond_roof_L209:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L210
    mov byte ptr [edi + 0f11h], al
write_large_diamond_roof_L210:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L211
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L211:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L212
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L212:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L213
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L213:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L214
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L214:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L215
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L215:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L216
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L216:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L217
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L217:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L218
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L218:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L219
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L219:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L220
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L220:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L221
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L221:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L222
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L222:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L223
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L223:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L224
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L224:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L225
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L225:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L226
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L226:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L227
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L227:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L228
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L228:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L229
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L229:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L230
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L230:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L231
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L231:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L232
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L232:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L233
    mov byte ptr [edi + 0f28h], al
write_large_diamond_roof_L233:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L234
    mov byte ptr [edi + 0f29h], al
write_large_diamond_roof_L234:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L235
    mov byte ptr [edi + 11aah], al
write_large_diamond_roof_L235:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L236
    mov byte ptr [edi + 11abh], al
write_large_diamond_roof_L236:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L237
    mov byte ptr [edi + 142ch], al
write_large_diamond_roof_L237:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L238
    mov byte ptr [edi + 142dh], al
write_large_diamond_roof_L238:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L239
    mov byte ptr [edi + 16aeh], al
write_large_diamond_roof_L239:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L240
    mov byte ptr [edi + 16afh], al
write_large_diamond_roof_L240:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L241
    mov byte ptr [edi + 1930h], al
write_large_diamond_roof_L241:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L242
    mov byte ptr [edi + 1931h], al
write_large_diamond_roof_L242:
    inc esi
    add esi, 8
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L243
    mov byte ptr [edi + 1b86h], al
write_large_diamond_roof_L243:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L244
    mov byte ptr [edi + 1b87h], al
write_large_diamond_roof_L244:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L245
    mov byte ptr [edi + 1908h], al
write_large_diamond_roof_L245:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L246
    mov byte ptr [edi + 1909h], al
write_large_diamond_roof_L246:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L247
    mov byte ptr [edi + 168ah], al
write_large_diamond_roof_L247:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L248
    mov byte ptr [edi + 168bh], al
write_large_diamond_roof_L248:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L249
    mov byte ptr [edi + 140ch], al
write_large_diamond_roof_L249:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L250
    mov byte ptr [edi + 140dh], al
write_large_diamond_roof_L250:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L251
    mov byte ptr [edi + 118eh], al
write_large_diamond_roof_L251:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L252
    mov byte ptr [edi + 118fh], al
write_large_diamond_roof_L252:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L253
    mov byte ptr [edi + 0f10h], al
write_large_diamond_roof_L253:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L254
    mov byte ptr [edi + 0f11h], al
write_large_diamond_roof_L254:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L255
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L255:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L256
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L256:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L257
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L257:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L258
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L258:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L259
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L259:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L260
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L260:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L261
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L261:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L262
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L262:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L263
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L263:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L264
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L264:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L265
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L265:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L266
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L266:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L267
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L267:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L268
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L268:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L269
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L269:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L270
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L270:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L271
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L271:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L272
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L272:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L273
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L273:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L274
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L274:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L275
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L275:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L276
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L276:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L277
    mov byte ptr [edi + 0f28h], al
write_large_diamond_roof_L277:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L278
    mov byte ptr [edi + 0f29h], al
write_large_diamond_roof_L278:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L279
    mov byte ptr [edi + 11aah], al
write_large_diamond_roof_L279:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L280
    mov byte ptr [edi + 11abh], al
write_large_diamond_roof_L280:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L281
    mov byte ptr [edi + 142ch], al
write_large_diamond_roof_L281:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L282
    mov byte ptr [edi + 142dh], al
write_large_diamond_roof_L282:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L283
    mov byte ptr [edi + 16aeh], al
write_large_diamond_roof_L283:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L284
    mov byte ptr [edi + 16afh], al
write_large_diamond_roof_L284:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L285
    mov byte ptr [edi + 1930h], al
write_large_diamond_roof_L285:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L286
    mov byte ptr [edi + 1931h], al
write_large_diamond_roof_L286:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L287
    mov byte ptr [edi + 1bb2h], al
write_large_diamond_roof_L287:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L288
    mov byte ptr [edi + 1bb3h], al
write_large_diamond_roof_L288:
    inc esi
    add esi, 6
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L289
    mov byte ptr [edi + 1e04h], al
write_large_diamond_roof_L289:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L290
    mov byte ptr [edi + 1e05h], al
write_large_diamond_roof_L290:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L291
    mov byte ptr [edi + 1b86h], al
write_large_diamond_roof_L291:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L292
    mov byte ptr [edi + 1b87h], al
write_large_diamond_roof_L292:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L293
    mov byte ptr [edi + 1908h], al
write_large_diamond_roof_L293:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L294
    mov byte ptr [edi + 1909h], al
write_large_diamond_roof_L294:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L295
    mov byte ptr [edi + 168ah], al
write_large_diamond_roof_L295:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L296
    mov byte ptr [edi + 168bh], al
write_large_diamond_roof_L296:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L297
    mov byte ptr [edi + 140ch], al
write_large_diamond_roof_L297:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L298
    mov byte ptr [edi + 140dh], al
write_large_diamond_roof_L298:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L299
    mov byte ptr [edi + 118eh], al
write_large_diamond_roof_L299:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L300
    mov byte ptr [edi + 118fh], al
write_large_diamond_roof_L300:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L301
    mov byte ptr [edi + 0f10h], al
write_large_diamond_roof_L301:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L302
    mov byte ptr [edi + 0f11h], al
write_large_diamond_roof_L302:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L303
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L303:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L304
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L304:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L305
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L305:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L306
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L306:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L307
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L307:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L308
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L308:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L309
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L309:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L310
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L310:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L311
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L311:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L312
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L312:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L313
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L313:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L314
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L314:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L315
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L315:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L316
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L316:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L317
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L317:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L318
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L318:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L319
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L319:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L320
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L320:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L321
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L321:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L322
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L322:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L323
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L323:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L324
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L324:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L325
    mov byte ptr [edi + 0f28h], al
write_large_diamond_roof_L325:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L326
    mov byte ptr [edi + 0f29h], al
write_large_diamond_roof_L326:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L327
    mov byte ptr [edi + 11aah], al
write_large_diamond_roof_L327:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L328
    mov byte ptr [edi + 11abh], al
write_large_diamond_roof_L328:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L329
    mov byte ptr [edi + 142ch], al
write_large_diamond_roof_L329:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L330
    mov byte ptr [edi + 142dh], al
write_large_diamond_roof_L330:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L331
    mov byte ptr [edi + 16aeh], al
write_large_diamond_roof_L331:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L332
    mov byte ptr [edi + 16afh], al
write_large_diamond_roof_L332:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L333
    mov byte ptr [edi + 1930h], al
write_large_diamond_roof_L333:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L334
    mov byte ptr [edi + 1931h], al
write_large_diamond_roof_L334:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L335
    mov byte ptr [edi + 1bb2h], al
write_large_diamond_roof_L335:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L336
    mov byte ptr [edi + 1bb3h], al
write_large_diamond_roof_L336:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L337
    mov byte ptr [edi + 1e34h], al
write_large_diamond_roof_L337:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L338
    mov byte ptr [edi + 1e35h], al
write_large_diamond_roof_L338:
    inc esi
    add esi, 4
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L339
    mov byte ptr [edi + 2082h], al
write_large_diamond_roof_L339:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L340
    mov byte ptr [edi + 2083h], al
write_large_diamond_roof_L340:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L341
    mov byte ptr [edi + 1e04h], al
write_large_diamond_roof_L341:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L342
    mov byte ptr [edi + 1e05h], al
write_large_diamond_roof_L342:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L343
    mov byte ptr [edi + 1b86h], al
write_large_diamond_roof_L343:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L344
    mov byte ptr [edi + 1b87h], al
write_large_diamond_roof_L344:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L345
    mov byte ptr [edi + 1908h], al
write_large_diamond_roof_L345:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L346
    mov byte ptr [edi + 1909h], al
write_large_diamond_roof_L346:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L347
    mov byte ptr [edi + 168ah], al
write_large_diamond_roof_L347:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L348
    mov byte ptr [edi + 168bh], al
write_large_diamond_roof_L348:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L349
    mov byte ptr [edi + 140ch], al
write_large_diamond_roof_L349:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L350
    mov byte ptr [edi + 140dh], al
write_large_diamond_roof_L350:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L351
    mov byte ptr [edi + 118eh], al
write_large_diamond_roof_L351:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L352
    mov byte ptr [edi + 118fh], al
write_large_diamond_roof_L352:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L353
    mov byte ptr [edi + 0f10h], al
write_large_diamond_roof_L353:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L354
    mov byte ptr [edi + 0f11h], al
write_large_diamond_roof_L354:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L355
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L355:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L356
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L356:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L357
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L357:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L358
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L358:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L359
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L359:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L360
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L360:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L361
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L361:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L362
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L362:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L363
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L363:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L364
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L364:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L365
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L365:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L366
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L366:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L367
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L367:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L368
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L368:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L369
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L369:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L370
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L370:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L371
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L371:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L372
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L372:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L373
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L373:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L374
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L374:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L375
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L375:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L376
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L376:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L377
    mov byte ptr [edi + 0f28h], al
write_large_diamond_roof_L377:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L378
    mov byte ptr [edi + 0f29h], al
write_large_diamond_roof_L378:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L379
    mov byte ptr [edi + 11aah], al
write_large_diamond_roof_L379:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L380
    mov byte ptr [edi + 11abh], al
write_large_diamond_roof_L380:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L381
    mov byte ptr [edi + 142ch], al
write_large_diamond_roof_L381:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L382
    mov byte ptr [edi + 142dh], al
write_large_diamond_roof_L382:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L383
    mov byte ptr [edi + 16aeh], al
write_large_diamond_roof_L383:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L384
    mov byte ptr [edi + 16afh], al
write_large_diamond_roof_L384:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L385
    mov byte ptr [edi + 1930h], al
write_large_diamond_roof_L385:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L386
    mov byte ptr [edi + 1931h], al
write_large_diamond_roof_L386:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L387
    mov byte ptr [edi + 1bb2h], al
write_large_diamond_roof_L387:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L388
    mov byte ptr [edi + 1bb3h], al
write_large_diamond_roof_L388:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L389
    mov byte ptr [edi + 1e34h], al
write_large_diamond_roof_L389:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L390
    mov byte ptr [edi + 1e35h], al
write_large_diamond_roof_L390:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L391
    mov byte ptr [edi + 20b6h], al
write_large_diamond_roof_L391:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L392
    mov byte ptr [edi + 20b7h], al
write_large_diamond_roof_L392:
    inc esi
    add esi, 2
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_roof_L452
write_large_diamond_roof_L393:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L394
    mov byte ptr [edi + 2300h], al
write_large_diamond_roof_L394:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L395
    mov byte ptr [edi + 2301h], al
write_large_diamond_roof_L395:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L396
    mov byte ptr [edi + 2082h], al
write_large_diamond_roof_L396:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L397
    mov byte ptr [edi + 2083h], al
write_large_diamond_roof_L397:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L398
    mov byte ptr [edi + 1e04h], al
write_large_diamond_roof_L398:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L399
    mov byte ptr [edi + 1e05h], al
write_large_diamond_roof_L399:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L400
    mov byte ptr [edi + 1b86h], al
write_large_diamond_roof_L400:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L401
    mov byte ptr [edi + 1b87h], al
write_large_diamond_roof_L401:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L402
    mov byte ptr [edi + 1908h], al
write_large_diamond_roof_L402:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L403
    mov byte ptr [edi + 1909h], al
write_large_diamond_roof_L403:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L404
    mov byte ptr [edi + 168ah], al
write_large_diamond_roof_L404:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L405
    mov byte ptr [edi + 168bh], al
write_large_diamond_roof_L405:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L406
    mov byte ptr [edi + 140ch], al
write_large_diamond_roof_L406:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L407
    mov byte ptr [edi + 140dh], al
write_large_diamond_roof_L407:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L408
    mov byte ptr [edi + 118eh], al
write_large_diamond_roof_L408:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L409
    mov byte ptr [edi + 118fh], al
write_large_diamond_roof_L409:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L410
    mov byte ptr [edi + 0f10h], al
write_large_diamond_roof_L410:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L411
    mov byte ptr [edi + 0f11h], al
write_large_diamond_roof_L411:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L412
    mov byte ptr [edi + 0c92h], al
write_large_diamond_roof_L412:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L413
    mov byte ptr [edi + 0c93h], al
write_large_diamond_roof_L413:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L414
    mov byte ptr [edi + 0a14h], al
write_large_diamond_roof_L414:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L415
    mov byte ptr [edi + 0a15h], al
write_large_diamond_roof_L415:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L416
    mov byte ptr [edi + 796h], al
write_large_diamond_roof_L416:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L417
    mov byte ptr [edi + 797h], al
write_large_diamond_roof_L417:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L418
    mov byte ptr [edi + 518h], al
write_large_diamond_roof_L418:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L419
    mov byte ptr [edi + 519h], al
write_large_diamond_roof_L419:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L420
    mov byte ptr [edi + 29ah], al
write_large_diamond_roof_L420:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L421
    mov byte ptr [edi + 29bh], al
write_large_diamond_roof_L421:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L422
    mov byte ptr [edi + 1ch], al
write_large_diamond_roof_L422:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L423
    mov byte ptr [edi + 1dh], al
write_large_diamond_roof_L423:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L424
    mov byte ptr [edi + 29eh], al
write_large_diamond_roof_L424:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L425
    mov byte ptr [edi + 29fh], al
write_large_diamond_roof_L425:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L426
    mov byte ptr [edi + 520h], al
write_large_diamond_roof_L426:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L427
    mov byte ptr [edi + 521h], al
write_large_diamond_roof_L427:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L428
    mov byte ptr [edi + 7a2h], al
write_large_diamond_roof_L428:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L429
    mov byte ptr [edi + 7a3h], al
write_large_diamond_roof_L429:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L430
    mov byte ptr [edi + 0a24h], al
write_large_diamond_roof_L430:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L431
    mov byte ptr [edi + 0a25h], al
write_large_diamond_roof_L431:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L432
    mov byte ptr [edi + 0ca6h], al
write_large_diamond_roof_L432:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L433
    mov byte ptr [edi + 0ca7h], al
write_large_diamond_roof_L433:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L434
    mov byte ptr [edi + 0f28h], al
write_large_diamond_roof_L434:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L435
    mov byte ptr [edi + 0f29h], al
write_large_diamond_roof_L435:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L436
    mov byte ptr [edi + 11aah], al
write_large_diamond_roof_L436:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L437
    mov byte ptr [edi + 11abh], al
write_large_diamond_roof_L437:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L438
    mov byte ptr [edi + 142ch], al
write_large_diamond_roof_L438:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L439
    mov byte ptr [edi + 142dh], al
write_large_diamond_roof_L439:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L440
    mov byte ptr [edi + 16aeh], al
write_large_diamond_roof_L440:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L441
    mov byte ptr [edi + 16afh], al
write_large_diamond_roof_L441:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L442
    mov byte ptr [edi + 1930h], al
write_large_diamond_roof_L442:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L443
    mov byte ptr [edi + 1931h], al
write_large_diamond_roof_L443:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L444
    mov byte ptr [edi + 1bb2h], al
write_large_diamond_roof_L444:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L445
    mov byte ptr [edi + 1bb3h], al
write_large_diamond_roof_L445:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L446
    mov byte ptr [edi + 1e34h], al
write_large_diamond_roof_L446:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L447
    mov byte ptr [edi + 1e35h], al
write_large_diamond_roof_L447:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L448
    mov byte ptr [edi + 20b6h], al
write_large_diamond_roof_L448:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L449
    mov byte ptr [edi + 20b7h], al
write_large_diamond_roof_L449:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L450
    mov byte ptr [edi + 2338h], al
write_large_diamond_roof_L450:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_roof_L451
    mov byte ptr [edi + 2339h], al
write_large_diamond_roof_L451:
    inc esi
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_large_diamond_roof_L393
write_large_diamond_roof_L452:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_large_diamond_leftroof
; ════════════════════════════════════════════════════════════
write_large_diamond_leftroof_:
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
    add esi, 3ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L1
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L2
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L2:
    inc esi
    add esi, 1ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L3
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L4
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L5
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L6
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L6:
    inc esi
    add esi, 18h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L7
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L8
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L9
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L10
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L11
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L12
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L12:
    inc esi
    add esi, 16h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L13
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L14
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L15
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L16
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L17
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L18
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L19
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L20
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L20:
    inc esi
    add esi, 14h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L21
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L22
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L23
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L24
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L25
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L26
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L27
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L28
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L29
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L30
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L30:
    inc esi
    add esi, 12h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L31
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L32
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L33
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L34
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L35
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L36
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L37
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L38
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L39
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L40
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L41
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_leftroof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L42
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_leftroof_L42:
    inc esi
    add esi, 10h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L43
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L44
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L45
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L46
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L47
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L48
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L49
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L50
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L51
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L52
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L53
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_leftroof_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L54
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_leftroof_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L55
    mov byte ptr [edi + 118ch], al
write_large_diamond_leftroof_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L56
    mov byte ptr [edi + 118dh], al
write_large_diamond_leftroof_L56:
    inc esi
    add esi, 0eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L57
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L58
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L59
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L60
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L61
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L62
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L63
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L64
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L65
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L66
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L67
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_leftroof_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L68
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_leftroof_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L69
    mov byte ptr [edi + 118ch], al
write_large_diamond_leftroof_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L70
    mov byte ptr [edi + 118dh], al
write_large_diamond_leftroof_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L71
    mov byte ptr [edi + 140eh], al
write_large_diamond_leftroof_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L72
    mov byte ptr [edi + 140fh], al
write_large_diamond_leftroof_L72:
    inc esi
    add esi, 0ch
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L73
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L74
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L75
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L76
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L77
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L78
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L79
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L80
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L81
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L82
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L83
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_leftroof_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L84
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_leftroof_L84:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L85
    mov byte ptr [edi + 118ch], al
write_large_diamond_leftroof_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L86
    mov byte ptr [edi + 118dh], al
write_large_diamond_leftroof_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L87
    mov byte ptr [edi + 140eh], al
write_large_diamond_leftroof_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L88
    mov byte ptr [edi + 140fh], al
write_large_diamond_leftroof_L88:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L89
    mov byte ptr [edi + 1690h], al
write_large_diamond_leftroof_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L90
    mov byte ptr [edi + 1691h], al
write_large_diamond_leftroof_L90:
    inc esi
    add esi, 0ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L91
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L92
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L93
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L94
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L95
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L96
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L97
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L98
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L99
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L100
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L101
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_leftroof_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L102
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_leftroof_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L103
    mov byte ptr [edi + 118ch], al
write_large_diamond_leftroof_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L104
    mov byte ptr [edi + 118dh], al
write_large_diamond_leftroof_L104:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L105
    mov byte ptr [edi + 140eh], al
write_large_diamond_leftroof_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L106
    mov byte ptr [edi + 140fh], al
write_large_diamond_leftroof_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L107
    mov byte ptr [edi + 1690h], al
write_large_diamond_leftroof_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L108
    mov byte ptr [edi + 1691h], al
write_large_diamond_leftroof_L108:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L109
    mov byte ptr [edi + 1912h], al
write_large_diamond_leftroof_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L110
    mov byte ptr [edi + 1913h], al
write_large_diamond_leftroof_L110:
    inc esi
    add esi, 8
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L111
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L112
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L112:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L113
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L113:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L114
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L114:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L115
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L116
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L116:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L117
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L117:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L118
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L119
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L119:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L120
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L120:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L121
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_leftroof_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L122
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_leftroof_L122:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L123
    mov byte ptr [edi + 118ch], al
write_large_diamond_leftroof_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L124
    mov byte ptr [edi + 118dh], al
write_large_diamond_leftroof_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L125
    mov byte ptr [edi + 140eh], al
write_large_diamond_leftroof_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L126
    mov byte ptr [edi + 140fh], al
write_large_diamond_leftroof_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L127
    mov byte ptr [edi + 1690h], al
write_large_diamond_leftroof_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L128
    mov byte ptr [edi + 1691h], al
write_large_diamond_leftroof_L128:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L129
    mov byte ptr [edi + 1912h], al
write_large_diamond_leftroof_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L130
    mov byte ptr [edi + 1913h], al
write_large_diamond_leftroof_L130:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L131
    mov byte ptr [edi + 1b94h], al
write_large_diamond_leftroof_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L132
    mov byte ptr [edi + 1b95h], al
write_large_diamond_leftroof_L132:
    inc esi
    add esi, 6
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L133
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L134
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L134:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L135
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L136
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L136:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L137
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L137:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L138
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L139
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L140
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L140:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L141
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L142
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L142:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L143
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_leftroof_L143:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L144
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_leftroof_L144:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L145
    mov byte ptr [edi + 118ch], al
write_large_diamond_leftroof_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L146
    mov byte ptr [edi + 118dh], al
write_large_diamond_leftroof_L146:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L147
    mov byte ptr [edi + 140eh], al
write_large_diamond_leftroof_L147:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L148
    mov byte ptr [edi + 140fh], al
write_large_diamond_leftroof_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L149
    mov byte ptr [edi + 1690h], al
write_large_diamond_leftroof_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L150
    mov byte ptr [edi + 1691h], al
write_large_diamond_leftroof_L150:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L151
    mov byte ptr [edi + 1912h], al
write_large_diamond_leftroof_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L152
    mov byte ptr [edi + 1913h], al
write_large_diamond_leftroof_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L153
    mov byte ptr [edi + 1b94h], al
write_large_diamond_leftroof_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L154
    mov byte ptr [edi + 1b95h], al
write_large_diamond_leftroof_L154:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L155
    mov byte ptr [edi + 1e16h], al
write_large_diamond_leftroof_L155:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L156
    mov byte ptr [edi + 1e17h], al
write_large_diamond_leftroof_L156:
    inc esi
    add esi, 4
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L157
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L157:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L158
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L158:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L159
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L160
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L161
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L162
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L162:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L163
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L164
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L165
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L165:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L166
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L167
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_leftroof_L167:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L168
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_leftroof_L168:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L169
    mov byte ptr [edi + 118ch], al
write_large_diamond_leftroof_L169:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L170
    mov byte ptr [edi + 118dh], al
write_large_diamond_leftroof_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L171
    mov byte ptr [edi + 140eh], al
write_large_diamond_leftroof_L171:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L172
    mov byte ptr [edi + 140fh], al
write_large_diamond_leftroof_L172:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L173
    mov byte ptr [edi + 1690h], al
write_large_diamond_leftroof_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L174
    mov byte ptr [edi + 1691h], al
write_large_diamond_leftroof_L174:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L175
    mov byte ptr [edi + 1912h], al
write_large_diamond_leftroof_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L176
    mov byte ptr [edi + 1913h], al
write_large_diamond_leftroof_L176:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L177
    mov byte ptr [edi + 1b94h], al
write_large_diamond_leftroof_L177:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L178
    mov byte ptr [edi + 1b95h], al
write_large_diamond_leftroof_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L179
    mov byte ptr [edi + 1e16h], al
write_large_diamond_leftroof_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L180
    mov byte ptr [edi + 1e17h], al
write_large_diamond_leftroof_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L181
    mov byte ptr [edi + 2098h], al
write_large_diamond_leftroof_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L182
    mov byte ptr [edi + 2099h], al
write_large_diamond_leftroof_L182:
    inc esi
    add esi, 2
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_leftroof_L212
write_large_diamond_leftroof_L183:
    add esi, 1eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L184
    mov byte ptr [edi + 280h], al
write_large_diamond_leftroof_L184:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L185
    mov byte ptr [edi + 281h], al
write_large_diamond_leftroof_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L186
    mov byte ptr [edi + 502h], al
write_large_diamond_leftroof_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L187
    mov byte ptr [edi + 503h], al
write_large_diamond_leftroof_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L188
    mov byte ptr [edi + 784h], al
write_large_diamond_leftroof_L188:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L189
    mov byte ptr [edi + 785h], al
write_large_diamond_leftroof_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L190
    mov byte ptr [edi + 0a06h], al
write_large_diamond_leftroof_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L191
    mov byte ptr [edi + 0a07h], al
write_large_diamond_leftroof_L191:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L192
    mov byte ptr [edi + 0c88h], al
write_large_diamond_leftroof_L192:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L193
    mov byte ptr [edi + 0c89h], al
write_large_diamond_leftroof_L193:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L194
    mov byte ptr [edi + 0f0ah], al
write_large_diamond_leftroof_L194:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L195
    mov byte ptr [edi + 0f0bh], al
write_large_diamond_leftroof_L195:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L196
    mov byte ptr [edi + 118ch], al
write_large_diamond_leftroof_L196:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L197
    mov byte ptr [edi + 118dh], al
write_large_diamond_leftroof_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L198
    mov byte ptr [edi + 140eh], al
write_large_diamond_leftroof_L198:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L199
    mov byte ptr [edi + 140fh], al
write_large_diamond_leftroof_L199:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L200
    mov byte ptr [edi + 1690h], al
write_large_diamond_leftroof_L200:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L201
    mov byte ptr [edi + 1691h], al
write_large_diamond_leftroof_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L202
    mov byte ptr [edi + 1912h], al
write_large_diamond_leftroof_L202:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L203
    mov byte ptr [edi + 1913h], al
write_large_diamond_leftroof_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L204
    mov byte ptr [edi + 1b94h], al
write_large_diamond_leftroof_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L205
    mov byte ptr [edi + 1b95h], al
write_large_diamond_leftroof_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L206
    mov byte ptr [edi + 1e16h], al
write_large_diamond_leftroof_L206:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L207
    mov byte ptr [edi + 1e17h], al
write_large_diamond_leftroof_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L208
    mov byte ptr [edi + 2098h], al
write_large_diamond_leftroof_L208:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L209
    mov byte ptr [edi + 2099h], al
write_large_diamond_leftroof_L209:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L210
    mov byte ptr [edi + 231ah], al
write_large_diamond_leftroof_L210:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_leftroof_L211
    mov byte ptr [edi + 231bh], al
write_large_diamond_leftroof_L211:
    inc esi
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_large_diamond_leftroof_L183
write_large_diamond_leftroof_L212:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_large_diamond_rightroof
; ════════════════════════════════════════════════════════════
write_large_diamond_rightroof_:
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
    add esi, 3ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 1ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L1
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L2
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L2:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 18h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L3
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L4
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L5
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L5:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L6
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L6:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 16h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L7
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L7:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L8
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L8:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L9
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L10
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L11
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L12
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L12:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 14h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L13
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L14
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L15
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L16
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L17
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L18
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L19
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L20
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L20:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 12h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L21
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L22
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L23
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L24
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L25
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L26
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L27
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L28
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L29
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L30
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L30:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 10h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L31
    mov byte ptr [edi + 0f10h], al
write_large_diamond_rightroof_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L32
    mov byte ptr [edi + 0f11h], al
write_large_diamond_rightroof_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L33
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L34
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L35
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L36
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L37
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L38
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L39
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L40
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L41
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L42
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L42:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L43
    mov byte ptr [edi + 118eh], al
write_large_diamond_rightroof_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L44
    mov byte ptr [edi + 118fh], al
write_large_diamond_rightroof_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L45
    mov byte ptr [edi + 0f10h], al
write_large_diamond_rightroof_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L46
    mov byte ptr [edi + 0f11h], al
write_large_diamond_rightroof_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L47
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L48
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L49
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L50
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L51
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L52
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L53
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L54
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L55
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L56
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L56:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 0ch
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L57
    mov byte ptr [edi + 140ch], al
write_large_diamond_rightroof_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L58
    mov byte ptr [edi + 140dh], al
write_large_diamond_rightroof_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L59
    mov byte ptr [edi + 118eh], al
write_large_diamond_rightroof_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L60
    mov byte ptr [edi + 118fh], al
write_large_diamond_rightroof_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L61
    mov byte ptr [edi + 0f10h], al
write_large_diamond_rightroof_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L62
    mov byte ptr [edi + 0f11h], al
write_large_diamond_rightroof_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L63
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L64
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L65
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L66
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L67
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L68
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L69
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L70
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L71
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L72
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L72:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L73
    mov byte ptr [edi + 168ah], al
write_large_diamond_rightroof_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L74
    mov byte ptr [edi + 168bh], al
write_large_diamond_rightroof_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L75
    mov byte ptr [edi + 140ch], al
write_large_diamond_rightroof_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L76
    mov byte ptr [edi + 140dh], al
write_large_diamond_rightroof_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L77
    mov byte ptr [edi + 118eh], al
write_large_diamond_rightroof_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L78
    mov byte ptr [edi + 118fh], al
write_large_diamond_rightroof_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L79
    mov byte ptr [edi + 0f10h], al
write_large_diamond_rightroof_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L80
    mov byte ptr [edi + 0f11h], al
write_large_diamond_rightroof_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L81
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L82
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L83
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L84
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L84:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L85
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L86
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L87
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L88
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L88:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L89
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L90
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L90:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 8
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L91
    mov byte ptr [edi + 1908h], al
write_large_diamond_rightroof_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L92
    mov byte ptr [edi + 1909h], al
write_large_diamond_rightroof_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L93
    mov byte ptr [edi + 168ah], al
write_large_diamond_rightroof_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L94
    mov byte ptr [edi + 168bh], al
write_large_diamond_rightroof_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L95
    mov byte ptr [edi + 140ch], al
write_large_diamond_rightroof_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L96
    mov byte ptr [edi + 140dh], al
write_large_diamond_rightroof_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L97
    mov byte ptr [edi + 118eh], al
write_large_diamond_rightroof_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L98
    mov byte ptr [edi + 118fh], al
write_large_diamond_rightroof_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L99
    mov byte ptr [edi + 0f10h], al
write_large_diamond_rightroof_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L100
    mov byte ptr [edi + 0f11h], al
write_large_diamond_rightroof_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L101
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L102
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L103
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L104
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L104:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L105
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L106
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L107
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L108
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L108:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L109
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L110
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L110:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L111
    mov byte ptr [edi + 1b86h], al
write_large_diamond_rightroof_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L112
    mov byte ptr [edi + 1b87h], al
write_large_diamond_rightroof_L112:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L113
    mov byte ptr [edi + 1908h], al
write_large_diamond_rightroof_L113:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L114
    mov byte ptr [edi + 1909h], al
write_large_diamond_rightroof_L114:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L115
    mov byte ptr [edi + 168ah], al
write_large_diamond_rightroof_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L116
    mov byte ptr [edi + 168bh], al
write_large_diamond_rightroof_L116:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L117
    mov byte ptr [edi + 140ch], al
write_large_diamond_rightroof_L117:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L118
    mov byte ptr [edi + 140dh], al
write_large_diamond_rightroof_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L119
    mov byte ptr [edi + 118eh], al
write_large_diamond_rightroof_L119:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L120
    mov byte ptr [edi + 118fh], al
write_large_diamond_rightroof_L120:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L121
    mov byte ptr [edi + 0f10h], al
write_large_diamond_rightroof_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L122
    mov byte ptr [edi + 0f11h], al
write_large_diamond_rightroof_L122:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L123
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L124
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L125
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L126
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L127
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L128
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L128:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L129
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L130
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L130:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L131
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L132
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L132:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L133
    mov byte ptr [edi + 1e04h], al
write_large_diamond_rightroof_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L134
    mov byte ptr [edi + 1e05h], al
write_large_diamond_rightroof_L134:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L135
    mov byte ptr [edi + 1b86h], al
write_large_diamond_rightroof_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L136
    mov byte ptr [edi + 1b87h], al
write_large_diamond_rightroof_L136:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L137
    mov byte ptr [edi + 1908h], al
write_large_diamond_rightroof_L137:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L138
    mov byte ptr [edi + 1909h], al
write_large_diamond_rightroof_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L139
    mov byte ptr [edi + 168ah], al
write_large_diamond_rightroof_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L140
    mov byte ptr [edi + 168bh], al
write_large_diamond_rightroof_L140:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L141
    mov byte ptr [edi + 140ch], al
write_large_diamond_rightroof_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L142
    mov byte ptr [edi + 140dh], al
write_large_diamond_rightroof_L142:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L143
    mov byte ptr [edi + 118eh], al
write_large_diamond_rightroof_L143:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L144
    mov byte ptr [edi + 118fh], al
write_large_diamond_rightroof_L144:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L145
    mov byte ptr [edi + 0f10h], al
write_large_diamond_rightroof_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L146
    mov byte ptr [edi + 0f11h], al
write_large_diamond_rightroof_L146:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L147
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L147:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L148
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L149
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L150
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L150:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L151
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L152
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L153
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L154
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L154:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L155
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L155:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L156
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L156:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L157
    mov byte ptr [edi + 2082h], al
write_large_diamond_rightroof_L157:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L158
    mov byte ptr [edi + 2083h], al
write_large_diamond_rightroof_L158:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L159
    mov byte ptr [edi + 1e04h], al
write_large_diamond_rightroof_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L160
    mov byte ptr [edi + 1e05h], al
write_large_diamond_rightroof_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L161
    mov byte ptr [edi + 1b86h], al
write_large_diamond_rightroof_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L162
    mov byte ptr [edi + 1b87h], al
write_large_diamond_rightroof_L162:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L163
    mov byte ptr [edi + 1908h], al
write_large_diamond_rightroof_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L164
    mov byte ptr [edi + 1909h], al
write_large_diamond_rightroof_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L165
    mov byte ptr [edi + 168ah], al
write_large_diamond_rightroof_L165:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L166
    mov byte ptr [edi + 168bh], al
write_large_diamond_rightroof_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L167
    mov byte ptr [edi + 140ch], al
write_large_diamond_rightroof_L167:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L168
    mov byte ptr [edi + 140dh], al
write_large_diamond_rightroof_L168:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L169
    mov byte ptr [edi + 118eh], al
write_large_diamond_rightroof_L169:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L170
    mov byte ptr [edi + 118fh], al
write_large_diamond_rightroof_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L171
    mov byte ptr [edi + 0f10h], al
write_large_diamond_rightroof_L171:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L172
    mov byte ptr [edi + 0f11h], al
write_large_diamond_rightroof_L172:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L173
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L174
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L174:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L175
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L176
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L176:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L177
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L177:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L178
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L179
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L180
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L181
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L182
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L182:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_rightroof_L212
write_large_diamond_rightroof_L183:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L184
    mov byte ptr [edi + 2300h], al
write_large_diamond_rightroof_L184:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L185
    mov byte ptr [edi + 2301h], al
write_large_diamond_rightroof_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L186
    mov byte ptr [edi + 2082h], al
write_large_diamond_rightroof_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L187
    mov byte ptr [edi + 2083h], al
write_large_diamond_rightroof_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L188
    mov byte ptr [edi + 1e04h], al
write_large_diamond_rightroof_L188:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L189
    mov byte ptr [edi + 1e05h], al
write_large_diamond_rightroof_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L190
    mov byte ptr [edi + 1b86h], al
write_large_diamond_rightroof_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L191
    mov byte ptr [edi + 1b87h], al
write_large_diamond_rightroof_L191:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L192
    mov byte ptr [edi + 1908h], al
write_large_diamond_rightroof_L192:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L193
    mov byte ptr [edi + 1909h], al
write_large_diamond_rightroof_L193:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L194
    mov byte ptr [edi + 168ah], al
write_large_diamond_rightroof_L194:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L195
    mov byte ptr [edi + 168bh], al
write_large_diamond_rightroof_L195:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L196
    mov byte ptr [edi + 140ch], al
write_large_diamond_rightroof_L196:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L197
    mov byte ptr [edi + 140dh], al
write_large_diamond_rightroof_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L198
    mov byte ptr [edi + 118eh], al
write_large_diamond_rightroof_L198:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L199
    mov byte ptr [edi + 118fh], al
write_large_diamond_rightroof_L199:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L200
    mov byte ptr [edi + 0f10h], al
write_large_diamond_rightroof_L200:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L201
    mov byte ptr [edi + 0f11h], al
write_large_diamond_rightroof_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L202
    mov byte ptr [edi + 0c92h], al
write_large_diamond_rightroof_L202:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L203
    mov byte ptr [edi + 0c93h], al
write_large_diamond_rightroof_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L204
    mov byte ptr [edi + 0a14h], al
write_large_diamond_rightroof_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L205
    mov byte ptr [edi + 0a15h], al
write_large_diamond_rightroof_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L206
    mov byte ptr [edi + 796h], al
write_large_diamond_rightroof_L206:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L207
    mov byte ptr [edi + 797h], al
write_large_diamond_rightroof_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L208
    mov byte ptr [edi + 518h], al
write_large_diamond_rightroof_L208:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L209
    mov byte ptr [edi + 519h], al
write_large_diamond_rightroof_L209:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L210
    mov byte ptr [edi + 29ah], al
write_large_diamond_rightroof_L210:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_rightroof_L211
    mov byte ptr [edi + 29bh], al
write_large_diamond_rightroof_L211:
    inc esi
    add esi, 1eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_large_diamond_rightroof_L183
write_large_diamond_rightroof_L212:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_large_diamond_righthalfroof
; ════════════════════════════════════════════════════════════
write_large_diamond_righthalfroof_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 6], edx
    mov ecx, dword ptr [_y_length]
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    cmp dword ptr [_sndinit + 6], 2
    jne write_large_diamond_righthalfroof_L1
    sub edi, 2
write_large_diamond_righthalfroof_L1:
    cmp dword ptr [_sndinit + 6], 0
    jne write_large_diamond_righthalfroof_L2
    add edi, 1ch
write_large_diamond_righthalfroof_L2:
    add esi, 1eh
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L5
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L3
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L3:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L4
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L4:
    inc esi
write_large_diamond_righthalfroof_L5:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L8
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L6
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L7
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L7:
    inc esi
write_large_diamond_righthalfroof_L8:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L9
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L10
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L10:
    inc esi
    add esi, 1ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L13
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L11
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L12
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L12:
    inc esi
write_large_diamond_righthalfroof_L13:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L14
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L14:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L15
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L15:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L16
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L17
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L17:
    inc esi
    add esi, 18h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L20
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L18
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L19
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L19:
    inc esi
write_large_diamond_righthalfroof_L20:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L21
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L21:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L22
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L23
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L23:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L24
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L24:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L25
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L26
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L26:
    inc esi
    add esi, 16h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L29
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L27
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L28
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L28:
    inc esi
write_large_diamond_righthalfroof_L29:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L30
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L31
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L32
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L32:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L33
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L34
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L34:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L35
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L35:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L36
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L37
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L37:
    inc esi
    add esi, 14h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L40
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L38
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L39
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L39:
    inc esi
write_large_diamond_righthalfroof_L40:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L41
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L42
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L43
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L44
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L45
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L45:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L46
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L47
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L47:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L48
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L48:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L49
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L50
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L50:
    inc esi
    add esi, 12h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L53
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L51
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L52
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L52:
    inc esi
write_large_diamond_righthalfroof_L53:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L54
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L55
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L56
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L57
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L58
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L59
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L60
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L60:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L61
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L62
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L62:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L63
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L63:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L64
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfroof_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L65
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfroof_L65:
    inc esi
    add esi, 10h
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L68
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L66
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L67
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L67:
    inc esi
write_large_diamond_righthalfroof_L68:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L69
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L70
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L71
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L72
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L72:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L73
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L74
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L75
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L76
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L77
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L77:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L78
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L79
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfroof_L79:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L80
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfroof_L80:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L81
    mov byte ptr [edi + 118eh], al
write_large_diamond_righthalfroof_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L82
    mov byte ptr [edi + 118fh], al
write_large_diamond_righthalfroof_L82:
    inc esi
    add esi, 0eh
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L85
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L83
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L84
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L84:
    inc esi
write_large_diamond_righthalfroof_L85:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L86
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L87
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L88
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L88:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L89
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L90
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L91
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L92
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L93
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L94
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L95
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L96
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfroof_L96:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L97
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfroof_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L98
    mov byte ptr [edi + 118eh], al
write_large_diamond_righthalfroof_L98:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L99
    mov byte ptr [edi + 118fh], al
write_large_diamond_righthalfroof_L99:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L100
    mov byte ptr [edi + 1410h], al
write_large_diamond_righthalfroof_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L101
    mov byte ptr [edi + 1411h], al
write_large_diamond_righthalfroof_L101:
    inc esi
    add esi, 0ch
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L104
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L102
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L103
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L103:
    inc esi
write_large_diamond_righthalfroof_L104:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L105
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L106
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L107
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L108
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L108:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L109
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L110
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L110:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L111
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L112
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L112:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L113
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L113:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L114
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L114:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L115
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfroof_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L116
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfroof_L116:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L117
    mov byte ptr [edi + 118eh], al
write_large_diamond_righthalfroof_L117:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L118
    mov byte ptr [edi + 118fh], al
write_large_diamond_righthalfroof_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L119
    mov byte ptr [edi + 1410h], al
write_large_diamond_righthalfroof_L119:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L120
    mov byte ptr [edi + 1411h], al
write_large_diamond_righthalfroof_L120:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L121
    mov byte ptr [edi + 1692h], al
write_large_diamond_righthalfroof_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L122
    mov byte ptr [edi + 1693h], al
write_large_diamond_righthalfroof_L122:
    inc esi
    add esi, 0ah
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 0bh
    je near ptr write_large_diamond_righthalfroof_L40
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L123
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L124
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L125
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L126
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L127
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L128
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L128:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L129
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L130
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L130:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L131
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L132
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L132:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L133
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L134
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L134:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L135
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfroof_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L136
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfroof_L136:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L137
    mov byte ptr [edi + 118eh], al
write_large_diamond_righthalfroof_L137:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L138
    mov byte ptr [edi + 118fh], al
write_large_diamond_righthalfroof_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L139
    mov byte ptr [edi + 1410h], al
write_large_diamond_righthalfroof_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L140
    mov byte ptr [edi + 1411h], al
write_large_diamond_righthalfroof_L140:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L141
    mov byte ptr [edi + 1692h], al
write_large_diamond_righthalfroof_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L142
    mov byte ptr [edi + 1693h], al
write_large_diamond_righthalfroof_L142:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L143
    mov byte ptr [edi + 1914h], al
write_large_diamond_righthalfroof_L143:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L144
    mov byte ptr [edi + 1915h], al
write_large_diamond_righthalfroof_L144:
    inc esi
    add esi, 8
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L147
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L145
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L146
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L146:
    inc esi
write_large_diamond_righthalfroof_L147:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L148
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L149
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L150
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L150:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L151
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L152
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L153
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L154
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L154:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L155
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L155:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L156
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L156:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L157
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L157:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L158
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfroof_L158:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L159
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfroof_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L160
    mov byte ptr [edi + 118eh], al
write_large_diamond_righthalfroof_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L161
    mov byte ptr [edi + 118fh], al
write_large_diamond_righthalfroof_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L162
    mov byte ptr [edi + 1410h], al
write_large_diamond_righthalfroof_L162:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L163
    mov byte ptr [edi + 1411h], al
write_large_diamond_righthalfroof_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L164
    mov byte ptr [edi + 1692h], al
write_large_diamond_righthalfroof_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L165
    mov byte ptr [edi + 1693h], al
write_large_diamond_righthalfroof_L165:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L166
    mov byte ptr [edi + 1914h], al
write_large_diamond_righthalfroof_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L167
    mov byte ptr [edi + 1915h], al
write_large_diamond_righthalfroof_L167:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L168
    mov byte ptr [edi + 1b96h], al
write_large_diamond_righthalfroof_L168:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L169
    mov byte ptr [edi + 1b97h], al
write_large_diamond_righthalfroof_L169:
    inc esi
    add esi, 6
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L172
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L170
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L171
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L171:
    inc esi
write_large_diamond_righthalfroof_L172:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L173
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L174
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L174:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L175
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L176
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L176:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L177
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L177:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L178
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L179
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L180
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L181
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L182
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L182:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L183
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfroof_L183:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L184
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfroof_L184:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L185
    mov byte ptr [edi + 118eh], al
write_large_diamond_righthalfroof_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L186
    mov byte ptr [edi + 118fh], al
write_large_diamond_righthalfroof_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L187
    mov byte ptr [edi + 1410h], al
write_large_diamond_righthalfroof_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L188
    mov byte ptr [edi + 1411h], al
write_large_diamond_righthalfroof_L188:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L189
    mov byte ptr [edi + 1692h], al
write_large_diamond_righthalfroof_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L190
    mov byte ptr [edi + 1693h], al
write_large_diamond_righthalfroof_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L191
    mov byte ptr [edi + 1914h], al
write_large_diamond_righthalfroof_L191:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L192
    mov byte ptr [edi + 1915h], al
write_large_diamond_righthalfroof_L192:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L193
    mov byte ptr [edi + 1b96h], al
write_large_diamond_righthalfroof_L193:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L194
    mov byte ptr [edi + 1b97h], al
write_large_diamond_righthalfroof_L194:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L195
    mov byte ptr [edi + 1e18h], al
write_large_diamond_righthalfroof_L195:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L196
    mov byte ptr [edi + 1e19h], al
write_large_diamond_righthalfroof_L196:
    inc esi
    add esi, 4
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L199
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L197
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L198
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L198:
    inc esi
write_large_diamond_righthalfroof_L199:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L200
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L200:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L201
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L202
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L202:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L203
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L204
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L205
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L206
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L206:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L207
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L208
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L208:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L209
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L209:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L210
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfroof_L210:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L211
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfroof_L211:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L212
    mov byte ptr [edi + 118eh], al
write_large_diamond_righthalfroof_L212:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L213
    mov byte ptr [edi + 118fh], al
write_large_diamond_righthalfroof_L213:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L214
    mov byte ptr [edi + 1410h], al
write_large_diamond_righthalfroof_L214:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L215
    mov byte ptr [edi + 1411h], al
write_large_diamond_righthalfroof_L215:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L216
    mov byte ptr [edi + 1692h], al
write_large_diamond_righthalfroof_L216:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L217
    mov byte ptr [edi + 1693h], al
write_large_diamond_righthalfroof_L217:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L218
    mov byte ptr [edi + 1914h], al
write_large_diamond_righthalfroof_L218:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L219
    mov byte ptr [edi + 1915h], al
write_large_diamond_righthalfroof_L219:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L220
    mov byte ptr [edi + 1b96h], al
write_large_diamond_righthalfroof_L220:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L221
    mov byte ptr [edi + 1b97h], al
write_large_diamond_righthalfroof_L221:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L222
    mov byte ptr [edi + 1e18h], al
write_large_diamond_righthalfroof_L222:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L223
    mov byte ptr [edi + 1e19h], al
write_large_diamond_righthalfroof_L223:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L224
    mov byte ptr [edi + 209ah], al
write_large_diamond_righthalfroof_L224:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L225
    mov byte ptr [edi + 209bh], al
write_large_diamond_righthalfroof_L225:
    inc esi
    add esi, 2
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_righthalfroof_L258
write_large_diamond_righthalfroof_L226:
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_righthalfroof_L229
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L227
    mov byte ptr [edi], al
write_large_diamond_righthalfroof_L227:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L228
    mov byte ptr [edi + 1], al
write_large_diamond_righthalfroof_L228:
    inc esi
write_large_diamond_righthalfroof_L229:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L230
    mov byte ptr [edi + 282h], al
write_large_diamond_righthalfroof_L230:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L231
    mov byte ptr [edi + 283h], al
write_large_diamond_righthalfroof_L231:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L232
    mov byte ptr [edi + 504h], al
write_large_diamond_righthalfroof_L232:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L233
    mov byte ptr [edi + 505h], al
write_large_diamond_righthalfroof_L233:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L234
    mov byte ptr [edi + 786h], al
write_large_diamond_righthalfroof_L234:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L235
    mov byte ptr [edi + 787h], al
write_large_diamond_righthalfroof_L235:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L236
    mov byte ptr [edi + 0a08h], al
write_large_diamond_righthalfroof_L236:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L237
    mov byte ptr [edi + 0a09h], al
write_large_diamond_righthalfroof_L237:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L238
    mov byte ptr [edi + 0c8ah], al
write_large_diamond_righthalfroof_L238:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L239
    mov byte ptr [edi + 0c8bh], al
write_large_diamond_righthalfroof_L239:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L240
    mov byte ptr [edi + 0f0ch], al
write_large_diamond_righthalfroof_L240:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L241
    mov byte ptr [edi + 0f0dh], al
write_large_diamond_righthalfroof_L241:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L242
    mov byte ptr [edi + 118eh], al
write_large_diamond_righthalfroof_L242:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L243
    mov byte ptr [edi + 118fh], al
write_large_diamond_righthalfroof_L243:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L244
    mov byte ptr [edi + 1410h], al
write_large_diamond_righthalfroof_L244:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L245
    mov byte ptr [edi + 1411h], al
write_large_diamond_righthalfroof_L245:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L246
    mov byte ptr [edi + 1692h], al
write_large_diamond_righthalfroof_L246:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L247
    mov byte ptr [edi + 1693h], al
write_large_diamond_righthalfroof_L247:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L248
    mov byte ptr [edi + 1914h], al
write_large_diamond_righthalfroof_L248:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L249
    mov byte ptr [edi + 1915h], al
write_large_diamond_righthalfroof_L249:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L250
    mov byte ptr [edi + 1b96h], al
write_large_diamond_righthalfroof_L250:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L251
    mov byte ptr [edi + 1b97h], al
write_large_diamond_righthalfroof_L251:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L252
    mov byte ptr [edi + 1e18h], al
write_large_diamond_righthalfroof_L252:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L253
    mov byte ptr [edi + 1e19h], al
write_large_diamond_righthalfroof_L253:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L254
    mov byte ptr [edi + 209ah], al
write_large_diamond_righthalfroof_L254:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L255
    mov byte ptr [edi + 209bh], al
write_large_diamond_righthalfroof_L255:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L256
    mov byte ptr [edi + 231ch], al
write_large_diamond_righthalfroof_L256:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_righthalfroof_L257
    mov byte ptr [edi + 231dh], al
write_large_diamond_righthalfroof_L257:
    inc esi
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_large_diamond_righthalfroof_L226
write_large_diamond_righthalfroof_L258:
    popad
    ret

; ════════════════════════════════════════════════════════════
; write_large_diamond_lefthalfroof
; ════════════════════════════════════════════════════════════
write_large_diamond_lefthalfroof_:
    pushad
    mov esi, eax
    mov dword ptr [_sndinit + 6], edx
    mov ecx, dword ptr [_y_length]
    add esi, dword ptr [_sprite_hat_start]
    mov edi, dword ptr [_internal_screen]
    add edi, dword ptr [_sprite_x]
    mov eax, dword ptr [_sprite_y]
    mov edx, dword ptr [_screen_width]
    mul edx
    add edi, eax
    add esi, 1eh
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L3
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L1
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L1:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L2
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L2:
    inc esi
write_large_diamond_lefthalfroof_L3:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 1ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L4
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L4:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L5
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L5:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L8
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L6
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L6:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L7
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L7:
    inc esi
write_large_diamond_lefthalfroof_L8:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 18h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L9
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L9:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L10
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L10:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L11
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L11:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L12
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L12:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L15
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L13
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L13:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L14
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L14:
    inc esi
write_large_diamond_lefthalfroof_L15:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 16h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L16
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L16:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L17
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L17:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L18
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L18:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L19
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L19:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L20
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L20:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L21
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L21:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L24
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L22
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L22:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L23
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L23:
    inc esi
write_large_diamond_lefthalfroof_L24:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 14h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L25
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L25:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L26
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L26:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L27
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L27:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L28
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L28:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L29
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L29:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L30
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L30:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L31
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L31:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L32
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L32:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L35
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L33
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L33:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L34
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L34:
    inc esi
write_large_diamond_lefthalfroof_L35:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 12h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L36
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L36:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L37
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L37:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L38
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L38:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L39
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L39:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L40
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L40:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L41
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L41:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L42
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L42:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L43
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L43:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L44
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L44:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L45
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L45:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L48
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L46
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L46:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L47
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L47:
    inc esi
write_large_diamond_lefthalfroof_L48:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 10h
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L49
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthalfroof_L49:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L50
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthalfroof_L50:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L51
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L51:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L52
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L52:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L53
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L53:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L54
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L54:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L55
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L55:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L56
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L56:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L57
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L57:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L58
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L58:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L59
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L59:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L60
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L60:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L63
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L61
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L61:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L62
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L62:
    inc esi
write_large_diamond_lefthalfroof_L63:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 0eh
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L64
    mov byte ptr [edi + 118eh], al
write_large_diamond_lefthalfroof_L64:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L65
    mov byte ptr [edi + 118fh], al
write_large_diamond_lefthalfroof_L65:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L66
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthalfroof_L66:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L67
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthalfroof_L67:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L68
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L68:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L69
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L69:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L70
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L70:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L71
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L71:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L72
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L72:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L73
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L73:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L74
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L74:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L75
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L75:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L76
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L76:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L77
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L77:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L80
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L78
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L78:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L79
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L79:
    inc esi
write_large_diamond_lefthalfroof_L80:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 0ch
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L81
    mov byte ptr [edi + 140ch], al
write_large_diamond_lefthalfroof_L81:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L82
    mov byte ptr [edi + 140dh], al
write_large_diamond_lefthalfroof_L82:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L83
    mov byte ptr [edi + 118eh], al
write_large_diamond_lefthalfroof_L83:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L84
    mov byte ptr [edi + 118fh], al
write_large_diamond_lefthalfroof_L84:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L85
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthalfroof_L85:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L86
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthalfroof_L86:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L87
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L87:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L88
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L88:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L89
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L89:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L90
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L90:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L91
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L91:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L92
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L92:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L93
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L93:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L94
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L94:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L95
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L95:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L96
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L96:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L99
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L97
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L97:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L98
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L98:
    inc esi
write_large_diamond_lefthalfroof_L99:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 0ah
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L100
    mov byte ptr [edi + 168ah], al
write_large_diamond_lefthalfroof_L100:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L101
    mov byte ptr [edi + 168bh], al
write_large_diamond_lefthalfroof_L101:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L102
    mov byte ptr [edi + 140ch], al
write_large_diamond_lefthalfroof_L102:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L103
    mov byte ptr [edi + 140dh], al
write_large_diamond_lefthalfroof_L103:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L104
    mov byte ptr [edi + 118eh], al
write_large_diamond_lefthalfroof_L104:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L105
    mov byte ptr [edi + 118fh], al
write_large_diamond_lefthalfroof_L105:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L106
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthalfroof_L106:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L107
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthalfroof_L107:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L108
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L108:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L109
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L109:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L110
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L110:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L111
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L111:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L112
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L112:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L113
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L113:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L114
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L114:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L115
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L115:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L116
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L116:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L117
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L117:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L120
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L118
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L118:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L119
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L119:
    inc esi
write_large_diamond_lefthalfroof_L120:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 8
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L121
    mov byte ptr [edi + 1908h], al
write_large_diamond_lefthalfroof_L121:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L122
    mov byte ptr [edi + 1909h], al
write_large_diamond_lefthalfroof_L122:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L123
    mov byte ptr [edi + 168ah], al
write_large_diamond_lefthalfroof_L123:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L124
    mov byte ptr [edi + 168bh], al
write_large_diamond_lefthalfroof_L124:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L125
    mov byte ptr [edi + 140ch], al
write_large_diamond_lefthalfroof_L125:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L126
    mov byte ptr [edi + 140dh], al
write_large_diamond_lefthalfroof_L126:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L127
    mov byte ptr [edi + 118eh], al
write_large_diamond_lefthalfroof_L127:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L128
    mov byte ptr [edi + 118fh], al
write_large_diamond_lefthalfroof_L128:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L129
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthalfroof_L129:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L130
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthalfroof_L130:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L131
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L131:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L132
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L132:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L133
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L133:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L134
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L134:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L135
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L135:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L136
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L136:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L137
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L137:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L138
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L138:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L139
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L139:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L140
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L140:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L143
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L141
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L141:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L142
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L142:
    inc esi
write_large_diamond_lefthalfroof_L143:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 6
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L144
    mov byte ptr [edi + 1b86h], al
write_large_diamond_lefthalfroof_L144:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L145
    mov byte ptr [edi + 1b87h], al
write_large_diamond_lefthalfroof_L145:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L146
    mov byte ptr [edi + 1908h], al
write_large_diamond_lefthalfroof_L146:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L147
    mov byte ptr [edi + 1909h], al
write_large_diamond_lefthalfroof_L147:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L148
    mov byte ptr [edi + 168ah], al
write_large_diamond_lefthalfroof_L148:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L149
    mov byte ptr [edi + 168bh], al
write_large_diamond_lefthalfroof_L149:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L150
    mov byte ptr [edi + 140ch], al
write_large_diamond_lefthalfroof_L150:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L151
    mov byte ptr [edi + 140dh], al
write_large_diamond_lefthalfroof_L151:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L152
    mov byte ptr [edi + 118eh], al
write_large_diamond_lefthalfroof_L152:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L153
    mov byte ptr [edi + 118fh], al
write_large_diamond_lefthalfroof_L153:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L154
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthalfroof_L154:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L155
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthalfroof_L155:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L156
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L156:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L157
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L157:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L158
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L158:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L159
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L159:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L160
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L160:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L161
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L161:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L162
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L162:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L163
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L163:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L164
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L164:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L165
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L165:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L168
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L166
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L166:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L167
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L167:
    inc esi
write_large_diamond_lefthalfroof_L168:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 4
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L169
    mov byte ptr [edi + 1e04h], al
write_large_diamond_lefthalfroof_L169:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L170
    mov byte ptr [edi + 1e05h], al
write_large_diamond_lefthalfroof_L170:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L171
    mov byte ptr [edi + 1b86h], al
write_large_diamond_lefthalfroof_L171:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L172
    mov byte ptr [edi + 1b87h], al
write_large_diamond_lefthalfroof_L172:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L173
    mov byte ptr [edi + 1908h], al
write_large_diamond_lefthalfroof_L173:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L174
    mov byte ptr [edi + 1909h], al
write_large_diamond_lefthalfroof_L174:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L175
    mov byte ptr [edi + 168ah], al
write_large_diamond_lefthalfroof_L175:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L176
    mov byte ptr [edi + 168bh], al
write_large_diamond_lefthalfroof_L176:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L177
    mov byte ptr [edi + 140ch], al
write_large_diamond_lefthalfroof_L177:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L178
    mov byte ptr [edi + 140dh], al
write_large_diamond_lefthalfroof_L178:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L179
    mov byte ptr [edi + 118eh], al
write_large_diamond_lefthalfroof_L179:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L180
    mov byte ptr [edi + 118fh], al
write_large_diamond_lefthalfroof_L180:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L181
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthalfroof_L181:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L182
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthalfroof_L182:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L183
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L183:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L184
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L184:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L185
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L185:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L186
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L186:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L187
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L187:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L188
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L188:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L189
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L189:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L190
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L190:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L191
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L191:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L192
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L192:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L195
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L193
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L193:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L194
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L194:
    inc esi
write_large_diamond_lefthalfroof_L195:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
    add esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L196
    mov byte ptr [edi + 2082h], al
write_large_diamond_lefthalfroof_L196:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L197
    mov byte ptr [edi + 2083h], al
write_large_diamond_lefthalfroof_L197:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L198
    mov byte ptr [edi + 1e04h], al
write_large_diamond_lefthalfroof_L198:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L199
    mov byte ptr [edi + 1e05h], al
write_large_diamond_lefthalfroof_L199:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L200
    mov byte ptr [edi + 1b86h], al
write_large_diamond_lefthalfroof_L200:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L201
    mov byte ptr [edi + 1b87h], al
write_large_diamond_lefthalfroof_L201:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L202
    mov byte ptr [edi + 1908h], al
write_large_diamond_lefthalfroof_L202:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L203
    mov byte ptr [edi + 1909h], al
write_large_diamond_lefthalfroof_L203:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L204
    mov byte ptr [edi + 168ah], al
write_large_diamond_lefthalfroof_L204:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L205
    mov byte ptr [edi + 168bh], al
write_large_diamond_lefthalfroof_L205:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L206
    mov byte ptr [edi + 140ch], al
write_large_diamond_lefthalfroof_L206:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L207
    mov byte ptr [edi + 140dh], al
write_large_diamond_lefthalfroof_L207:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L208
    mov byte ptr [edi + 118eh], al
write_large_diamond_lefthalfroof_L208:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L209
    mov byte ptr [edi + 118fh], al
write_large_diamond_lefthalfroof_L209:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L210
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthalfroof_L210:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L211
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthalfroof_L211:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L212
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L212:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L213
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L213:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L214
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L214:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L215
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L215:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L216
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L216:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L217
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L217:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L218
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L218:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L219
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L219:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L220
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L220:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L221
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L221:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L224
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L222
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L222:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L223
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L223:
    inc esi
write_large_diamond_lefthalfroof_L224:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jle near ptr write_large_diamond_lefthalfroof_L257
write_large_diamond_lefthalfroof_L225:
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L226
    mov byte ptr [edi + 2300h], al
write_large_diamond_lefthalfroof_L226:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L227
    mov byte ptr [edi + 2301h], al
write_large_diamond_lefthalfroof_L227:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L228
    mov byte ptr [edi + 2082h], al
write_large_diamond_lefthalfroof_L228:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L229
    mov byte ptr [edi + 2083h], al
write_large_diamond_lefthalfroof_L229:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L230
    mov byte ptr [edi + 1e04h], al
write_large_diamond_lefthalfroof_L230:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L231
    mov byte ptr [edi + 1e05h], al
write_large_diamond_lefthalfroof_L231:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L232
    mov byte ptr [edi + 1b86h], al
write_large_diamond_lefthalfroof_L232:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L233
    mov byte ptr [edi + 1b87h], al
write_large_diamond_lefthalfroof_L233:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L234
    mov byte ptr [edi + 1908h], al
write_large_diamond_lefthalfroof_L234:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L235
    mov byte ptr [edi + 1909h], al
write_large_diamond_lefthalfroof_L235:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L236
    mov byte ptr [edi + 168ah], al
write_large_diamond_lefthalfroof_L236:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L237
    mov byte ptr [edi + 168bh], al
write_large_diamond_lefthalfroof_L237:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L238
    mov byte ptr [edi + 140ch], al
write_large_diamond_lefthalfroof_L238:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L239
    mov byte ptr [edi + 140dh], al
write_large_diamond_lefthalfroof_L239:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L240
    mov byte ptr [edi + 118eh], al
write_large_diamond_lefthalfroof_L240:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L241
    mov byte ptr [edi + 118fh], al
write_large_diamond_lefthalfroof_L241:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L242
    mov byte ptr [edi + 0f10h], al
write_large_diamond_lefthalfroof_L242:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L243
    mov byte ptr [edi + 0f11h], al
write_large_diamond_lefthalfroof_L243:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L244
    mov byte ptr [edi + 0c92h], al
write_large_diamond_lefthalfroof_L244:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L245
    mov byte ptr [edi + 0c93h], al
write_large_diamond_lefthalfroof_L245:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L246
    mov byte ptr [edi + 0a14h], al
write_large_diamond_lefthalfroof_L246:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L247
    mov byte ptr [edi + 0a15h], al
write_large_diamond_lefthalfroof_L247:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L248
    mov byte ptr [edi + 796h], al
write_large_diamond_lefthalfroof_L248:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L249
    mov byte ptr [edi + 797h], al
write_large_diamond_lefthalfroof_L249:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L250
    mov byte ptr [edi + 518h], al
write_large_diamond_lefthalfroof_L250:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L251
    mov byte ptr [edi + 519h], al
write_large_diamond_lefthalfroof_L251:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L252
    mov byte ptr [edi + 29ah], al
write_large_diamond_lefthalfroof_L252:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L253
    mov byte ptr [edi + 29bh], al
write_large_diamond_lefthalfroof_L253:
    inc esi
    add esi, 2
    cmp dword ptr [_sndinit + 6], 2
    je write_large_diamond_lefthalfroof_L256
    sub esi, 2
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L254
    mov byte ptr [edi + 1ch], al
write_large_diamond_lefthalfroof_L254:
    inc esi
    mov al, byte ptr [esi]
    cmp al, 0
    je write_large_diamond_lefthalfroof_L255
    mov byte ptr [edi + 1dh], al
write_large_diamond_lefthalfroof_L255:
    inc esi
write_large_diamond_lefthalfroof_L256:
    sub edi, dword ptr [_screen_width]
    dec ecx
    cmp ecx, 0
    jg near ptr write_large_diamond_lefthalfroof_L225
write_large_diamond_lefthalfroof_L257:
    popad
    ret

_TEXT ENDS
END
