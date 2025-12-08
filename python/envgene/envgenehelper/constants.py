# envgenehelper/constants.py

cleanup_targets = [
    "Applications",
    "Namespaces",
    "Profiles",
    "cloud.yml",
    "tenant.yml",
    "bg_domain.yml",
    "composite_structure.yml",
]

# Targets to exclude from sparse checkout in generate_effective_set job
# Note: Namespaces is intentionally excluded here because the Java effective-set-generator
# needs namespace definitions from Git when env-builder doesn't render them (SBOM-only flow)
sparse_checkout_exclude_targets = [
    "Applications",
    "Profiles",
    "cloud.yml",
    "tenant.yml",
    "bg_domain.yml",
    "composite_structure.yml",
]
