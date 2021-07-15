test:
	python -m unittest discover -s tests -v

TMP_PCI_IDS = /tmp/ocboot-pci.ids
DEST_PCI_IDS = $(CURDIR)/onecloud/roles/utils/update-pciids/files/pci.ids

update-pciids:
	curl -o $(TMP_PCI_IDS) http://pci-ids.ucw.cz/v2.2/pci.ids && \
		mv $(TMP_PCI_IDS) $(DEST_PCI_IDS)

.PHONY: test
