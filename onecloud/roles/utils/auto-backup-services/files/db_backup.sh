#!/usr/bin/env bash

set -e
set -o pipefail

if [ "$DEBUG" == "true" ]; then
    set -ex
    export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
fi

export PATH=$PATH:/opt/yunion/bin
export KUBECONFIG=/etc/kubernetes/admin.conf
export BKUP_DATE=$(date +"%Y%m%d-%H%M%S")
export BKUP_PATH=${BKUP_PATH:-/opt/yunion/backup}/$BKUP_DATE
export DB_HOST=
export DB_USER=
export DB_PSWD=
export DB_PORT=
export MYSQL_BACKUP_ARGS='--add-drop-database --add-drop-table --add-locks --single-transaction --quick'
export MAX_BKUP=${MAX_BKUP:-10}
export LIGHT_BKUP=${LIGHT_BKUP:-true}
export VERBOSE=${VERBOSE:-false}
export PV_ARGS='pv --wait --timer --rate --eta --size '
export MAX_DISK_PERCENTAGE=${MAX_DISK_PERCENTAGE:-75}

dbs=()

__info() {
    line="$*"
    local regex="mysqldump|mysql|hostname|Light|DBs|Size:.*B\b|Backup result|Backup Disk"
    echo "[$(date +"%F %T")] $line" | grep --no-messages --color=auto --ignore-case --perl-regexp "$regex" ||
        echo "[$(date +"%F %T")] $line"
}

convert_seconds() {
    local seconds="$1"
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))
    local seconds=$((seconds % 60))

    if [ "$hours" -gt 0 ]; then
        echo "$hours hours, $minutes minutes, $seconds seconds"
    elif [ "$minutes" -gt 0 ]; then
        echo "$minutes minutes, $seconds seconds"
    else
        echo "$seconds seconds"
    fi
}

title() {
    local termwidth="$(tput cols)"
    termwidth=$((termwidth / 2))
    local padding="$(printf '%0.1s' ={1..500})"

    printf '\n%*.*s %s %*.*s\n' 0 "$(((termwidth - 2 - ${#1}) / 2))" "$padding" "$1" 0 "$(((termwidth - 1 - ${#1}) / 2))" "$padding"
}

check_bin_exist() {
    for bin in "$@"; do
        __info $($bin --version)
    done
}

check_backup_disk() {
    local disk
    if [ ! -d "$BKUP_PATH" ]; then
        mkdir -p "$BKUP_PATH"
    fi

    disk=$(df --output=source "$BKUP_PATH" | grep -v '^Filesystem' | head -1)
    if [ -z "$disk" ]; then
        "get disk error!"
        exit 1
    fi

    disk_usage=$(df -h --output=pcent --exclude-type=tmpfs,devtmpfs "$disk" | grep -v 'Use%' | head -1 | tr -d % | xargs)
    if [ "$disk_usage" -gt $MAX_DISK_PERCENTAGE ]; then
        __info "$BKUP_PATH is on disk $disk, usage:$disk_usage%, too high to continue backup."
        __info "Allowed maximum disk usage: $MAX_DISK_PERCENTAGE."
        exit 1
    fi
    __info "Backup Disk: $disk; Used: $disk_usage%"
}

init_db() {
    local
    title "Init"
    check_backup_disk
    local content="$(kubectl get onecloudcluster -n onecloud default -o yaml | grep -A 5 -w mysql)"
    export DB_HOST=$(echo "$content" | grep -w host: | awk '{print $(NF)}')
    export DB_USER=$(echo "$content" | grep -w username: | awk '{print $(NF)}')
    export DB_PSWD=$(echo "$content" | grep -w password: | awk '{print $(NF)}')
    export DB_PORT=$(echo "$content" | grep -w port: | awk '{print $(NF)}')
    export DB_PORT=${DB_PORT:-3306}
    local size
    if ! check_bin_exist mysql mysqldump; then
        __info "mysql or mysqldump is missing!"
        exit 1
    fi

    if [ -n "$DB_HOST" ] && [ -n "$DB_USER" ] && [ -n "$DB_PSWD" ]; then
        dbs=($(get_dbs))
        size=$(get_all_db_size_bytes)
        size=$(numfmt --to=iec --suffix=B "$size")
    else
        __info "init db error"
        exit 1
    fi

    local flag=Full
    if [[ "$LIGHT_BKUP" == "true" ]]; then
        flag=Light
    fi

    __info "Hostname: $(hostname), IP: $(ip route get 1 | head -1 | awk '{print $7}')"
    __info "performing $flag backup."
    __info "DBs to backup: [${dbs[*]}]"
    __info "Size: $size before compress."
}

query() {
    mysql --skip-column-names -h "$DB_HOST" -u "$DB_USER" -p"$DB_PSWD" -P "$DB_PORT" "$@"
}

get_dbs() {
    local filter
    if [ "$LIGHT_BKUP" == true ]; then
        filter='s#^\(Database\|mysql\|performance_schema\|test\|information_schema\|yunionlogger\|yunionmeter\)$##g'
    else
        filter='s#^\(Database\|mysql\|performance_schema\|test\|information_schema\)$##g'
    fi
    query -e 'show databases;' | sed -e "$filter" | sort
}

# --ignore-table=DB.table
get_ignore_tables_for_db() {
    local db="$1"
    local sql
    local tables=()
    if [ -z "$db" ]; then
        return
    fi
    sql="show tables from \`$db\` where \`Tables_in_$db\` like 'opslog%' or \`Tables_in_$db\` like 'task%';"
    tables=($(query -e "$sql"))
    for table in "${tables[@]}"; do
        echo "--ignore-table=$db.$table"
    done
}

get_all_ignored_tables() {
    local tables=()
    for db in "${dbs[@]}"; do
        tables+=($(get_ignore_tables_for_db $db))
    done
    echo "${tables[@]}"
}

backup_db() {
    local timestamp=$BKUP_DATE
    local args=()
    local output="$BKUP_PATH/onecloud.sql.$timestamp.gz"
    local startTime
    local endTime
    startTime=$(date +"%s")
    title "Backup Database"
    args=(${MYSQL_BACKUP_ARGS[@]} -h $DB_HOST -u $DB_USER -p"$DB_PSWD" -P "$DB_PORT")
    args+=(--databases ${dbs[@]})
    if [ "$LIGHT_BKUP" == true ]; then
        args+=($(get_all_ignored_tables))
    fi

    if [ -x /usr/bin/pv ]; then
        mysqldump "${args[@]}" | ${PV_ARGS[@]} $(get_all_db_size_bytes) | gzip -c >"$output"
    else
        mysqldump "${args[@]}" | gzip -c >"$output"
    fi
    endTime=$(date +"%s")
    __info "It takes $(convert_seconds $((endTime - startTime)))."
}

get_db_size_bytes() {
    local db="$1"
    local sql
    if [ -z "$db" ]; then
        return
    fi
    sql='SELECT
        sum(ROUND((DATA_LENGTH + INDEX_LENGTH )*0.85) )
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = "'$db'" '
    if [[ "$LIGHT_BKUP" == "true" ]]; then
        sql="$sql"'AND table_name not like "opslog%"
        AND table_name not like "task%"'
    fi
    query -e "$sql" | xargs
}

get_all_db_size_bytes() {
    local sum=0
    local db
    local size
    for db in "${dbs[@]}"; do
        size=$(get_db_size_bytes $db)
        sum=$((sum + size))
    done
    echo $sum
}

rotate_bkups() {
    local old_bkups=()
    local max=$((MAX_BKUP + 1))
    (
        cd "$(dirname $BKUP_PATH)"
        if ! [ -d "$BKUP_PATH" ]; then
            __info "backup path $BKUP_PATH dose not exist!"
            exit 1
        fi
        __info "Archive Backup Files..."
        find $BKUP_PATH -type f | xargs ls -lah
        tar czvf onecloud.bkup.$BKUP_DATE.tar.gz $BKUP_DATE && rm -rf $BKUP_DATE
        echo
        __info "Backup result: "
        ls -lah $(readlink -f onecloud.bkup.$BKUP_DATE.tar.gz)
    )
    old_bkups=($(find $(dirname $BKUP_PATH) -name "onecloud*.gz" | sort --reverse | tail -n +$max))
    title "Cleaning"
    if [ "${#old_bkups[@]}" -gt 0 ]; then
        __info "cleaning old backups: ${old_bkups[*]}"
        if ! rm -f "${old_bkups[@]}"; then
            __info "rm old backup files error! ${old_bkups[*]}"
            exit 1
        fi
    fi
    title "All DONE"
}

backup_etcd() {
    title "Backup ETCD"
    local etcd_id="$(docker ps -a | grep etcd | grep Up | grep -v pause | grep 'etcd --adv' | head -1 | awk '{print $1}' || :)"
    local etcdctl=(docker exec $etcd_id /usr/local/bin/etcdctl)
    if [ -z "$etcd_id" ]; then
        echo "Docekr or ETCD is not running. ignore etcd backup"
        return
    fi

    __info "$(${etcdctl[@]} version | xargs)"

    ETCDCTL_API=3 ${etcdctl[@]} snapshot save /tmp/etcd_snapshot_$BKUP_DATE.db \
        --cacert /etc/kubernetes/pki/etcd/ca.crt \
        --cert /etc/kubernetes/pki/etcd/server.crt \
        --key /etc/kubernetes/pki/etcd/server.key

    ETCDCTL_API=3 ${etcdctl[@]} snapshot status /tmp/etcd_snapshot_$BKUP_DATE.db

    docker cp $etcd_id:/tmp/etcd_snapshot_$BKUP_DATE.db $BKUP_PATH

    docker exec $etcd_id rm -f /tmp/etcd_snapshot_$BKUP_DATE.db
}

backup_k8s() {
    title "Backup K8s"
    kubectl -n onecloud -o yaml get deployment onecloud-operator >$BKUP_PATH/onecloud-operator.$BKUP_DATE.yml
    kubectl -n onecloud -o yaml get oc >$BKUP_PATH/oc.$BKUP_DATE.yml
    sed -i -e '/^ *creationTimestamp:/d' -e '/^ *resourceVersion:/d' -e '/^ *selfLink:/d' -e '/^ *uid:/d' $BKUP_PATH/onecloud-operator.$BKUP_DATE.yml
    sed -i -e '/^ *creationTimestamp:/d' -e '/^ *resourceVersion:/d' -e '/^ *selfLink:/d' -e '/^ *uid:/d' $BKUP_PATH/oc.$BKUP_DATE.yml
    __info "K8s backup files:"
    find $BKUP_PATH -name '*yml' -type f | xargs ls -lah
}

main() {
    init_db
    backup_k8s
    backup_etcd
    backup_db
    rotate_bkups
}

main
