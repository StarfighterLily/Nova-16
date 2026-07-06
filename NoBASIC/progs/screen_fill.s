	.def	@feat.00;
	.scl	3;
	.type	0;
	.endef
	.globl	@feat.00
@feat.00 = 0
	.file	"screen_fill.ll"
	.def	main;
	.scl	2;
	.type	32;
	.endef
	.text
	.globl	main                            # -- Begin function main
	.p2align	4
main:                                   # @main
.seh_proc main
# %bb.0:                                # %entry
	pushq	%rbp
	.seh_pushreg %rbp
	subq	$48, %rsp
	.seh_stackalloc 48
	leaq	48(%rsp), %rbp
	.seh_setframe %rbp, 48
	.seh_endprologue
	movw	$1, %cx
	addw	$0, %cx
	subq	$32, %rsp
	callq	setlayer
	addq	$32, %rsp
	xorl	%eax, %eax
                                        # kill: def $ax killed $ax killed $eax
	addw	$0, %ax
	movw	g_z(%rip), %cx
	movw	%cx, -2(%rbp)
	movw	%ax, -2(%rbp)
	movw	%ax, g_z(%rip)
	xorl	%eax, %eax
                                        # kill: def $ax killed $ax killed $eax
	addw	$0, %ax
	movw	g_y(%rip), %cx
	movw	%cx, -4(%rbp)
	movw	%ax, -4(%rbp)
	movw	$255, %ax
	addw	$0, %ax
	movw	%ax, -6(%rbp)
	movw	$1, -8(%rbp)
.LBB0_1:                                # %for.cond.0
                                        # =>This Loop Header: Depth=1
                                        #     Child Loop BB0_3 Depth 2
	movw	-4(%rbp), %ax
	cmpw	-6(%rbp), %ax
	jg	.LBB0_6
# %bb.2:                                # %for.body.1
                                        #   in Loop: Header=BB0_1 Depth=1
	movl	$16, %eax
	movq	%rax, -32(%rbp)                 # 8-byte Spill
	callq	__chkstk
	subq	%rax, %rsp
	movq	-32(%rbp), %rax                 # 8-byte Reload
	movq	%rsp, %rcx
	movq	%rcx, %rdx
	movq	%rdx, -40(%rbp)                 # 8-byte Spill
	movw	g_x(%rip), %dx
	movw	%dx, (%rcx)
	movw	$0, (%rcx)
	callq	__chkstk
	subq	%rax, %rsp
	movq	-32(%rbp), %rax                 # 8-byte Reload
	movq	%rsp, %rcx
	movq	%rcx, %rdx
	movq	%rdx, -24(%rbp)                 # 8-byte Spill
	movw	$255, (%rcx)
	callq	__chkstk
	subq	%rax, %rsp
	movq	%rsp, %rax
	movq	%rax, -16(%rbp)                 # 8-byte Spill
	movw	$1, (%rax)
.LBB0_3:                                # %for.cond.3
                                        #   Parent Loop BB0_1 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movq	-24(%rbp), %rcx                 # 8-byte Reload
	movq	-40(%rbp), %rax                 # 8-byte Reload
	movw	(%rax), %ax
	cmpw	(%rcx), %ax
	jg	.LBB0_5
# %bb.4:                                # %for.body.4
                                        #   in Loop: Header=BB0_3 Depth=2
	movq	-40(%rbp), %rax                 # 8-byte Reload
	movw	(%rax), %cx
	movw	-4(%rbp), %dx
	movw	-2(%rbp), %r8w
	subq	$32, %rsp
	callq	pxlon
	movq	-16(%rbp), %rdx                 # 8-byte Reload
	movq	-40(%rbp), %rax                 # 8-byte Reload
	addq	$32, %rsp
	movw	-2(%rbp), %cx
	addw	$1, %cx
	movw	%cx, -2(%rbp)
	movw	(%rax), %cx
	addw	(%rdx), %cx
	movw	%cx, (%rax)
	jmp	.LBB0_3
.LBB0_5:                                # %for.end.5
                                        #   in Loop: Header=BB0_1 Depth=1
	movw	-4(%rbp), %ax
	addw	-8(%rbp), %ax
	movw	%ax, -4(%rbp)
	jmp	.LBB0_1
.LBB0_6:                                # %for.end.2
	xorl	%eax, %eax
	.seh_startepilogue
	movq	%rbp, %rsp
	popq	%rbp
	.seh_endepilogue
	retq
	.seh_endproc
                                        # -- End function
	.bss
	.globl	g_x                             # @g_x
	.p2align	1, 0x0
g_x:
	.short	0                               # 0x0

	.globl	g_y                             # @g_y
	.p2align	1, 0x0
g_y:
	.short	0                               # 0x0

	.globl	g_z                             # @g_z
	.p2align	1, 0x0
g_z:
	.short	0                               # 0x0

	.addrsig
	.addrsig_sym setlayer
	.addrsig_sym pxlon
	.addrsig_sym g_x
	.addrsig_sym g_y
	.addrsig_sym g_z
