.section .rodata.editor_frame,"",@
.hidden editor_frame
.globl editor_frame
editor_frame:
.incbin "editor-frame.json"
.byte 0
.size editor_frame, .-editor_frame
