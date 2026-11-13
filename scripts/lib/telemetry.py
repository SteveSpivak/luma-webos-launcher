"""
scripts/lib/telemetry.py — Honest kernel syscall + procfs telemetry (zero fabrication).

Reads only verifiable, unprivileged kernel signals. Unknown cgroup values stay null.
Works on Linux 6.1+ containers and macOS Darwin.
"""
from __future__ import annotations

import datetime
import os
import platform
import resource
from pathlib import Path

PAGE_SIZE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def _read_first(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def probe_cpu_telemetry() -> dict:
    """Real CPU affinity + cgroup quota (Linux) / Mach P/E cores (macOS)."""
    result: dict = {
        "logical_cpus": os.cpu_count(),
        "affinity_count": None,
        "cgroup": {"source": None, "raw": None, "cores": None},
    }

    if hasattr(os, "sched_getaffinity"):
        try:
            result["affinity_count"] = len(os.sched_getaffinity(0))
        except OSError:
            pass

    # Linux cgroup v2 unified hierarchy probe (all known controller locations)
    cgroup_paths = [
        Path("/sys/fs/cgroup/cpu.max"),
        Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"),
    ]
    for p in cgroup_paths:
        raw = _read_first(p)
        if raw is None:
            continue
        result["cgroup"]["source"] = str(p)
        result["cgroup"]["raw"] = raw
        try:
            if p.name == "cpu.max":
                quota, period = raw.split()[:2]
                if quota != "max":
                    result["cgroup"]["cores"] = round(int(quota) / int(period), 3)
            elif p.name == "cpu.cfs_quota_us":
                quota = int(raw)
                period_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
                period = int(period_path.read_text().strip())
                if quota > 0 and period > 0:
                    result["cgroup"]["cores"] = round(quota / period, 3)
        except (ValueError, ZeroDivisionError, OSError):
            pass
        break  # first readable cgroup source wins

    # macOS Mach P/E core telemetry
    if platform.system() == "Darwin":
        try:
            import subprocess
            result["mach_p_cores"] = int(
                subprocess.check_output(["sysctl", "-n", "hw.perflevel0.physicalcpu"],
                                        stderr=subprocess.DEVNULL, text=True).strip()
            )
            result["mach_e_cores"] = int(
                subprocess.check_output(["sysctl", "-n", "hw.perflevel1.physicalcpu"],
                                        stderr=subprocess.DEVNULL, text=True).strip()
            )
        except (OSError, ValueError, subprocess.CalledProcessError):
            pass

    return result


def probe_memory_telemetry() -> dict:
    """Real RSS/current/limit from procfs + cgroup memory controller."""
    result: dict = {
        "rss_current_bytes": None,
        "rss_peak_bytes": None,
        "cgroup": {"source": None, "limit_bytes": None, "current_bytes": None},
    }

    # /proc/self/status always readable by own process on Linux
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip()
            if key in ("VmRSS", "VmPeak", "VmSwap", "Threads"):
                multiplier = 1024  # /proc status values are in kB
                result[f"{key.lower()}_bytes"] = int(val.strip().split()[0]) * multiplier
    except OSError:
        pass

    # getrusage ru_maxrss (KB on Linux, Bytes on macOS)
    ru_self = resource.getrusage(resource.RUSAGE_SELF)
    ru_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    scale = 1024 if platform.system() == "Linux" else 1
    result["rusage_self_maxrss_bytes"] = int(ru_self.ru_maxrss * scale)
    result["rusage_children_maxrss_bytes"] = int(ru_child.ru_maxrss * scale)

    # cgroup memory controller (all known locations)
    mem_paths = [
        Path("/sys/fs/cgroup/memory.max"),
        Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
    ]
    cur_paths = [
        Path("/sys/fs/cgroup/memory.current"),
        Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"),
    ]
    for max_p, cur_p in zip(mem_paths, cur_paths):
        raw_max = _read_first(max_p)
        raw_cur = _read_first(cur_p)
        if raw_max is None or raw_cur is None:
            continue
        result["cgroup"]["source"] = str(max_p)
        result["cgroup"]["current_bytes"] = int(raw_cur)
        if raw_max != "max":
            result["cgroup"]["limit_bytes"] = int(raw_max)
        break

    return result


def probe_pressure_telemetry() -> dict:
    """Linux Pressure Stall Information (PSI) — global stall accounting."""
    psi = {}
    for res in ("cpu", "memory", "io"):
        try:
            line = Path(f"/proc/pressure/{res}").read_text().strip().splitlines()[0]
            psi[res] = line
        except OSError:
            psi[res] = None
    return psi


def probe_rusage() -> dict:
    """getrusage(2) process-level syscall telemetry."""
    ru_self = resource.getrusage(resource.RUSAGE_SELF)
    ru_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "user_cpu_sec": round(ru_self.ru_utime + ru_child.ru_utime, 6),
        "sys_cpu_sec": round(ru_self.ru_stime + ru_child.ru_stime, 6),
        "maxrss_bytes": int(ru_self.ru_maxrss * (1024 if platform.system() == "Linux" else 1)),
        "minor_page_faults": ru_self.ru_minflt + ru_child.ru_minflt,
        "major_page_faults": ru_self.ru_majflt + ru_child.ru_majflt,
        "voluntary_ctx_switches": ru_self.ru_nvcsw + ru_child.ru_nvcsw,
        "involuntary_ctx_switches": ru_self.ru_nivcsw + ru_child.ru_nivcsw,
        "block_input_ops": ru_self.ru_inblock + ru_child.ru_inblock,
        "block_output_ops": ru_self.ru_oublock + ru_child.ru_oublock,
    }


def sample_all() -> dict:
    """Full honest telemetry snapshot. Unknowns remain null."""
    return {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu": probe_cpu_telemetry(),
        "memory": probe_memory_telemetry(),
        "pressure": probe_pressure_telemetry(),
        "rusage": probe_rusage(),
    }
