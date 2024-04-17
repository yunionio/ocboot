#!/usr/bin/env bash

delete_crash(){
    local not_running
    not_running=( $(kubectl get pods -n onecloud --no-headers |grep CrashLoopBackOff |awk '{print $1}') )
    if [[ "$not_running" -gt 0 ]]; then
        kubectl -n onecloud delete pods "${not_running[@]}"
    fi
}

wait_for_running() {
    local running=
    local idx=0
    while [[ "$idx" -lt 10 ]]; do
        idx=$((idx + 1))
        delete_crash
        sleep 30
        running="$(kubectl get pods -A --no-headers | grep -cviP 'Running|telegraf|meter|etcd|extdb|-host-|autoupdate|webconsole|cloudmon|scheduledtask')"
        if [[ "$running" -eq 0 ]]; then
            exit 0
        else
            echo "waiting for $running pods "
        fi
    done
}

export -f wait_for_running
timeout 1200 bash -c "wait_for_running"

rm -f /tmp/wait-for-pods-running.sh

