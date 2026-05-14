.PHONY: help clone install test demo clean research-tier prod-tier

PROD_REPOS := stepback ragdoctor flowwarden looper mnemos bankroll toolforge adversary rerun homer cartograph manyworlds distill atelier kiln crucible
RESEARCH_REPOS := coevo groundwork
ALL_REPOS := $(PROD_REPOS) $(RESEARCH_REPOS)
GH_OWNER := thehalleyyoung
WORK := .checkouts

help:
	@echo "agent-h Makefile targets:"
	@echo "  make clone           - git clone all 12 component repos into $(WORK)/"
	@echo "  make install         - pip install all components in editable mode"
	@echo "  make prod-tier       - install only the production-tier 10 components"
	@echo "  make research-tier   - install only the research-software-tier 2 components (coevo, groundwork)"
	@echo "  make test            - run each component's pytest suite"
	@echo "  make demo            - run examples/integrated_demo.py"
	@echo "  make clean           - remove $(WORK)/"

clone:
	@mkdir -p $(WORK)
	@for r in $(ALL_REPOS); do \
	  if [ -d $(WORK)/$$r ]; then \
	    echo "[$$r] already cloned, pulling..."; \
	    git -C $(WORK)/$$r pull --ff-only; \
	  else \
	    echo "[$$r] cloning..."; \
	    git clone --depth=1 https://github.com/$(GH_OWNER)/$$r.git $(WORK)/$$r; \
	  fi; \
	done

install: clone
	@for r in $(ALL_REPOS); do \
	  echo "===== pip install -e $(WORK)/$$r ====="; \
	  pip install -e $(WORK)/$$r || exit 1; \
	done

prod-tier: clone
	@for r in $(PROD_REPOS); do \
	  echo "===== pip install -e $(WORK)/$$r ====="; \
	  pip install -e $(WORK)/$$r || exit 1; \
	done

research-tier: clone
	@for r in $(RESEARCH_REPOS); do \
	  echo "===== pip install -e $(WORK)/$$r ====="; \
	  pip install -e $(WORK)/$$r || exit 1; \
	done

test:
	@for r in $(ALL_REPOS); do \
	  echo "===== pytest: $$r ====="; \
	  (cd $(WORK)/$$r && python -m pytest -q --maxfail=5) || exit 1; \
	done

demo:
	python examples/integrated_demo.py

clean:
	rm -rf $(WORK)
