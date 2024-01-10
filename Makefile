test:
	python3 -m unittest discover -s tests -v

TMP_PCI_IDS = /tmp/ocboot-pci.ids
DEST_PCI_IDS = $(CURDIR)/onecloud/roles/utils/gpu-init/files/pci.ids
OLD_VERSION?=

update-pciids:
	curl -o $(TMP_PCI_IDS) http://pci-ids.ucw.cz/v2.2/pci.ids && \
		mv $(TMP_PCI_IDS) $(DEST_PCI_IDS)

.PHONY: test

REGISTRY ?= "registry.cn-beijing.aliyuncs.com/yunionio"
VERSION ?= v4-k3s.4

image:
	docker buildx build --platform linux/arm64,linux/amd64 --push \
		-t $(REGISTRY)/ocboot:$(VERSION) -f ./Dockerfile .

generate-docker-compose-manifests:
	VERSION=$(VERSION) python3 ./generate-compose.py > ./compose/docker-compose.yml
	@if [ -n "$(OLD_VERSION)" ] && [ -n "$(VERSION)" ]; then \
		perl -pi -e "s#$(OLD_VERSION)#$(VERSION)#" $$(find . -type f \( -iname \*.py -o -iname \*.yaml -o -iname \*.sh \) ! -path "./.git/*" ); \
	fi
