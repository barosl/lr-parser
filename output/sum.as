	extern printf, scanf

	section .data
fmt_out: db '%d', 10, 0
fmt_in: db '%d', 0
var_0: dd 0
var_1: dd 0
var_2: dd 0
var_3: dd 0
var_4: dd 0
var_5: dd 0
var_6: dd 0
var_7: dd 0
buf_int: dd 0

	section .text

	global main
main:
	push ebp
	mov ebp, esp
	mov dword [var_2], 0
	mov dword eax, [var_2]
	mov dword [var_3], eax
	push buf_int
	push fmt_in
	call scanf
	add esp, 4*2
	mov eax, [buf_int]
	mov dword [var_4], eax
label_0:
	mov dword eax, [var_4]
	cmp eax, 0
	jnz label_1
	jmp label_2
label_1:
	mov dword eax, [var_3]
	mov edx, [var_4]
	add eax, edx
	mov dword [var_5], eax
	mov dword eax, [var_5]
	mov dword [var_3], eax
	mov dword [var_6], 1
	mov dword eax, [var_4]
	mov edx, [var_6]
	sub eax, edx
	mov dword [var_7], eax
	mov dword eax, [var_7]
	mov dword [var_4], eax
	jmp label_0
label_2:
	mov dword eax, [var_3]
	push eax
	push fmt_out
	call printf
	add esp, 4*2
	mov esp, ebp
	pop ebp
	mov eax, 0
	ret
