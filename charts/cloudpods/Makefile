lint:
	helm template --debug . --set cluster.mysql.statefulset.enabled=true -f values-dev.yaml

install-dev:
	helm install --name-template default --namespace onecloud --debug  . -f values-dev.yaml  --create-namespace

update-dev:
	helm upgrade -n onecloud default . -f values-dev.yaml

delete-dev:
	helm delete -n onecloud default
