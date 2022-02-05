#!/usr/bin/env bash
set -e
export PATH=$PATH:/opt/yunion/bin
export KUBECONFIG=/etc/kubernetes/admin.conf

OCVER=$(kubectl -n onecloud get onecloudclusters default -o=jsonpath='{.spec.version}')
echo "/opt/yunion/bin/ocadm cluster update --version $OCVER --wait"

if [ "$1" == "-all" ]; then
    nslist="$(kubectl get namespace|tail -n +2| awk '{print $1}' | xargs)"
else
    nslist=onecloud
fi

for namespace in $nslist; do
    for typ in daemonset deployment; do
        kubectl get $typ -n $namespace -o jsonpath='{range .items[*]}{@.metadata.name}{"@"}{@.spec.template.spec.containers[*].name}{"%"}{@.spec.template.spec.containers[*].image}{"\n"}{end}'} | while read line; do
            dep=$(echo $line |awk -F@ '{print $1}')
            names=($(echo $line|sed -e 's#.*@##g' -e 's#%.*$##g'))
            images=($(echo $line |sed -e 's#.*%##'))
            echo -e "kubectl set image -n $namespace $typ/$dep \c"
            for idx in ${!names[@]}; do
                echo -e "${names[$idx]}=${images[$idx]} \c"
            done
        echo
        done
        kubectl get $typ -n $namespace -o jsonpath='{range .items[*]}{@.metadata.name}{"@"}{@.spec.template.spec.initContainers[*].name}{"%"}{@.spec.template.spec.initContainers[*].image}{"\n"}{end}'} |while read line; do
            if ! echo "$line" |grep -q '@%$'; then
                dep=$(echo $line |awk -F@ '{print $1}')
                echo -e "kubectl set image -n $namespace $typ/$dep \c"
                img=$(echo "$line" |sed -e 's#.*%##')
                echo -e "init=$img \c"
            fi
        done |sed -e 's# kubectl#\nkubectl#g'
    done
done
