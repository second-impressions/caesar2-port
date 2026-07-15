"""bribe_emperor — gift re-read / split live-range research.

PS re-reads imperial_gift_level into EAX for the scattered single uses
(gift<avg, gift<trib, players-=, total+=) AND caches it in EDI only for
the dense `trib*N` comparison chain.  trib lives in ECX, rating in EBX,
imperial_favour in EBP.  Our default build CSEs `gift` into one EAX-kept
value, forcing trib*N→ECX, trib→EDX and cascading the whole function
(283 b diff).

bribe has NO calls, so an isolated single-TU compile reproduces the
regalloc exactly — this experiment hunts the source shape that makes
Watcom split/re-read gift the way PS did.

    uv run c2 cgex run bribe_grind
    uv run c2 cgex run bribe_grind --trial baseline
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="bribe_grind",
    ps_function="bribe_emperor",
    chk=False,
    prelude="""
extern int imperial_gift_level;
extern int av_imperial_gift_level;
extern int tribute;
extern int players_denarii;
extern int imperial_favour;
extern int month;
extern int final_bribe;
extern unsigned char warned_of_emperor_reply_month;
extern unsigned char warned_of_emperor_reply_level;
extern int total_amount_of_bribes;
extern int total_no_of_bribes;
""",
    extra_defs="""
int imperial_gift_level;
int av_imperial_gift_level;
int tribute;
int players_denarii;
int imperial_favour;
int month;
int final_bribe;
unsigned char warned_of_emperor_reply_month;
unsigned char warned_of_emperor_reply_level;
int total_amount_of_bribes;
int total_no_of_bribes;
""",
)

# ── baseline: current decomp source ───────────────────────────────
exp.add(
    "baseline",
    """
void bribe_emperor(void)
{
    int rating, gift, trib, avg;
    gift = imperial_gift_level;
    avg = av_imperial_gift_level;
    if (gift < avg)        rating = -1;
    else if (gift == avg)  rating = 0;
    else                   rating = 1;

    trib = tribute;
    if (gift < trib) {
        rating--;
    } else if (gift > trib) {
        if (gift >= trib * 10)     rating += 6;
        else if (gift >= trib * 7) rating += 5;
        else if (gift >= trib * 5) rating += 4;
        else if (gift >= trib * 3) rating += 3;
        else if (gift >= trib * 2) rating += 2;
        else                       rating++;
    }

    players_denarii -= gift;
    imperial_favour += rating * 10;
    if (imperial_favour < 0)   imperial_favour = 0;
    if (imperial_favour > 200) imperial_favour = 200;

    if (rating <= -1) rating = -1;
    if (rating >= 5)  rating = 5;

    warned_of_emperor_reply_month = month + 2;
    if (warned_of_emperor_reply_month >= 12)
        warned_of_emperor_reply_month -= 12;
    warned_of_emperor_reply_month++;
    warned_of_emperor_reply_level = rating + 1;

    total_amount_of_bribes += gift;
    total_no_of_bribes++;
    av_imperial_gift_level = total_amount_of_bribes / total_no_of_bribes;

    if (final_bribe != 0) {
        if (rating <= -1) { final_bribe = 2; imperial_favour = 0; }
        else              { final_bribe = 0; }
    }
}
""",
    note="current decomp source (expect ~283 if cgex reproduces)",
)

# ── no-local: read the global directly everywhere ─────────────────
exp.add(
    "no-local",
    """
void bribe_emperor(void)
{
    int rating, trib;
    if (imperial_gift_level < av_imperial_gift_level)        rating = -1;
    else if (imperial_gift_level == av_imperial_gift_level)  rating = 0;
    else                                                     rating = 1;

    trib = tribute;
    if (imperial_gift_level < trib) {
        rating--;
    } else if (imperial_gift_level > trib) {
        if (imperial_gift_level >= trib * 10)     rating += 6;
        else if (imperial_gift_level >= trib * 7) rating += 5;
        else if (imperial_gift_level >= trib * 5) rating += 4;
        else if (imperial_gift_level >= trib * 3) rating += 3;
        else if (imperial_gift_level >= trib * 2) rating += 2;
        else                                      rating++;
    }

    players_denarii -= imperial_gift_level;
    imperial_favour += rating * 10;
    if (imperial_favour < 0)   imperial_favour = 0;
    if (imperial_favour > 200) imperial_favour = 200;

    if (rating <= -1) rating = -1;
    if (rating >= 5)  rating = 5;

    warned_of_emperor_reply_month = month + 2;
    if (warned_of_emperor_reply_month >= 12)
        warned_of_emperor_reply_month -= 12;
    warned_of_emperor_reply_month++;
    warned_of_emperor_reply_level = rating + 1;

    total_amount_of_bribes += imperial_gift_level;
    total_no_of_bribes++;
    av_imperial_gift_level = total_amount_of_bribes / total_no_of_bribes;

    if (final_bribe != 0) {
        if (rating <= -1) { final_bribe = 2; imperial_favour = 0; }
        else              { final_bribe = 0; }
    }
}
""",
    note="no gift local; global read directly (CSE test)",
)

# ── split: local only for the dense chain (PS's EDI cache) ────────
exp.add(
    "split-chain",
    """
void bribe_emperor(void)
{
    int rating, trib;
    if (imperial_gift_level < av_imperial_gift_level)        rating = -1;
    else if (imperial_gift_level == av_imperial_gift_level)  rating = 0;
    else                                                     rating = 1;

    trib = tribute;
    if (imperial_gift_level < trib) {
        rating--;
    } else if (imperial_gift_level > trib) {
        int gift = imperial_gift_level;
        if (gift >= trib * 10)     rating += 6;
        else if (gift >= trib * 7) rating += 5;
        else if (gift >= trib * 5) rating += 4;
        else if (gift >= trib * 3) rating += 3;
        else if (gift >= trib * 2) rating += 2;
        else                       rating++;
    }

    players_denarii -= imperial_gift_level;
    imperial_favour += rating * 10;
    if (imperial_favour < 0)   imperial_favour = 0;
    if (imperial_favour > 200) imperial_favour = 200;

    if (rating <= -1) rating = -1;
    if (rating >= 5)  rating = 5;

    warned_of_emperor_reply_month = month + 2;
    if (warned_of_emperor_reply_month >= 12)
        warned_of_emperor_reply_month -= 12;
    warned_of_emperor_reply_month++;
    warned_of_emperor_reply_level = rating + 1;

    total_amount_of_bribes += imperial_gift_level;
    total_no_of_bribes++;
    av_imperial_gift_level = total_amount_of_bribes / total_no_of_bribes;

    if (final_bribe != 0) {
        if (rating <= -1) { final_bribe = 2; imperial_favour = 0; }
        else              { final_bribe = 0; }
    }
}
""",
    note="gift local only in the chain block; PS-style split",
)

# ── no-trib-local: read tribute inline (gift reads first at compare) ──
exp.add(
    "no-trib-local",
    """
void bribe_emperor(void)
{
    int rating;
    if (imperial_gift_level < av_imperial_gift_level)        rating = -1;
    else if (imperial_gift_level == av_imperial_gift_level)  rating = 0;
    else                                                     rating = 1;

    if (imperial_gift_level < tribute) {
        rating--;
    } else if (imperial_gift_level > tribute) {
        if (imperial_gift_level >= tribute * 10)     rating += 6;
        else if (imperial_gift_level >= tribute * 7) rating += 5;
        else if (imperial_gift_level >= tribute * 5) rating += 4;
        else if (imperial_gift_level >= tribute * 3) rating += 3;
        else if (imperial_gift_level >= tribute * 2) rating += 2;
        else                                         rating++;
    }

    players_denarii -= imperial_gift_level;
    imperial_favour += rating * 10;
    if (imperial_favour < 0)   imperial_favour = 0;
    if (imperial_favour > 200) imperial_favour = 200;

    if (rating <= -1) rating = -1;
    if (rating >= 5)  rating = 5;

    warned_of_emperor_reply_month = month + 2;
    if (warned_of_emperor_reply_month >= 12)
        warned_of_emperor_reply_month -= 12;
    warned_of_emperor_reply_month++;
    warned_of_emperor_reply_level = rating + 1;

    total_amount_of_bribes += imperial_gift_level;
    total_no_of_bribes++;
    av_imperial_gift_level = total_amount_of_bribes / total_no_of_bribes;

    if (final_bribe != 0) {
        if (rating <= -1) { final_bribe = 2; imperial_favour = 0; }
        else              { final_bribe = 0; }
    }
}
""",
    note="no gift OR trib local; both read inline (gift-first ordering)",
)

def _body(second_test):
    return """
void bribe_emperor(void)
{
    int rating;
    if (imperial_gift_level < av_imperial_gift_level)        rating = -1;
    else if (imperial_gift_level == av_imperial_gift_level)  rating = 0;
    else                                                     rating = 1;

    if (imperial_gift_level < tribute) {
        rating--;
    } else if (%s) {
        if (imperial_gift_level >= tribute * 10)     rating += 6;
        else if (imperial_gift_level >= tribute * 7) rating += 5;
        else if (imperial_gift_level >= tribute * 5) rating += 4;
        else if (imperial_gift_level >= tribute * 3) rating += 3;
        else if (imperial_gift_level >= tribute * 2) rating += 2;
        else                                         rating++;
    }

    players_denarii -= imperial_gift_level;
    imperial_favour += rating * 10;
    if (imperial_favour < 0)   imperial_favour = 0;
    if (imperial_favour > 200) imperial_favour = 200;
    if (rating <= -1) rating = -1;
    if (rating >= 5)  rating = 5;
    warned_of_emperor_reply_month = month + 2;
    if (warned_of_emperor_reply_month >= 12)
        warned_of_emperor_reply_month -= 12;
    warned_of_emperor_reply_month++;
    warned_of_emperor_reply_level = rating + 1;
    total_amount_of_bribes += imperial_gift_level;
    total_no_of_bribes++;
    av_imperial_gift_level = total_amount_of_bribes / total_no_of_bribes;
    if (final_bribe != 0) {
        if (rating <= -1) { final_bribe = 2; imperial_favour = 0; }
        else              { final_bribe = 0; }
    }
}
""" % second_test

exp.add("chain-ne", _body("imperial_gift_level != tribute"),
        note="second test != (skip-if-equal -> je?)")
exp.add("chain-gt", _body("imperial_gift_level > tribute"),
        note="natural > (gives jle, baseline of this family)")
