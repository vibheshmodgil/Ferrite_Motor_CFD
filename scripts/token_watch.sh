#!/bin/sh
# Lists agent transcript sizes. ~11 bytes/token (calibrated: 3.6 MB = 328K reported)
# Prints FLAG at >=3.3 MB (~300K): that agent should
# write a handoff and be replaced.
# ponytail: size proxy only, no live token API available to scripts.
D="$LOCALAPPDATA/Temp/claude/C--Users-vibhe-Downloads-OUTPUT-CFD"
find "$D" -path '*tasks/a*.output' -mmin -120 -printf '%s %f\n' 2>/dev/null |
  awk '{t=$1/11000; printf "%-28s ~%4dK tok %s\n", $2, t, (t>=300?"FLAG: handoff+replace":"")}'
