#!/usr/bin/env bash

export KUBECONFIG=/etc/kubernetes/admin.conf
source <(/opt/yunion/bin/ocadm cluster rcadmin)
CommercialOrCommunityEdition=$(kubectl -n onecloud get oc -o jsonpath='{.items[0].metadata.annotations.onecloud\.yunion\.io/edition}' || :)
CurrentVersion=$(kubectl -n onecloud get onecloudclusters default -o=jsonpath='{.spec.version}')
# echo "CommercialOrCommunityEdition: [[$CommercialOrCommunityEdition]]; CurrentVersion: [[$CurrentVersion]]"

if [[ "$CommercialOrCommunityEdition" == "ce" ]]; then
    kubectl -n onecloud patch onecloudcluster default --type='json' -p '[{"op": "replace", "path": "/spec/autoupdate/disable", "value": true }]'
    # delete configmap
    kubectl delete configmap -n onecloud default-autoupdate &>/dev/null || :
    pods=($(kubectl get pods -A | grep autoupdate | awk '{print $2}'))
    if [[ "${#pods[@]}" -gt 0 ]]; then
        kubectl -n onecloud delete pods "${pods[@]}" &>/dev/null || :
    fi
    kubectl -n onecloud delete configmap default-autoupdate &>/dev/null || :
    kubectl -n onecloud delete deployments default-autoupdate &>/dev/null || :
elif [[ "$CommercialOrCommunityEdition" == "ee" ]]; then
    kubectl -n onecloud patch onecloudcluster default --type='json' -p '[{"op": "replace", "path": "/spec/autoupdate/disable", "value": false }]'
fi

