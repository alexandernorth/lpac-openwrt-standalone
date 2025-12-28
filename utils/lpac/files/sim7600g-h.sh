#!/bin/sh
set -eu

DEV="${DEV:-/dev/ttyUSB2}"
#BAUD="${BAUD:-115200}"
DIR="/usr/lib/lpac/at-scripts" #"$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

usage() {
  echo "Usage:"
  echo "  $0 usb-mode rndis"
  echo "  $0 usb-mode qmi"
  echo "  $0 status network"
  exit 2
}

[ $# -eq 2 ] || usage

group="$1"
action="$2"

case "$group:$action" in
  usb-mode:rndis) script="$DIR/usb-mode-rndis.miniscr" ;;
  usb-mode:qmi)   script="$DIR/usb-mode-qmi.miniscr" ;;
  status:network) script="$DIR/status-network.miniscr" ;;
  *) usage ;;
esac

log="/tmp/at-${group}-${action}.log"
rm -f "$log"

minicom -o -D "$DEV" -S "$script" -C "$log" </dev/null >/dev/null 2>&1 || {
  echo "Failed (see $log)"
  exit 1
}

echo "OK (see $log)"
