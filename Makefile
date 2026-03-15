COLLECTION_PATH = $(HOME)/.ansible/collections/ansible_collections/wzzrd/pihole
PYTHON_VERSION  = 3.11

.PHONY: all help sanity unit lint black black-check molecule-dns molecule-blocklists

all: unit black lint sanity

help:
	@echo "Available targets:"
	@echo "  sanity            ansible-test sanity (run from installed collection path)"
	@echo "  unit              pytest unit tests"
	@echo "  lint              ansible-lint"
	@echo "  black             auto-format with black"
	@echo "  black-check       check formatting with black"
	@echo "  molecule-dns      molecule test -s dns_dhcp"
	@echo "  molecule-blocklists  molecule test -s blocklists"

sanity:
	#cd $(COLLECTION_PATH) && ansible-test sanity --python $(PYTHON_VERSION)
	ansible-test sanity --python $(PYTHON_VERSION)

unit:
	pytest tests/unit/ -v

lint:
	ansible-lint

black:
	black plugins/ tests/

black-check:
	black --check plugins/ tests/

molecule-dns:
	molecule test -s dns_dhcp

molecule-blocklists:
	molecule test -s blocklists
