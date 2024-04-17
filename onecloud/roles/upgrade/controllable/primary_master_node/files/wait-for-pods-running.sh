#!/usr/bin/env bash

clean_pod_configmap() {
    local item=$1
    local pods=()
    pods+=($(kubectl get pods -A | grep -vi 'running' | grep -P "default-$item" | awk '{print $2}'))
    if [[ "${#pods[@]}" -gt 0 ]]; then
        kubectl delete configmap -n onecloud default-$item &>/dev/null || :
        kubectl -n onecloud delete pods --grace-period=0 --force "${pods[@]}" &>/dev/null || :
    fi
}

wait_for_running() {
    local running=
    local idx=0
    while [[ "$idx" -lt 120 ]]; do
        idx=$((idx + 1))
        sleep 15
        running="$(kubectl get pods -A --no-headers | grep -cviP 'Running|telegraf|meter|etcd|extdb|-host-|autoupdate|webconsole|cloudmon|scheduledtask')"
        if [[ "$running" -eq 0 ]]; then
            exit 0
        else
            echo "waiting for $running pods "
        fi
    done
    exit 1
}

export -f wait_for_running

clean_pod_configmap autoupdate
clean_pod_configmap webconsole

timeout 1800 bash -c "wait_for_running"
rm -f /tmp/wait-for-pods-running.sh

