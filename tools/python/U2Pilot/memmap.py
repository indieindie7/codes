r"""Address-space use of a running 32-bit game (Unreal2.exe by default), sampled from outside.

    py memmap.py [exe-name] [--every SECONDS] [--for SECONDS]

Prints, per sample: the highest used address, the address space in use (committed + reserved), the free
total and the largest free block. A 32-bit process without the Large Address Aware flag has 2 GB of user
space; with it, 4 GB on 64-bit Windows. "largest free" is what a big allocation (a texture, a vertex
buffer) can still get, which runs out before the total does.
"""
import ctypes
import ctypes.wintypes as W
import subprocess
import sys
import time


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p), ("AllocationProtect", W.DWORD),
                ("PartitionId", W.WORD), ("RegionSize", ctypes.c_size_t), ("State", W.DWORD), ("Protect", W.DWORD),
                ("Type", W.DWORD)]


MEM_FREE, MEM_COMMIT, MEM_RESERVE = 0x10000, 0x1000, 0x2000
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = W.HANDLE
k32.VirtualQueryEx.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t


def pid_of(name):
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + name, "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[0].lower() == name.lower():
            return int(parts[1])
    return None


def sample(h):
    m = MBI()
    addr, top, used, free, largest = 0, 0, 0, 0, 0
    while addr < 0x100000000:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(m), ctypes.sizeof(m)):
            break
        size = m.RegionSize
        if m.State == MEM_FREE:
            free += size
            largest = max(largest, size)
        else:
            used += size
            top = max(top, addr + size)
        addr += size
    return top, used, free, largest


def main():
    a = sys.argv[1:]
    name = next((x for x in a if not x.startswith("--") and not x.replace(".", "").isdigit()), "Unreal2.exe")
    every = float(a[a.index("--every") + 1]) if "--every" in a else 10
    total = float(a[a.index("--for") + 1]) if "--for" in a else 0
    t0 = time.time()
    h = None
    while True:
        pid = pid_of(name)
        if pid and h is None:
            h = k32.OpenProcess(0x0400 | 0x0010, False, pid)
        if h:
            top, used, free, largest = sample(h)
            mb = 1 << 20
            print("%6.0f s  top %5d MB  in use %5d MB  free %5d MB  largest free %5d MB" % (time.time() - t0, top // mb, used // mb, free // mb, largest // mb), flush=True)
        if total and time.time() - t0 > total:
            break
        if not pid and h is not None:
            break
        time.sleep(every)


if __name__ == "__main__":
    main()
