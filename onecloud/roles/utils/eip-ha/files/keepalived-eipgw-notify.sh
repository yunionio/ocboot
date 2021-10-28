#!/usr/bin/env bash

prog="$0"
statefile=/var/run/yunion-sdnagent-eipgw.state
pidfile=/var/run/yunion-sdnagent-eipgw.pid


__errmsg() {
	logger -t "$prog" "$*"
}

_has_eipgw() {
	local comm
	comm="$(pgrep --list-name --pidfile "$pidfile" | cut -d' ' -f2)"
	[ -n "$comm" -a "$comm" = sdnagent ]
}

_start() {
	/opt/yunion/bin/sdnagent --config /etc/yunion/sdnagent.conf 2>&1 | logger -t sdnagent-eipgw &
	__errmsg "sdnagent eipgw process group id $$"
}

_stop() {
	pkill --pidfile "$pidfile"
	ovs-vsctl --if-exists del-br breip
	ovs-vsctl list-ports brvpc \
		| grep '^ev-' \
		| while read port; do \
			ovs-vsctl --if-exists del-port brvpc "$port"; \
		done
}

notify() {
	local state="$1"; shift

	__errmsg "notify: got state $state"

	set -x
	echo "$state" >"$statefile"
	case "$state" in
		MASTER)
			_start
			;;
		*)
			_stop
			;;
	esac
}

monitor() {
	local state
	if [ -s "$statefile" ]; then
		state="$(<"$statefile")"
		__errmsg "monitor: hey state $state"
		case "$state" in
			MASTER)
				if ! _has_eipgw; then
					_start
				fi
				;;
			*)
				if _has_eipgw; then
					_stop
				fi
				;;
		esac
	fi
	return 0
}

"$@"
