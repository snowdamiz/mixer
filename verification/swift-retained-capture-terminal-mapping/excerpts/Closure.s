__RNCNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v127run_one_admitted_fixture_v10Bb_:
Lfunc_begin3160:
	.loc	50 861 0 is_stmt 1
	.cfi_startproc
	sub	sp, sp, #48
	.cfi_def_cfa_offset 48
	stp	x29, x30, [sp, #32]
	add	x29, sp, #32
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	mov	x9, x0
Ltmp36776:
	.loc	50 861 71 prologue_end
	ldr	x0, [x9]
	.loc	50 861 80 is_stmt 0
	ldur	q0, [x9, #8]
	mov	x1, sp
	str	q0, [sp]
	ldur	q0, [x9, #24]
	str	q0, [sp, #16]
	.loc	50 861 89
	ldr	x2, [x9, #40]
	.loc	50 861 39
	bl	__RNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v131run_prepaid_admitted_fixture_v1
Ltmp36777:
	.cfi_def_cfa wsp, 48
	.loc	50 861 98 epilogue_begin
	ldp	x29, x30, [sp, #32]
	add	sp, sp, #48
	.cfi_def_cfa_offset 0
	.cfi_restore w30
	.cfi_restore w29
	ret
Ltmp36778:
Lfunc_end3160:
	.cfi_endproc
