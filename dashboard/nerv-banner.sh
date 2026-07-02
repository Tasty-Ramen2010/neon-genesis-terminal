#!/usr/bin/env bash
# NERV / MAGI boot banner - prints on new interactive shells.
# Disable for a session:  export NERV_BANNER=0
[ "${NERV_BANNER:-1}" = "0" ] && return 0 2>/dev/null

A='\033[38;5;208m'; G='\033[38;5;40m'; C='\033[38;5;51m'; M='\033[38;5;201m'
Y='\033[38;5;226m'; R='\033[38;5;196m'; BL='\033[38;5;39m'; D='\033[38;5;240m'
B='\033[1m'; X='\033[0m'
FIG=$(command -v figlet)

# NERV in figlet slant, each line a different phosphor hue
if [ -n "$FIG" ]; then
  cols=(51 39 208 201 196)
  i=0
  printf '\n'
  "$FIG" -f slant "NERV" 2>/dev/null | while IFS= read -r line; do
    printf "  \033[1;38;5;%sm%s${X}\n" "${cols[$((i % 5))]}" "$line"
    i=$((i+1))
  done
else
  printf "\n  ${C}${B}N E R V${X}\n"
fi

printf "  ${D}MAGI SYSTEM . marduk institute${X}\n\n"
printf "  ${D}┌─${X} ${A}${B}MAGI${X} ${D}──────────────────────────────────────────────┐${X}\n"
printf "  ${D}│${X}  ${C}o MELCHIOR-1${X}   ${Y}o BALTHASAR-2${X}   ${M}o CASPER-3${X}   ${D}supervisor${X} ${G}${B}OK${X} ${D}│${X}\n"
printf "  ${D}│${X}  ${A}OPERATOR${X} ${D}.${X} ${G}%s@%s${X}\n" "$(whoami)" "$(hostname -s)"
printf "  ${D}│${X}  ${A}MISSION TIME${X} ${D}.${X} ${C}%s${X}\n" "$(date '+%Y-%m-%d %H:%M:%SZ')"
printf "  ${D}│${X}  ${A}A.T. FIELD${X} ${D}.${X} ${G}${B}NOMINAL${X}   ${D}sync${X} ${G}${B}100%%${X}\n"
printf "  ${D}└────────────────────────────────────────────────────────┘${X}\n\n"
