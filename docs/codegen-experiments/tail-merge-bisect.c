/* Tests cross-function tail-merge:
 * Three sibling functions share a common tail (the call sequence to
 * cleanup_a + cleanup_b + return).  Does the compiler merge their
 * tails into one shared block?
 */

extern int  decision;
extern int  state;
extern void cleanup_a(void);
extern void cleanup_b(int x);
extern int  helper(int msg);

/* === Test 1: three wrappers with common tail-call to helper() === */
int wrap_alpha(void) {
    return helper(1);
}

int wrap_beta(void) {
    return helper(0x47);
}

int wrap_gamma(void) {
    return helper(0x5c);
}

/* === Test 2: cross-function tail-merge with shared cleanup === */
void op_one(void) {
    state = 1;
    cleanup_a();
    cleanup_b(state);
}

void op_two(void) {
    state = 2;
    cleanup_a();
    cleanup_b(state);
}

void op_three(void) {
    state = 3;
    cleanup_a();
    cleanup_b(state);
}

/* === Test 3: conditional tail-jump (like floop_end/gloop_end) === */
void floppy_op(void) {
    cleanup_a();
    if (decision != 0) {
        state = 0x15;
        cleanup_b(state);
        return;
    }
    cleanup_b(0);
}

void glop_op(void) {
    cleanup_a();
    cleanup_b(0);
}
