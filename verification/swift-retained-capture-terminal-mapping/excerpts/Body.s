__RNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v131run_prepaid_admitted_fixture_v1:
Lfunc_begin4876:
	.loc	50 863 0 is_stmt 1
	.cfi_startproc
	.cfi_personality 155, _rust_eh_personality
	.cfi_lsda 16, Lexception493
	stp	x28, x27, [sp, #-32]!
	.cfi_def_cfa_offset 32
	stp	x29, x30, [sp, #16]
	add	x29, sp, #16
	.cfi_def_cfa w29, 16
	.cfi_offset w30, -8
	.cfi_offset w29, -16
	.cfi_offset w27, -24
	.cfi_offset w28, -32
	.cfi_remember_state
	sub	x9, sp, #15, lsl #12
LBB4876_1:
	.loc	1 0 0 is_stmt 0
	sub	sp, sp, #1, lsl #12
	ldr	xzr, [sp]
	cmp	sp, x9
	b.ne	LBB4876_1
	sub	sp, sp, #2448
	ldr	xzr, [sp]
	sub	x9, x29, #95
	str	x9, [sp, #192]
	add	x9, sp, #4, lsl #12
	add	x9, x9, #2736
	str	x9, [sp, #160]
	mov	x9, x8
	ldr	x8, [sp, #192]
	str	x9, [sp, #168]
	mov	x9, x0
	str	x9, [sp, #200]
	mov	x0, x1
	str	x0, [sp, #176]
Ltmp67288:
	str	x2, [sp, #184]
	stur	x9, [x8, #7]
Ltmp67289:
	stur	x2, [x8, #15]
Ltmp67290:
	.loc	50 868 13 is_stmt 1
	strb	wzr, [x8, #6]
	strb	wzr, [x8, #5]
	strb	wzr, [x8, #4]
	strb	wzr, [x8, #3]
	strb	wzr, [x8, #2]
	strb	wzr, [x8, #1]
	strb	wzr, [x8]
	.loc	50 868 28 is_stmt 0
	bl	__RNvMs6_NtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v1NtB5_27PrepaidCorrelationAttemptV116original_root_v1
Ltmp67291:
	.loc	50 0 28
	ldr	x8, [sp, #192]
	.loc	50 868 28
	mov	x9, x0
	ldr	x0, [sp, #200]
	str	x9, [sp, #208]
	stur	x9, [x8, #23]
Ltmp67292:
	.loc	50 869 23 is_stmt 1
	stur	x0, [x8, #31]
	add	x8, sp, #256
Ltmp67293:
	.loc	50 870 62
	bl	__RNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v119setup_files_once_v1
	ldr	w8, [sp, #256]
Ltmp67294:
	.loc	50 870 56 is_stmt 0
	cbz	x8, LBB4876_3
	b	LBB4876_4
Ltmp67295:
LBB4876_3:
	.loc	50 0 56
	ldr	x9, [sp, #192]
	.loc	50 871 37 is_stmt 1
	ldr	w13, [sp, #260]
	stur	w13, [x9, #43]
	.loc	50 871 45 is_stmt 0
	ldr	w12, [sp, #264]
	stur	w12, [x9, #47]
	.loc	50 871 52
	ldr	w11, [sp, #268]
	stur	w11, [x9, #51]
	.loc	50 871 61
	ldr	w10, [sp, #272]
	stur	w10, [x9, #55]
	.loc	50 871 67
	ldr	w8, [sp, #276]
	stur	w8, [x9, #59]
Ltmp67296:
	.loc	50 871 81
	str	w13, [sp, #236]
	str	w12, [sp, #240]
	str	w11, [sp, #244]
	str	w10, [sp, #248]
	str	w8, [sp, #252]
	mov	w8, #1
Ltmp67297:
	.loc	50 870 14 is_stmt 1
	strb	w8, [x9, #6]
	ldr	w10, [sp, #236]
	str	w10, [sp, #216]
	.loc	50 870 22 is_stmt 0
	strb	w8, [x9, #5]
	ldr	w10, [sp, #240]
	str	w10, [sp, #220]
	.loc	50 870 29
	strb	w8, [x9, #4]
	ldr	w10, [sp, #244]
	str	w10, [sp, #224]
	.loc	50 870 38
	strb	w8, [x9, #3]
	ldr	w10, [sp, #248]
	str	w10, [sp, #228]
	.loc	50 870 44
	strb	w8, [x9, #2]
	ldr	w8, [sp, #252]
	str	w8, [sp, #232]
	.loc	50 873 10 is_stmt 1
	ldr	w8, [sp, #256]
	cbz	x8, LBB4876_5
	b	LBB4876_6
Ltmp67298:
LBB4876_4:
	.loc	50 872 13
	add	x1, sp, #256
	add	x0, sp, #296
	str	x0, [sp, #128]
	mov	w8, #40
	mov	x2, x8
	str	x2, [sp, #144]
	bl	_memcpy
	ldr	x1, [sp, #128]
	ldr	x2, [sp, #144]
	add	x0, sp, #3, lsl #12
	add	x0, x0, #1664
	str	x0, [sp, #136]
Ltmp67299:
	.loc	50 872 106 is_stmt 0
	bl	_memcpy
	ldr	x1, [sp, #136]
	ldr	x2, [sp, #144]
	add	x8, sp, #336
	str	x8, [sp, #152]
	.loc	50 872 67
	add	x0, x8, #8
	bl	_memcpy
	ldr	x0, [sp, #168]
	ldr	x1, [sp, #152]
	mov	x8, #-1
	str	x8, [sp, #336]
	.loc	50 872 31
	mov	w8, #13616
	mov	x2, x8
	bl	_memcpy
	ldr	x8, [sp, #208]
	ldr	x9, [sp, #168]
	str	x8, [x9, #13616]
Ltmp67300:
	.loc	50 883 6 is_stmt 1
	b	LBB4876_22
Ltmp67301:
LBB4876_5:
Ltmp67249:
	.loc	50 874 28
	bl	__RNvXs2_NtCscBrn2zMo5wc_8mixer_vm7executeNtB5_12CancellationNtNtCsjIpoRzUjyHQ_4core7default7Default7defaultB7_
	str	x0, [sp, #120]
Ltmp67250:
	b	LBB4876_9
Ltmp67302:
LBB4876_6:
Ltmp67247:
	.loc	50 873 10
	add	x0, sp, #256
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v114SetupOutcomeV1EBL_
Ltmp67248:
	b	LBB4876_5
Ltmp67303:
LBB4876_7:
	.loc	50 0 10 is_stmt 0
	ldr	x8, [sp, #192]
	.loc	50 883 5 is_stmt 1
	ldrb	w8, [x8, #2]
	tbnz	w8, #0, LBB4876_29
	b	LBB4876_28
Ltmp67304:
LBB4876_8:
Ltmp67251:
	.loc	50 0 5 is_stmt 0
	ldr	x9, [sp, #192]
	stur	x0, [x9, #63]
	mov	x8, x1
	stur	w8, [x9, #71]
	b	LBB4876_7
Ltmp67305:
LBB4876_9:
	ldr	x8, [sp, #200]
	ldr	x9, [sp, #192]
	ldr	x10, [sp, #120]
	add	x11, sp, #3, lsl #12
	add	x11, x11, #1704
	str	x11, [sp, #112]
Ltmp67306:
	.loc	50 874 28 is_stmt 1
	str	x10, [sp, #13992]
Ltmp67307:
	.loc	50 875 13
	mov	w10, #1
	strb	w10, [x9, #1]
	.loc	50 875 67 is_stmt 0
	strb	wzr, [x9, #6]
	ldr	w10, [sp, #216]
	str	w10, [sp, #92]
	.loc	50 875 75
	strb	wzr, [x9, #5]
	ldr	w10, [sp, #220]
	str	w10, [sp, #96]
	.loc	50 875 82
	strb	wzr, [x9, #4]
	ldr	w9, [sp, #224]
	str	w9, [sp, #100]
	.loc	50 876 13 is_stmt 1
	add	x1, x8, #336
	add	x0, sp, #3, lsl #12
	add	x0, x0, #2976
	str	x0, [sp, #104]
	mov	w8, #40
	mov	x2, x8
	bl	_memcpy
	ldr	w0, [sp, #92]
	ldr	w1, [sp, #96]
	ldr	w2, [sp, #100]
	ldr	x3, [sp, #104]
	ldr	x4, [sp, #112]
Ltmp67252:
	.loc	50 875 33
	add	x8, sp, #3, lsl #12
	add	x8, x8, #1712
	bl	__RNvNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v133load_selected_retained_profile_v1
Ltmp67253:
	b	LBB4876_12
Ltmp67308:
LBB4876_10:
	.loc	50 0 33 is_stmt 0
	ldr	x8, [sp, #192]
	.loc	50 883 5 is_stmt 1
	ldrb	w8, [x8, #1]
	tbnz	w8, #0, LBB4876_27
	b	LBB4876_7
Ltmp67309:
LBB4876_11:
Ltmp67258:
	.loc	50 0 5 is_stmt 0
	ldr	x9, [sp, #192]
	stur	x0, [x9, #63]
	mov	x8, x1
	stur	w8, [x9, #71]
	b	LBB4876_10
Ltmp67310:
LBB4876_12:
	.loc	50 877 76 is_stmt 1
	add	x1, sp, #3, lsl #12
	add	x1, x1, #1712
	add	x0, sp, #4, lsl #12
	add	x0, x0, #184
	str	x0, [sp, #80]
	mov	w8, #1264
	mov	x2, x8
	bl	_memcpy
	ldr	x0, [sp, #80]
Ltmp67254:
	.loc	50 877 32 is_stmt 0
	add	x8, sp, #3, lsl #12
	add	x8, x8, #3016
	bl	__RNvMs9_NtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v1NtB5_23SuppliedLoaderCarrierV118retain_complete_v1
Ltmp67255:
	b	LBB4876_13
Ltmp67311:
LBB4876_13:
	.loc	50 0 32
	ldr	x8, [sp, #160]
	ldr	x9, [sp, #176]
Ltmp67312:
	.loc	50 878 55 is_stmt 1
	ldr	q0, [x9]
	add	x10, sp, #4, lsl #12
	add	x10, x10, #2736
	str	x10, [sp, #64]
	str	q0, [x8]
	ldr	q0, [x9, #16]
	str	q0, [x8, #16]
	.loc	50 878 64 is_stmt 0
	add	x1, sp, #3, lsl #12
	add	x1, x1, #3016
	add	x0, sp, #4, lsl #12
	add	x0, x0, #2768
	str	x0, [sp, #72]
	mov	w8, #1264
	mov	x2, x8
	bl	_memcpy
	ldr	x0, [sp, #64]
	ldr	x1, [sp, #72]
	ldr	x2, [sp, #184]
Ltmp67256:
	.loc	50 878 26
	add	x8, sp, #4, lsl #12
	add	x8, x8, #1448
	bl	__RNvNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v128correlate_admitted_loader_v1
Ltmp67257:
	b	LBB4876_14
Ltmp67313:
LBB4876_14:
	.loc	50 0 26
	ldr	x8, [sp, #200]
	ldr	x9, [sp, #192]
	ldr	x11, [sp, #160]
	.loc	50 878 90
	mov	w10, #1
	strb	w10, [x9]
Ltmp67314:
	.loc	50 879 45 is_stmt 1
	strb	wzr, [x9, #3]
	ldr	w10, [sp, #228]
	str	w10, [x11, #1720]
	.loc	50 879 51 is_stmt 0
	strb	wzr, [x9, #2]
	ldr	w10, [sp, #232]
	str	w10, [x11, #1724]
	.loc	50 879 61
	strb	wzr, [x9, #1]
	ldr	x9, [sp, #13992]
	str	x9, [sp, #20848]
	.loc	50 880 36 is_stmt 1
	add	x0, x8, #80
Ltmp67259:
	.loc	50 880 21 is_stmt 0
	add	x8, sp, #5, lsl #12
	add	x8, x8, #376
	bl	__RNvNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor5cache18initial_profile_v135trusted_local_host_account_entry_v114copy_claims_v1
Ltmp67260:
	b	LBB4876_17
Ltmp67315:
LBB4876_15:
Ltmp67264:
	.loc	50 880 110
	add	x0, sp, #5, lsl #12
	add	x0, x0, #368
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCscBrn2zMo5wc_8mixer_vm7execute12CancellationEBF_
Ltmp67265:
	b	LBB4876_24
Ltmp67316:
LBB4876_16:
Ltmp67263:
	.loc	50 0 110
	ldr	x9, [sp, #192]
	stur	x0, [x9, #63]
	mov	x8, x1
	stur	w8, [x9, #71]
	b	LBB4876_15
Ltmp67317:
LBB4876_17:
	ldr	x8, [sp, #200]
	.loc	50 880 62
	add	x1, x8, #376
	add	x0, sp, #5, lsl #12
	add	x0, x0, #632
	mov	w8, #136
	mov	x2, x8
	bl	_memcpy
Ltmp67261:
	.loc	50 880 95
	bl	__RNvMNtCs1SSuMAdGM58_3std4timeNtB2_7Instant3now
	str	x0, [sp, #48]
	str	w1, [sp, #60]
Ltmp67262:
	b	LBB4876_18
Ltmp67318:
LBB4876_18:
	.loc	50 0 95
	ldr	x10, [sp, #160]
	.loc	50 879 20 is_stmt 1
	ldr	w9, [x10, #1720]
	add	x8, sp, #4, lsl #12
	add	x8, x8, #4032
	str	x8, [sp, #24]
	str	w9, [x10, #1712]
	ldr	w9, [x10, #1724]
	str	w9, [x10, #1716]
	ldr	x9, [sp, #20848]
	str	x9, [sp, #20432]
	add	x0, x8, #24
	add	x1, sp, #5, lsl #12
	add	x1, x1, #376
	mov	w8, #256
	mov	x2, x8
	bl	_memcpy
	ldr	x8, [sp, #24]
	add	x0, x8, #280
	add	x1, sp, #5, lsl #12
	add	x1, x1, #632
	mov	w8, #136
	mov	x2, x8
	bl	_memcpy
	ldr	x11, [sp, #48]
	ldr	x10, [sp, #160]
	ldr	w9, [sp, #60]
	ldr	x8, [sp, #192]
	str	x11, [sp, #20416]
	str	w9, [x10, #1304]
Ltmp67319:
	.loc	50 881 24
	strb	wzr, [x8]
	add	x1, sp, #4, lsl #12
	add	x1, x1, #1448
	add	x0, sp, #8, lsl #12
	add	x0, x0, #2096
	str	x0, [sp, #32]
	mov	w8, #1288
	mov	x2, x8
	bl	_memcpy
	ldr	x1, [sp, #24]
	add	x0, sp, #8, lsl #12
	add	x0, x0, #3384
	str	x0, [sp, #40]
	.loc	50 881 55 is_stmt 0
	mov	w8, #424
	mov	x2, x8
	bl	_memcpy
	ldr	x0, [sp, #32]
	ldr	x1, [sp, #40]
Ltmp67270:
	.loc	50 881 35
	add	x8, sp, #5, lsl #12
	add	x8, x8, #768
	bl	__RNvMse_NtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v1NtB5_25OwnedCorrelationOutcomeV119run_fixture_once_v1
Ltmp67271:
	b	LBB4876_21
Ltmp67320:
LBB4876_19:
	.loc	50 0 35
	ldr	x8, [sp, #192]
	.loc	50 883 5 is_stmt 1
	ldrb	w8, [x8]
	tbnz	w8, #0, LBB4876_26
	b	LBB4876_10
Ltmp67321:
LBB4876_20:
Ltmp67272:
	.loc	50 0 5 is_stmt 0
	ldr	x9, [sp, #192]
	stur	x0, [x9, #63]
	mov	x8, x1
	stur	w8, [x9, #71]
	b	LBB4876_19
Ltmp67322:
LBB4876_21:
	.loc	50 882 78 is_stmt 1
	add	x1, sp, #5, lsl #12
	add	x1, x1, #768
	add	x0, sp, #12, lsl #12
	add	x0, x0, #1040
	str	x0, [sp]
	mov	w8, #13616
	mov	x2, x8
	str	x2, [sp, #16]
	bl	_memcpy
	ldr	x1, [sp]
	ldr	x2, [sp, #16]
	add	x0, sp, #8, lsl #12
	add	x0, x0, #3808
	str	x0, [sp, #8]
	.loc	50 882 45 is_stmt 0
	bl	_memcpy
	ldr	x0, [sp, #168]
	ldr	x1, [sp, #8]
	ldr	x2, [sp, #16]
	.loc	50 882 9
	bl	_memcpy
	ldr	x9, [sp, #208]
	ldr	x10, [sp, #168]
	ldr	x8, [sp, #192]
	str	x9, [x10, #13616]
Ltmp67323:
	.loc	50 883 5 is_stmt 1
	strb	wzr, [x8]
Ltmp67324:
	.loc	50 883 5 is_stmt 0
	strb	wzr, [x8, #1]
Ltmp67325:
	.loc	50 883 5
	strb	wzr, [x8, #2]
	strb	wzr, [x8, #3]
	strb	wzr, [x8, #4]
	strb	wzr, [x8, #5]
	strb	wzr, [x8, #6]
Ltmp67326:
	.loc	50 883 6
	b	LBB4876_22
Ltmp67327:
LBB4876_22:
	.loc	50 883 6 epilogue_begin
	add	sp, sp, #15, lsl #12
Ltmp67328:
	add	sp, sp, #2448
	.cfi_def_cfa wsp, 32
	ldp	x29, x30, [sp, #16]
	ldp	x28, x27, [sp], #32
	.cfi_def_cfa_offset 0
	.cfi_restore w30
	.cfi_restore w29
	.cfi_restore w27
	.cfi_restore w28
	ret
LBB4876_23:
	.cfi_restore_state
Ltmp67329:
Ltmp67287:
	.loc	50 863 5 is_stmt 1
	bl	__RNvNtCsjIpoRzUjyHQ_4core9panicking16panic_in_cleanup
Ltmp67330:
LBB4876_24:
Ltmp67266:
	.loc	50 880 110
	add	x0, sp, #5, lsl #12
	add	x0, x0, #364
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm
Ltmp67267:
	b	LBB4876_25
Ltmp67331:
LBB4876_25:
Ltmp67268:
	add	x0, sp, #5, lsl #12
	add	x0, x0, #360
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm
Ltmp67269:
	b	LBB4876_19
Ltmp67332:
LBB4876_26:
Ltmp67273:
	.loc	50 883 5
	add	x0, sp, #4, lsl #12
	add	x0, x0, #1448
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtNtNtCscBrn2zMo5wc_8mixer_vm26experimental_swift_reactor26retained_profile_loader_v122prepaid_input_owner_v125OwnedCorrelationOutcomeV1EBJ_
Ltmp67274:
	b	LBB4876_10
Ltmp67333:
LBB4876_27:
Ltmp67275:
	.loc	50 883 5 is_stmt 0
	add	x0, sp, #3, lsl #12
	add	x0, x0, #1704
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCscBrn2zMo5wc_8mixer_vm7execute12CancellationEBF_
Ltmp67276:
	b	LBB4876_7
Ltmp67334:
LBB4876_28:
	.loc	50 0 5
	ldr	x8, [sp, #192]
	.loc	50 883 5
	ldrb	w8, [x8, #3]
	tbnz	w8, #0, LBB4876_31
	b	LBB4876_30
Ltmp67335:
LBB4876_29:
Ltmp67277:
	add	x0, sp, #232
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm
Ltmp67278:
	b	LBB4876_28
Ltmp67336:
LBB4876_30:
	.loc	50 0 5
	ldr	x8, [sp, #192]
	.loc	50 883 5
	ldrb	w8, [x8, #4]
	tbnz	w8, #0, LBB4876_33
	b	LBB4876_32
Ltmp67337:
LBB4876_31:
Ltmp67279:
	add	x0, sp, #228
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm
Ltmp67280:
	b	LBB4876_30
Ltmp67338:
LBB4876_32:
	.loc	50 0 5
	ldr	x8, [sp, #192]
	.loc	50 883 5
	ldrb	w8, [x8, #5]
	tbnz	w8, #0, LBB4876_35
	b	LBB4876_34
Ltmp67339:
LBB4876_33:
Ltmp67281:
	add	x0, sp, #224
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm
Ltmp67282:
	b	LBB4876_32
Ltmp67340:
LBB4876_34:
	.loc	50 0 5
	ldr	x8, [sp, #192]
	.loc	50 883 5
	ldrb	w8, [x8, #6]
	tbnz	w8, #0, LBB4876_37
	b	LBB4876_36
Ltmp67341:
LBB4876_35:
Ltmp67283:
	add	x0, sp, #220
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm
Ltmp67284:
	b	LBB4876_34
Ltmp67342:
LBB4876_36:
	.loc	50 0 5
	ldr	x8, [sp, #192]
	.loc	50 863 5 is_stmt 1
	ldur	x0, [x8, #63]
	bl	__Unwind_Resume
Ltmp67343:
LBB4876_37:
Ltmp67285:
	.loc	50 883 5
	add	x0, sp, #216
	bl	__RINvNtCsjIpoRzUjyHQ_4core3ptr9drop_glueNtNtCs1SSuMAdGM58_3std2fs4FileECscBrn2zMo5wc_8mixer_vm
Ltmp67286:
	b	LBB4876_36
Ltmp67344:
Lfunc_end4876:
	.cfi_endproc
