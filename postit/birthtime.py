"""When a file was created — which `os.stat` can't say on Linux.

Deliberately Qt-free, like `note.py`. Append opens the most recently *created*
note, not the most recently modified one, so it needs each file's birth time.
Python exposes that as `st_birthtime_ns` only on macOS, the BSDs and Windows;
on Linux the kernel reports it solely through `statx(2)`, which the standard
library doesn't wrap, so it is called here through ctypes.

`st_ctime` is no substitute: on Linux it is the time the inode last *changed*,
which a plain edit updates. And there is deliberately no fallback to the
modification time when the birth time is unknown — opening the wrong note would
be worse than saying the question can't be answered.
"""

from __future__ import annotations

import ctypes
import errno
import functools
import os
import struct
from collections.abc import Callable

# From <linux/stat.h> and <fcntl.h>. `struct statx` is a fixed 256 bytes, and
# `stx_btime` — an `__s64` of seconds then a `__u32` of nanoseconds — sits at
# byte 80, after the mask, sizes, ids and `stx_atime`. That layout is kernel ABI
# and never moves; new fields only ever take up the spare space at the end.
_AT_FDCWD = -100
_STATX_BTIME = 0x800
_STATX_SIZE = 256
_STATX_MASK = struct.Struct("=I")
_STATX_BTIME_FIELD = struct.Struct("=qI")
_STATX_BTIME_OFFSET = 80


class BirthTimeUnavailable(OSError):
    """This system or filesystem doesn't record when the file was created."""


@functools.cache
def _statx() -> Callable[..., int] | None:
    """glibc's `statx()` wrapper (2.28 and later), or None if libc has none."""
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        function = libc.statx
    except (OSError, AttributeError):
        return None
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_void_p,
    ]
    function.restype = ctypes.c_int
    return function


def _unavailable(path: str) -> BirthTimeUnavailable:
    return BirthTimeUnavailable(
        f"This system does not record when files were created, so the most "
        f"recent note can't be found.\n\n{path}"
    )


def birth_time_ns(path: str) -> int:
    """When `path` was created, in nanoseconds since the epoch.

    Symlinks are followed, as `os.stat` does. Raises BirthTimeUnavailable when
    the platform or filesystem keeps no birth time, or OSError if `path` can't
    be examined at all.
    """
    birth = getattr(os.stat(path), "st_birthtime_ns", None)
    if birth is not None:
        return birth

    statx = _statx()
    if statx is None:
        raise _unavailable(path)
    buffer = ctypes.create_string_buffer(_STATX_SIZE)
    if statx(_AT_FDCWD, os.fsencode(path), 0, _STATX_BTIME, buffer) != 0:
        code = ctypes.get_errno()
        if code == errno.ENOSYS:  # a kernel older than 4.11
            raise _unavailable(path)
        raise OSError(code, os.strerror(code), path)
    # The kernel clears STATX_BTIME in the returned mask when the filesystem
    # has no birth time to give (some network and older filesystems), leaving
    # the field zeroed rather than failing the call.
    (mask,) = _STATX_MASK.unpack_from(buffer, 0)
    if not mask & _STATX_BTIME:
        raise _unavailable(path)
    seconds, nanoseconds = _STATX_BTIME_FIELD.unpack_from(buffer, _STATX_BTIME_OFFSET)
    return seconds * 1_000_000_000 + nanoseconds
