#!/usr/bin/env bash
# What: use Bash for strict, predictable startup behavior; why: the power profile depends on Bash error and variable semantics.
set -euo pipefail
# What: reapply the validated CPU governor; why: inference latency should not depend on a stale post-boot governor state.
"${HOME}/set-governor.sh"
# What: apply the validated 39-watt and 90-Celsius firmware limits; why: sustained AMD inference must remain inside the qualified thermal envelope.
sudo -n /usr/local/bin/ryzenadj --stapm-limit=39000 --fast-limit=39000 --slow-limit=39000 --tctl-temp=90 >/dev/null
# What: record the AMD GPU sysfs directory; why: the next guarded write must target the qualified qualified GMKtek EVO-X2 device exactly.
gpu=/sys/bus/pci/devices/0000:64:00.0
# What: continue only when the qualified GPU exists; why: startup should not write to an absent or different device.
if [[ -d "$gpu" ]]; then
  # What: restore dynamic GPU clock scaling; why: automatic scaling cooperates with the thermal watchdog and avoids unsafe forced clocks.
  echo auto | sudo -n tee "$gpu/power_dpm_force_performance_level" >/dev/null
# What: close the GPU-presence guard; why: the conditional must bound only the device-specific write.
fi
# What: emit an auditable startup message; why: the journal should prove when the safety profile was applied.
printf '%s FreeToken inference power profile applied\n' "$(date '+%F %T')"
