"""gcm: switch vs if-else"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="getcitymood3",
    ps_function="get_city_mood",
    extra_defs="""
int bad_mood, emergency_mood, last_city_mood, rand128, threat_mood, tune_branch, tune_mood;
""",
    prelude="""
extern int bad_mood, emergency_mood, last_city_mood, rand128, threat_mood, tune_branch, tune_mood;
""",
)

exp.add('baseline', """
void get_city_mood(void)
{
    int old_mood;
    int r;

    old_mood = tune_mood;
    if (old_mood == 10) {
        tune_mood = 0;
        tune_branch = 0x28;
    } else if (old_mood == 11) {
        tune_mood = 0;
        tune_branch = 0x29;
    } else if (old_mood == 12) {
        tune_mood = 0;
        tune_branch = 0x2a;
    } else if (old_mood == 13) {
        tune_mood = 1;
        tune_branch = 0x2d;
        bad_mood = 0xc8;
    } else if (old_mood == 14) {
        tune_mood = 1;
        tune_branch = 0x2b;
        bad_mood = 0xc8;
    } else if (old_mood == 15) {
        tune_mood = 1;
        tune_branch = 0x2c;
        bad_mood = 0xc8;
    } else if (old_mood == 16) {
        tune_mood = 1;
        tune_branch = 0x2e;
        bad_mood = 0xc8;
    } else if (old_mood == 17) {
        tune_mood = 2;
        tune_branch = 0x2f;
        threat_mood = 0xc8;
    } else if (old_mood == 18) {
        tune_mood = 2;
        tune_branch = 0x30;
        threat_mood = 0xc8;
    } else if (old_mood == 19) {
        tune_mood = 2;
        tune_branch = 0x31;
        threat_mood = 0xc8;
    } else if (old_mood == 20) {
        tune_mood = 3;
        tune_branch = 0x32;
        emergency_mood = 0xc8;
    } else if (old_mood == 21) {
        tune_mood = 3;
        tune_branch = 0x33;
        emergency_mood = 0xc8;
    } else if (old_mood == 22) {
        tune_mood = 3;
        tune_branch = 0x34;
        emergency_mood = 0xc8;
    } else if (old_mood == 23) {
        tune_mood = 3;
        tune_branch = 0x35;
        emergency_mood = 0xc8;
    } else {
        r = rand128 & 7;
        if (old_mood == 0) {
            tune_branch = r;
            if (tune_branch > 6) tune_branch = 6;
        } else if (old_mood == 1) {
            r += 0xa;
            tune_branch = r;
            if (tune_branch > 0x10) tune_branch = 0x10;
        } else if (old_mood == 2) {
            r += 0x14;
            tune_branch = r;
            if (tune_branch > 0x1a) tune_branch = 0x1a;
        } else if (old_mood == 3) {
            r += 0x1e;
            tune_branch = r;
            if (tune_branch > 0x24) tune_branch = 0x24;
        } else {
            tune_mood = 0;
            tune_branch = 0;
        }
    }
    if (bad_mood != 0)       tune_mood = 1;
    if (threat_mood != 0)    tune_mood = 2;
    if (emergency_mood != 0) tune_mood = 3;

    if (bad_mood == 0 && threat_mood == 0 && emergency_mood == 0) {
        if (last_city_mood == 3)      tune_mood = 2;
        else if (last_city_mood == 2) tune_mood = 1;
        else                          tune_mood = bad_mood;
    }
    last_city_mood = tune_mood;
}
""", note='if-else chain')

exp.add('switch', """
void get_city_mood(void)
{
    int old_mood;
    int r;

    old_mood = tune_mood;
    switch (old_mood) {
    case 10: tune_mood = 0; tune_branch = 0x28; break;
    case 11: tune_mood = 0; tune_branch = 0x29; break;
    case 12: tune_mood = 0; tune_branch = 0x2a; break;
    case 13: tune_mood = 1; tune_branch = 0x2d; bad_mood = 0xc8; break;
    case 14: tune_mood = 1; tune_branch = 0x2b; bad_mood = 0xc8; break;
    case 15: tune_mood = 1; tune_branch = 0x2c; bad_mood = 0xc8; break;
    case 16: tune_mood = 1; tune_branch = 0x2e; bad_mood = 0xc8; break;
    case 17: tune_mood = 2; tune_branch = 0x2f; threat_mood = 0xc8; break;
    case 18: tune_mood = 2; tune_branch = 0x30; threat_mood = 0xc8; break;
    case 19: tune_mood = 2; tune_branch = 0x31; threat_mood = 0xc8; break;
    case 20: tune_mood = 3; tune_branch = 0x32; emergency_mood = 0xc8; break;
    case 21: tune_mood = 3; tune_branch = 0x33; emergency_mood = 0xc8; break;
    case 22: tune_mood = 3; tune_branch = 0x34; emergency_mood = 0xc8; break;
    case 23: tune_mood = 3; tune_branch = 0x35; emergency_mood = 0xc8; break;
    default:
        r = rand128 & 7;
        if (old_mood == 0) { tune_branch = r; if (tune_branch > 6) tune_branch = 6; }
        else if (old_mood == 1) { r += 0xa; tune_branch = r; if (tune_branch > 0x10) tune_branch = 0x10; }
        else if (old_mood == 2) { r += 0x14; tune_branch = r; if (tune_branch > 0x1a) tune_branch = 0x1a; }
        else if (old_mood == 3) { r += 0x1e; tune_branch = r; if (tune_branch > 0x24) tune_branch = 0x24; }
        else { tune_mood = 0; tune_branch = 0; }
        break;
    }
    if (bad_mood != 0)       tune_mood = 1;
    if (threat_mood != 0)    tune_mood = 2;
    if (emergency_mood != 0) tune_mood = 3;

    if (bad_mood == 0 && threat_mood == 0 && emergency_mood == 0) {
        if (last_city_mood == 3)      tune_mood = 2;
        else if (last_city_mood == 2) tune_mood = 1;
        else                          tune_mood = bad_mood;
    }
    last_city_mood = tune_mood;
}
""", note='switch statement')
