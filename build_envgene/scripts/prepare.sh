#!/bin/bash
set -e

#### input variables
# envgen_debug
# envgen_args
# module_inventory
# CI_SERVER_URL
# GITLAB_TOKEN

mkdir -p "$CI_PROJECT_DIR/build_env/tmp"
if [ -d "/build_env/tmp" ]; then
    cp -r /build_env/tmp/* "$CI_PROJECT_DIR/build_env/tmp/" || true
fi

exit $status

