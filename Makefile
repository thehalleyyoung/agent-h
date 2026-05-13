.PHONY: help clone install test demo clean

REPOS := stepback ragdoctor flowwarden
GH_OWNER := thehalleyyoung
WORK := .checkouts

help:
	@echo "agent-h Makefile targets:"
	@echo "  make clone    - git clone the three component repos into $(WORK)/"
	@echo "  make install  - pip install the three components in editable mode"
	@echo "  make test     - run each component's pytest suite"
	@echo "  make demo     - run examples/integrated_demo.py"
	@echo "  make clean    - remove $(WORK)/"

clone:
	@mkdir -p $(WORK)
	@for r in $(REPOS); do \
	  if [ -d $(WORK)/$$r ]; then \
	    echo "[$$r] already cloned, pulling..."; \
	    git -C $(WORK)/$$r pull --ff-only; \
	  else \
	    echo "[$$r] cloning..."; \
	    git clone --depth=1 https://github.com/$(GH_OWNER)/$$r.git $(WORK)/$$r; \
	  fi; \
	done

install: clone
	pip install -e $(WORK)/stepback'[dev,shims]'
	pip install -e $(WORK)/ragdoctor'[dev]'
	pip install -e $(WORK)/flowwarden

test:
	@for r in $(REPOS); do \
	  echo "===== pytest: $$r ====="; \
	  (cd $(WORK)/$$r && python -m pytest -q --maxfail=5) || exit 1; \
	done

demo:
	python examples/integrated_demo.py

clean:
	rm -rf $(WORK)
