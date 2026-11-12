# Lab 10 — Evo-Cortex Kleene Telemetry Experiment

> ⚡ **BLUF**: Validates the Kleene 3-valued telemetry probe (`sense` subcommand) on Arena Linux 6.1.158+
> with masked cgroup — confirming `cgroup_cpu_quota` and `cgroup_memory` are honestly reported as `null`
> with no invented 2048 MB fallback, and PSI pressure is readable-or-null.

+-----------------------------------------------------------------------------+
| KLEENE TELEMETRY PROBE FLOW                                                 |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [evo_cortex sense]  -->  [resource.getrusage(2) RSS, faults, ctxt sw]      |
|                                |                                            |
|                                v                                            |
|                       [/proc/self/status VmRSS/VmPeak/VmSwap]               |
|                                |                                            |
|                                v                                            |
|                 [/sys/fs/cgroup cpu.max + memory.max]  <-- NULL if masked   |
|                                |                                            |
|                                v                                            |
|                 [/proc/pressure/{cpu,memory,io}]  <-- NULL if unreadable    |
|                                                                             |
+-----------------------------------------------------------------------------+

## Measured Output (Arena Linux 6.1.158+, 2 vCPU, Python 3.11.2)

```text
cgroup_cpu_quota:      UNAVAILABLE_NULL   (honestly null — no invented fallback)
cgroup_memory:         UNAVAILABLE_NULL   (honestly null — no invented 2048 MB)
linux_psi cpu/mem/io:  null               (unreadable in sandbox — honestly null)
cpu_affinity_count:    2
preemption_thrash_ratio: 0.0              (no preemption thrash at baseline)
VmRSS_bytes:           ~20 MB baseline
major_faults_disk:     0                  (no swap pressure)
```

**Receipt**: `RCPT-B6090E0D5FFB` (exit 0, 75ms)

## Math: Kleene 3-Valued Logic

| State | Meaning | Action |
|-------|---------|--------|
| KNOWN | Value read from kernel syscall | Use directly |
| NULL  | cgroup/PSI masked/unreadable | Switch to Closed-Loop Derivative Control ($\dot{\text{RSS}}$, $\Delta majflt$) |
| BOUNDED | Interval estimate known | Use conservative bound |

**Control Barrier Guard**: When memory state is NULL → cap `W* = min(C_affinity, 2)`, `batch = 15`.
