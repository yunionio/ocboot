#!/usr/bin/env bash

export PATH=$PATH:/opt/yunion/bin
export KUBECONFIG=/etc/kubernetes/admin.conf
export DB_HOST=
export DB_USER=
export DB_PSWD=
export DB_PORT=

if [[ "$DEBUG" == "true" ]]; then
    set -ex ;export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
fi

### helpers
lines_2_json(){
	local lines="$1"
	local len="${#keys[@]}"

    if [ -z "$lines" ]; then
        echo "[]"
        return
    fi

	echo '['
	echo "$lines "|tail -n +1 |while read line ; do
	values=($(echo "$line"))
	echo -n "{"
	firstline=
	for i in 0 $(seq $len); do
		k=${keys[$i]}
		v=${values[$i]}
		if [ -z "$k" ]; then
			continue
		fi
		if [[ -z "$firstline" ]]; then
			echo -n "\"$k\": \"$v\""
			firstline=full
		else
			echo ",\"$k\": \"$v\""
		fi
	done
	echo -n "}"
	done | sed -e 's#}{#},{#g'
	echo ']'
}

get_node_name(){
    hostname
}
get_node_ip(){
    ip route get 1  |head -1 |awk '{print $7}'
}

get_qemu_version(){
    rpm -qa | grep yunion-qemu |xargs | sed -e 's# #","#g'
}

get_last_5min_load(){
    uptime |awk '{print $(NF-1)}' | tr -d ','
}

get_ncpu(){
    lscpu | grep -i '^CPU.s.' |awk '{print $2}'
}

get_cpu_load_percentage(){
    local load=$(get_last_5min_load)
    local n=$(get_ncpu)
    python -c "print('%0.2f%%' % (${load} * 100.0 / $n))"
}

_helper_multiple_lines(){
     tr '\n' ',' |sed -e 's#,$##g' -e 's# *, *#","#g'
}

get_mem_usage(){
    free | grep Mem | awk '{printf "%.0f%%",$3/$2*100}'
}

_get_disk_usage(){
    df -hT | grep '^/'
}

disk_usage_json(){
    local keys=( Filesystem              Type      Size  Used Avail Use% "Mounted on" )
    lines_2_json "$(_get_disk_usage)"
}

get_disk_usage_above_70(){
    local keys=( Filesystem              Type      Size  Used Avail Use% "Mounted on" )
    lines_2_json "$(_get_disk_usage| awk '$(NF-1) >= 70')"
}
get_disk_usage_above_90(){
    local keys=( Filesystem              Type      Size  Used Avail Use% "Mounted on" )
    lines_2_json "$(_get_disk_usage| awk '$(NF-1) >= 90')"
}

diskUsageHelper(){
    df -hT | grep dev |grep '^/' | _helper_multiple_lines
}

is_disk_usage_ok(){
    local n=$(_get_disk_usage| awk '$(NF-1) >= 70' | wc -l)
    if [ "$n" -eq 0 ]; then
        echo "OK"
    else
        echo "ERROR"
    fi
}

is_disk_usage_critical(){
    local n=$(get_disk_usage_above_90 |wc -l)
    [[ $n -gt 0 ]]
}

disk_io(){
    local n
    n=$(iostat -x |grep -n Device |awk -F: '{print $1}')
    iostat -x |tail -n +$n |sed -e '/^$/d'
}

## DB stat
get_db_account(){
    local content="$(kubectl get onecloudcluster -n onecloud default -o yaml |grep -A 5 -w mysql)"
    export DB_HOST=$(echo "$content" |grep -w host: |awk '{print $(NF)}')
    export DB_USER=$(echo "$content" |grep -w username: |awk '{print $(NF)}')
    export DB_PSWD=$(echo "$content" |grep -w password: |awk '{print $(NF)}')
    export DB_PORT=$(echo "$content" |grep -w port: |awk '{print $(NF)}')
    export DB_PORT=${DB_PORT:-3306}
}

get_db_account

check_mysql_status(){
    mysqladmin -h $DB_HOST -u $DB_USER -p"$DB_PSWD" -P "$DB_PORT" status
}

check_mysql_status_json(){
    local line="$(check_mysql_status)"
    line="\"$(echo "$line"| perl -p -e 's#(: [\d.]+)\s*#\"$1,\"#g')"
    echo $line |sed -e 's#,"$##'
}

check_mysql_status_code(){
    if check_mysql_status >/dev/null ; then
        echo "OK"
    else
        echo "ERROR"
    fi
}

check_mysql_ha_status(){
    mysql -h $DB_HOST -u $DB_USER -p"$DB_PSWD" -P "$DB_PORT" -e "SHOW SLAVE STATUS\G;"
}

mysql_slave_status_code(){
    if check_mysql_ha_status >/dev/null ; then
        echo "OK"
    else
        echo "ERROR"
    fi
}

check_mysql_aborted_connection(){
    mysql -h $DB_HOST -u $DB_USER -p"$DB_PSWD" -P "$DB_PORT" -e "SHOW GLOBAL STATUS LIKE 'aborted_connects';" | grep Aborted_connects  |awk '{print $2}'
}

check_mysql_aborted_connection_code(){
    local code="$(check_mysql_aborted_connection)"
    if [[ "$code" -eq 0 ]] ; then
        echo "OK"
    else
        echo "ERROR"
    fi
}

check_mysql_aborted_connection_details(){
    mysql -h $DB_HOST -u $DB_USER -p"$DB_PSWD" -P "$DB_PORT" -e "SHOW GLOBAL STATUS LIKE 'aborted_connects';" |grep Aborted_connects |xargs
}

## k8s
get_nodes(){
    kubectl  get nodes -o wide
}

get_nodes_json(){
    local keys=(NAME STATUS ROLES AGE VERSION INTERNAL-IP EXTERNAL-IP   OS-IMAGE KERNEL-VERSION CONTAINER-RUNTIME)
    lines_2_json "$(get_nodes|tail -n +2)"

}

get_pods(){
    kubectl  get pods -o wide -A
}

get_pods_json(){
    local keys=(NAMESPACE NAME READY STATUS RESTARTS   AGE IP NODE NOMINATED_NODE   "READINESS GATES")
    lines_2_json "$(get_pods|tail -n +2)"
}

get_error_pods_json(){
    local keys=(NAMESPACE NAME READY STATUS RESTARTS   AGE IP NODE NOMINATED_NODE   "READINESS GATES")
    lines_2_json "$(get_pods|grep -vi running|tail -n +2)"
}

get_container_image_and_tag(){
    kubectl get pods -A -o go-template --template='{{range .items}}{{range .spec.containers}}{{printf "%s\n" .image}}{{printf "%s\n" .name}}{{end}}{{end}}'
}

is_pod_status_ok(){
    local running_pod_count
    local abnormal_pod_count
    local pods=$(get_pods)
    running_pod_count=$(echo "$pods" |grep -v ^NAMESPACE |grep -w Running |wc -l)
    abnormal_pod_count=$(echo "$pods" |grep -v ^NAMESPACE |grep -wv Running |wc -l)
    if [[ "$running_pod_count" -gt 0 ]] && [[ "$abnormal_pod_count" -eq 0 ]]; then
        echo OK
    else
        echo "ERROR"
    fi
}

check_cert(){
    kubeadm alpha certs check-expiration |sed -e 's#,##g' -e 's# *$##'
}

check_cert_json(){
    local keys=(CERTIFICATE EXPIRES "RESIDUAL TIME"   "EXTERNALLY MANAGED")
    local lines="$(kubeadm alpha certs check-expiration|grep -v CERTIFICATE)"
    lines_2_json "$(echo "$lines" |awk '{print $1, "" $2 "_" $3 "_" $4"_" $5"_" $6 "", $7, $8}' )" |tr '_' ' '
}

k8s_cert_status(){
    local days_left
    local years_left
    years_left=$(kubeadm alpha certs check-expiration |grep -v '^CERTIFICATE' |awk '{print $(NF-1)}' |sort -u |grep -P '\dy' |wc -l)
    if [[ "$years_left" -gt 0 ]]; then
        echo "OK"
        return
    fi

    days_left=$(kubeadm alpha certs check-expiration |grep -v '^CERTIFICATE' |awk '{print $(NF-1)}' |sort -u |grep -vP '\dy' |tr -d 'd' |sort -k1n |head -1)
    if [[ $days_left -gt 90 ]]; then
        echo "OK"
    else
        echo "ERROR"
    fi
}
cat << EOF
{
    "nodes": [
        {
            "nodeName": "$(get_node_name)"
            , "nodeIp": "$(get_node_ip)"
            , "qemuVersion": ["$(get_qemu_version)"]
            , "last5MinLoadPerCPU": "$(get_cpu_load_percentage)"
            , "memUsage": "$(get_mem_usage)"
            , "diskStatus": "$(is_disk_usage_ok)"
            , "diskUsageAbove70%": $(get_disk_usage_above_70)
            , "diskUsageAbove90%": $(get_disk_usage_above_90)
            , "diskUsagesDetails": $(disk_usage_json)
            , "mysqlStatus": "$(check_mysql_status_code)"
            , "mysqlStatusDetails": {$(check_mysql_status_json)}
            , "mysqlAbortedConnectionStatus": "$(check_mysql_aborted_connection_code)"
            , "mysqlAbortedConnectionDetails": "$(check_mysql_aborted_connection_details)"
            , "mysqlSlaveStatus": "$(mysql_slave_status_code)"
            , "mysqlSlaveDetails": "$(check_mysql_ha_status)"
            , "k8sNodes": $(get_nodes_json)
            , "k8sPods":  $(get_pods_json)
            , "k8sPodsStatus": "$(is_pod_status_ok)"
            , "k8sPodsErrorPods": $(get_error_pods_json)
            , "k8sCertStatus": "$(k8s_cert_status)"
            , "k8sCertDetails": $(check_cert_json)
        }
    ]
}
EOF
