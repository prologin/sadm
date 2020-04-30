PROMTOOL ?= promtool

check: prometheus.yml
	$(PROMTOOL) check config prometheus.yml

prometheus.yml: sadm.rules.yml

sadm.rules.yml: gen_sadm_rules.py
	./$+
