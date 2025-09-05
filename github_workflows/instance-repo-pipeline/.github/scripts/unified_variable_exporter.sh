#!/bin/bash
# Unified Variable Exporter for EnvGene Pipeline Steps
# ===================================================
# This script provides a unified way to export all environment variables needed for:
# - Generate inventory
# - Credential Rotation  
# - Build Env
# - Generate Effective Set
# - Git Commit
#
# Usage: ./unified_variable_exporter.sh <step_name> <matrix_environment> [variables_json]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="${2:-INFO}"
    local step_prefix="[${STEP_NAME:-UNIFIED}]"
    echo -e "${BLUE}🔧 ${step_prefix}${NC} $1" >&2
}

# Get script arguments
STEP_NAME="${1:-}"
MATRIX_ENVIRONMENT="${2:-}"
VARIABLES_JSON="${3:-}"

if [ -z "$STEP_NAME" ] || [ -z "$MATRIX_ENVIRONMENT" ]; then
    log "❌ ERROR: Missing required arguments" "ERROR"
    log "Usage: $0 <step_name> <matrix_environment> [variables_json]"
    log "Example: $0 generate_inventory test-cluster/e01 '{\"MY_VAR\": \"value\"}'"
    exit 1
fi

log "🚀 Starting unified variable export process..."

# 1. Export pipeline variables from YAML
export_pipeline_vars_from_yaml() {
    log "Loading variables from pipeline_vars.yaml..."
    
    local pipeline_vars_file=".github/pipeline_vars.yaml"
    local exported_count=0
    
    if [ ! -f "$pipeline_vars_file" ]; then
        log "⚠️  pipeline_vars.yaml not found, skipping" "WARN"
        return 0
    fi
    
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [ -z "$line" ] || echo "$line" | grep -q "^[[:space:]]*#"; then
            continue
        fi
        
        # Check if it's a variable assignment
        if echo "$line" | grep -q "^[^:]*:"; then
            local key=$(echo "$line" | cut -d':' -f1 | xargs)
            local value=$(echo "$line" | cut -d':' -f2- | xargs)
            
            # Remove quotes if present
            if echo "$value" | grep -q '^".*"$' || echo "$value" | grep -q "^'.*'$"; then
                value=$(echo "$value" | sed 's/^.\(.*\).$/\1/')
            fi
            
            if [ -n "$key" ] && [ -n "$value" ]; then
                echo "export \"$key\"=\"$value\""
                log "  Found: $key = $value"
                exported_count=$((exported_count + 1))
            fi
        fi
    done < "$pipeline_vars_file"
    
    log "✅ Exported $exported_count variables from pipeline_vars.yaml"
    echo $exported_count >&2
}

# 2. Export GitHub workflow input variables
export_github_inputs() {
    log "Loading GitHub workflow input variables..."
    
    local exported_count=0
    
    # Common GitHub inputs that are available in all steps
    local github_inputs="DEPLOYMENT_TICKET_ID ENV_NAMES ENV_BUILDER GET_PASSPORT CMDB_IMPORT ENV_TEMPLATE_VERSION GENERATE_EFFECTIVE_SET GITHUB_PIPELINE_API_INPUT"
    
    for var in $github_inputs; do
        local value=""
        eval "value=\${$var:-}"
        if [ -n "$value" ]; then
            echo "export \"$var\"=\"$value\""
            log "  Input: $var = $value"
            exported_count=$((exported_count + 1))
        fi
    done
    
    log "✅ Exported $exported_count GitHub input variables"
    echo $exported_count >&2
}

# 3. Export API input variables
export_api_input_variables() {
    local api_input="${GITHUB_PIPELINE_API_INPUT:-}"
    
    if [ -z "$api_input" ]; then
        log "No API input provided, skipping API variable export"
        return 0
    fi
    
    log "Processing API input (${#api_input} chars)..."
    
    local exported_count=0
    
    # Try to parse as JSON first
    if command -v jq >/dev/null 2>&1 && echo "$api_input" | jq . >/dev/null 2>&1; then
        log "Parsed API input as JSON"
        # Use process substitution to avoid subshell issues
        while IFS= read -r line; do
            local key=$(echo "$line" | cut -d':' -f1 | xargs)
            local value=$(echo "$line" | cut -d':' -f2- | xargs)
            
            if [ -n "$key" ] && [ -n "$value" ] && [ "$value" != "null" ]; then
                echo "export \"$key\"=\"$value\""
                log "  API: $key = $value"
                exported_count=$((exported_count + 1))
            fi
        done < <(echo "$api_input" | jq -r 'to_entries[] | "\(.key): \(.value)"')
    else
        # Fall back to key=value format
        log "Parsing API input as key=value pairs"
        while IFS= read -r line; do
            if echo "$line" | grep -q "^[^=]*="; then
                local key=$(echo "$line" | cut -d'=' -f1 | xargs)
                local value=$(echo "$line" | cut -d'=' -f2- | xargs)
                
                if [ -n "$key" ] && [ -n "$value" ]; then
                    echo "export \"$key\"=\"$value\""
                    log "  API: $key = $value"
                    exported_count=$((exported_count + 1))
                fi
            fi
        done < <(echo "$api_input")
    fi
    
    log "✅ Exported $exported_count variables from API input"
    echo $exported_count >&2
}

# 4. Export variables from JSON
export_variables_from_json() {
    if [ -z "$VARIABLES_JSON" ] || [ "$VARIABLES_JSON" = "{}" ] || [ "$VARIABLES_JSON" = "null" ]; then
        log "No variables JSON provided, skipping JSON export"
        return 0
    fi
    
    log "Loading variables from JSON..."
    
    local exported_count=0
    
    if command -v jq >/dev/null 2>&1 && echo "$VARIABLES_JSON" | jq . >/dev/null 2>&1; then
        # Use process substitution to avoid subshell issues
        while IFS= read -r line; do
            local key=$(echo "$line" | cut -d':' -f1 | xargs)
            local value=$(echo "$line" | cut -d':' -f2- | xargs)
            
            if [ -n "$key" ] && [ -n "$value" ] && [ "$value" != "null" ]; then
                echo "export \"$key\"=\"$value\""
                log "  JSON: $key = $value"
                exported_count=$((exported_count + 1))
            fi
        done < <(echo "$VARIABLES_JSON" | jq -r 'to_entries[] | "\(.key): \(.value)"')
    else
        log "❌ Invalid JSON format or jq not available" "ERROR"
        return 0
    fi
    
    log "✅ Exported $exported_count variables from JSON"
    echo $exported_count >&2
}

# 5. Export system variables
export_system_variables() {
    log "Exporting system variables..."
    
    local exported_count=0
    
    # Essential system variables that should be available in all steps
    local system_vars="CI_PROJECT_DIR SECRET_KEY GITHUB_ACTIONS GITHUB_REPOSITORY GITHUB_REF_NAME GITHUB_USER_EMAIL GITHUB_USER_NAME GITHUB_TOKEN ENVGENE_AGE_PUBLIC_KEY ENVGENE_AGE_PRIVATE_KEY DOCKER_IMAGE_PIPEGENE DOCKER_IMAGE_ENVGENE DOCKER_IMAGE_EFFECTIVE_SET_GENERATOR"
    
    for var in $system_vars; do
        local value=""
        eval "value=\${$var:-}"
        if [ -n "$value" ]; then
            echo "export \"$var\"=\"$value\""
            log "  System: $var = $value"
            exported_count=$((exported_count + 1))
        fi
    done
    
    log "✅ Exported $exported_count system variables"
    echo $exported_count >&2
}

# 6. Export job-specific variables
export_job_specific_variables() {
    log "Exporting job-specific variables for: $MATRIX_ENVIRONMENT"
    
    # Extract environment components
    local cluster_name=$(echo "$MATRIX_ENVIRONMENT" | cut -d'/' -f1)
    local environment_name=$(echo "$MATRIX_ENVIRONMENT" | cut -d'/' -f2 | xargs)
    
    # Export job variables
    echo "export \"FULL_ENV\"=\"$MATRIX_ENVIRONMENT\""
    echo "export \"ENV_NAMES\"=\"$MATRIX_ENVIRONMENT\""
    echo "export \"CLUSTER_NAME\"=\"$cluster_name\""
    echo "export \"ENVIRONMENT_NAME\"=\"$environment_name\""
    echo "export \"ENV_NAME\"=\"$environment_name\""
    echo "export \"ENV_NAME_SHORT\"=\"$(echo "$environment_name" | awk -F "/" '{print $NF}')\""
    echo "export \"SANITIZED_NAME\"=\"$(echo "$MATRIX_ENVIRONMENT" | sed 's|/|_|g')\""
    echo "export \"PROJECT_DIR\"=\"${CI_PROJECT_DIR:-$(pwd)}\""
    
    log "  Job: FULL_ENV = $MATRIX_ENVIRONMENT"
    log "  Job: ENV_NAMES = $MATRIX_ENVIRONMENT"
    log "  Job: CLUSTER_NAME = $cluster_name"
    log "  Job: ENVIRONMENT_NAME = $environment_name"
    log "  Job: ENV_NAME = $environment_name"
    log "  Job: ENV_NAME_SHORT = $(echo "$environment_name" | awk -F "/" '{print $NF}')"
    log "  Job: SANITIZED_NAME = $(echo "$MATRIX_ENVIRONMENT" | sed 's|/|_|g')"
    log "  Job: PROJECT_DIR = ${CI_PROJECT_DIR:-$(pwd)}"
    
    # Add step-specific variables
    export_step_specific_variables
    
    log "✅ Exported job-specific variables"
    echo 1 >&2
}

# 7. Export step-specific variables
export_step_specific_variables() {
    case "$STEP_NAME" in
        "generate_inventory"|"credential_rotation"|"env_build"|"generate_effective_set"|"git_commit")
            # Common variables for all steps
            echo "export \"INSTANCES_DIR\"=\"${PROJECT_DIR}/environments\""
            echo "export \"module_ansible_dir\"=\"/module/ansible\""
            echo "export \"module_inventory\"=\"${PROJECT_DIR}/configuration/inventory.yaml\""
            echo "export \"module_ansible_cfg\"=\"/module/ansible/ansible.cfg\""
            echo "export \"module_config_default\"=\"/module/templates/defaults.yaml\""
            echo "export \"envgen_args\"=\" -vvv\""
            echo "export \"envgen_debug\"=\"true\""
            echo "export \"GIT_STRATEGY\"=\"none\""
            echo "export \"COMMIT_ENV\"=\"true\""
            
            log "  Step: INSTANCES_DIR = ${PROJECT_DIR}/environments"
            log "  Step: module_ansible_dir = /module/ansible"
            log "  Step: module_inventory = ${PROJECT_DIR}/configuration/inventory.yaml"
            log "  Step: module_ansible_cfg = /module/ansible/ansible.cfg"
            log "  Step: module_config_default = /module/templates/defaults.yaml"
            log "  Step: envgen_args =  -vvv"
            log "  Step: envgen_debug = true"
            log "  Step: GIT_STRATEGY = none"
            log "  Step: COMMIT_ENV = true"
            ;;
    esac
    
    case "$STEP_NAME" in
        "credential_rotation")
            echo "export \"CRED_ROTATION_FORCE\"=\"${CRED_ROTATION_FORCE:-}\""
            echo "export \"CRED_ROTATION_PAYLOAD\"=\"${CRED_ROTATION_PAYLOAD:-}\""
            echo "export \"PUBLIC_AGE_KEYS\"=\"${PUBLIC_AGE_KEYS:-}\""
            
            log "  Step: CRED_ROTATION_FORCE = ${CRED_ROTATION_FORCE:-}"
            log "  Step: CRED_ROTATION_PAYLOAD = ${CRED_ROTATION_PAYLOAD:-}"
            log "  Step: PUBLIC_AGE_KEYS = ${PUBLIC_AGE_KEYS:-}"
            ;;
    esac
}

# Main execution
main() {
    # 1. Export pipeline variables from YAML
    export_pipeline_vars_from_yaml
    
    # 2. Export GitHub workflow inputs
    export_github_inputs
    
    # 3. Export API input variables
    export_api_input_variables
    
    # 4. Export variables from JSON
    export_variables_from_json
    
    # 5. Export system variables
    export_system_variables
    
    # 6. Export job-specific variables
    export_job_specific_variables
    
    log "🎉 Variable export completed successfully!" >&2
}

# Run main function
main "$@"
