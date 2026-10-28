__RINvMs0_NtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v115host_account_v1NtB6_13ReservationV111dispatch_v1NtB8_24AdmittedFixtureOutcomeV1NCNvB8_27run_one_admitted_fixture_v10EBg_:
Lfunc_begin701:
	.loc	40 134 0
	.cfi_startproc
	stp	x28, x27, [sp, #-32]!
	.cfi_def_cfa_offset 32
	stp	x29, x30, [sp, #16]
	add	x29, sp, #16
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w27, -24
	.cfi_offset w28, -32
	sub	x9, sp, #10, lsl #12
LBB701_1:
	.loc	1 0 0 is_stmt 0
	sub	sp, sp, #1, lsl #12
	ldr	xzr, [sp]
	cmp	sp, x9
	b.ne	LBB701_1
	sub	sp, sp, #32
	sub	x9, x29, #32
	str	x8, [sp, #24]
	str	x0, [sp, #32]
	mov	x8, x1
	str	x8, [sp, #40]
	mov	x1, x2
	str	x0, [x9]
	str	x8, [x9, #8]
Ltmp4668:
	add	x0, sp, #3, lsl #12
	add	x0, x0, #1392
	str	x0, [sp, #48]
Ltmp4669:
	.loc	40 138 21 is_stmt 1
	mov	w8, #48
	mov	x2, x8
	bl	_memcpy
Ltmp4670:
	.loc	40 0 21 is_stmt 0
	ldr	x0, [sp, #48]
	.loc	40 138 21
	add	x8, sp, #56
	bl	__RNCNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v127run_one_admitted_fixture_v10Bb_
	b	LBB701_3
LBB701_3:
Ltmp4671:
	.loc	40 139 38 is_stmt 1
	add	x1, sp, #56
	add	x0, sp, #6, lsl #12
	add	x0, x0, #2776
	str	x0, [sp]
	mov	w8, #13624
	mov	x2, x8
	str	x2, [sp, #16]
	bl	_memcpy
	ldr	x1, [sp]
	ldr	x2, [sp, #16]
	add	x0, sp, #3, lsl #12
	add	x0, x0, #1440
	str	x0, [sp, #8]
	.loc	40 139 33 is_stmt 0
	bl	_memcpy
	ldr	x0, [sp, #24]
	ldr	x1, [sp, #8]
	ldr	x2, [sp, #16]
	.loc	40 139 9
	bl	_memcpy
	ldr	x10, [sp, #32]
	ldr	x9, [sp, #24]
	ldr	x8, [sp, #40]
	str	x10, [x9, #13624]
	str	x8, [x9, #13632]
Ltmp4672:
	.loc	40 140 6 epilogue_begin is_stmt 1
	add	sp, sp, #10, lsl #12
	add	sp, sp, #32
	.cfi_def_cfa wsp, 32
	ldp	x29, x30, [sp, #16]
	ldp	x28, x27, [sp], #32
	.cfi_def_cfa_offset 0
	.cfi_restore w30
	.cfi_restore w29
	.cfi_restore w27
	.cfi_restore w28
	ret
Ltmp4673:
Lfunc_end701:
	.cfi_endproc
