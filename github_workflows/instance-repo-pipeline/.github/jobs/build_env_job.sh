#!/bin/bash
set -e

# build_env_job.sh
# This script implements the logic from prepare_env_build_job function
# It performs environment build operations including certificate updates,
# template version setting, environment building, and cleanup

# Activate Python virtual environment
source /module/venv/bin/activate

# Enable debug mode if envgen_debug is set
if [ "${envgen_debug}" == "true" ]; then
  set -o xtrace
fi

# Update CA certificates if certs directory exists
if [ -d "${CI_PROJECT_DIR}/configuration/certs" ]; then
  bash /module/scripts/update_ca_cert.sh
fi

# Execute main.py to build the environment
echo "Executing main.py to build environment..."
cd /build_env
if ! python3 /build_env/scripts/build_env/main.py; then
  echo "Failed to execute main.py"
  exit 1
fi

# After script: Copy tmp files from /build_env/tmp to CI_PROJECT_DIR/tmp
echo "Copying tmp files..."
mkdir -p "${CI_PROJECT_DIR}/tmp"
if [ -d "/build_env/tmp" ]; then
  cp -r /build_env/tmp/* "${CI_PROJECT_DIR}/tmp" 2>/dev/null || true
fi

echo "Build environment job completed successfully"
