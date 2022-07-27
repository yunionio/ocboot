test:
	python3 -m unittest discover -s tests -v

TMP_PCI_IDS = /tmp/ocboot-pci.ids
DEST_PCI_IDS = $(CURDIR)/onecloud/roles/utils/gpu-init/files/pci.ids

update-pciids:
	curl -o $(TMP_PCI_IDS) http://pci-ids.ucw.cz/v2.2/pci.ids && \
		mv $(TMP_PCI_IDS) $(DEST_PCI_IDS)

.PHONY: test

REGISTRY ?= "registry.cn-beijing.aliyuncs.com/yunionio"
VERSION ?= $(shell git describe --exact-match 2> /dev/null || \
                git describe --match=$(git rev-parse --short=8 HEAD) --always --dirty --abbrev=8)

image:
	docker buildx build --platform linux/arm64,linux/amd64 --push \
		-t $(REGISTRY)/ocboot:$(VERSION) -f ./Dockerfile .
