"""Regression tests for the build-dir concurrency lock.

The persistent ``.c2-cache/build/`` is shared by every cache-mode
``c2 decomp-verify``.  Concurrent verifies once raced their
``wasm``/``wlink`` writes and corrupted shared object files (oversized
objs, ``invalid record type 0x0000``, duplicate symbols), which then
wedged the linker / dosemu.  ``_build_dir_lock`` serialises cache-mode
builds.  These tests pin its three guarantees:

  * mutual exclusion + blocking wait (a second acquirer waits),
  * the holder's PID is recorded in the lock file for diagnostics,
  * self-healing — the kernel releases the ``flock`` when the holder
    dies (even on SIGKILL), so a crash never leaves the lock stuck.
"""

import multiprocessing as mp
import os
import time
from pathlib import Path

from c2.commands.decomp_verify import _build_dir_lock


def _hold(lock_path: str, hold_s: float, ready, ev_block=None):
    with _build_dir_lock(Path(lock_path)):
        ready.set()
        time.sleep(hold_s)


def _hold_forever(lock_path: str, ready):
    with _build_dir_lock(Path(lock_path)):
        ready.set()
        time.sleep(60)


def test_records_pid_and_serialises(tmp_path):
    lock = tmp_path / "build.lock"
    ready = mp.Event()
    holder = mp.Process(target=_hold, args=(str(lock), 1.0, ready))
    holder.start()
    try:
        assert ready.wait(5), "holder never acquired the lock"

        # PID of the holder is written to the lock file for visibility.
        first_line = lock.read_text().splitlines()[0]
        assert first_line == str(holder.pid)

        # A second acquirer must block until the holder releases.
        t0 = time.time()
        with _build_dir_lock(lock):
            waited = time.time() - t0
            assert waited >= 0.5, f"did not wait for holder (waited {waited:.2f}s)"
            # Our identity replaces the holder's while we own it.
            assert lock.read_text().splitlines()[0] == str(os.getpid())
    finally:
        holder.join(10)

    # Lock file is cleared once released.
    assert lock.read_text() == ""


def test_self_heals_on_holder_kill(tmp_path):
    lock = tmp_path / "build.lock"
    ready = mp.Event()
    holder = mp.Process(target=_hold_forever, args=(str(lock), ready))
    holder.start()
    try:
        assert ready.wait(5), "holder never acquired the lock"
        # Simulate a crash: SIGKILL leaves no chance to run cleanup, but
        # the kernel drops the flock when the process dies.
        os.kill(holder.pid, 9)
        holder.join(10)

        t0 = time.time()
        with _build_dir_lock(lock):
            # Should be essentially instant — no stale-lock wait.
            assert time.time() - t0 < 2.0
    finally:
        if holder.is_alive():
            holder.kill()
            holder.join(10)
