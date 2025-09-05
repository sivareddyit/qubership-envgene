#!/usr/bin/env python3
"""
Script to collect all environment variables and create JSON for composite action.
"""

import os
import json
import sys


def get_all_pipeline_variables():
    """
    Collect all environment variables that should be passed to subsequent jobs.
    """
    variables = {}
    
    # Read from GITHUB_ENV file first (highest priority)
    github_env_file = os.getenv("GITHUB_ENV")
    if github_env_file and os.path.exists(github_env_file):
        try:
            with open(github_env_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        try:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Only include non-empty values
                            if value:
                                variables[key] = value
                        except ValueError:
                            print(f"⚠️  Warning: Skipping malformed line {line_num}: {line}")
                            continue
        except Exception as e:
            print(f"⚠️  Error reading GITHUB_ENV file: {e}")
    
    # Fallback to environment variables if GITHUB_ENV file is empty
    if not variables:
        print("📝 Falling back to environment variables")
        for key, value in os.environ.items():
            if value and is_pipeline_variable(key):
                variables[key] = value
    
    # Filter variables to exclude system/secret ones
    filtered_variables = {}
    for key, value in variables.items():
        if is_pipeline_variable(key) and not is_secret_variable(key):
            filtered_variables[key] = value
    
    return filtered_variables


def is_pipeline_variable(key):
    """
    Determine if a variable should be passed to subsequent jobs.
    """
    # System variables to exclude
    system_vars = {
        'GITHUB_ENV', 'GITHUB_OUTPUT', 'GITHUB_WORKSPACE', 'GITHUB_REPOSITORY', 
        'GITHUB_SHA', 'GITHUB_REF', 'GITHUB_ACTIONS', 'GITHUB_REF_NAME',
        'GITHUB_EVENT_NAME', 'GITHUB_EVENT_PATH', 'GITHUB_HEAD_REF', 'GITHUB_BASE_REF',
        'GITHUB_SERVER_URL', 'GITHUB_API_URL', 'GITHUB_GRAPHQL_URL',
        'RUNNER_OS', 'RUNNER_ARCH', 'RUNNER_NAME', 'RUNNER_ENVIRONMENT', 'RUNNER_TOOL_CACHE',
        'RUNNER_TEMP', 'RUNNER_WORKSPACE', 'RUNNER_PERFLOG', 'RUNNER_TRACKING_ID',
        'HOME', 'PATH', 'SHELL', 'USER', 'LANG', 'PWD', 'OLDPWD',
        'TERM', 'HOSTNAME', 'HOSTTYPE', 'MACHTYPE', 'OSTYPE',
        'CI_COMMIT_REF_NAME', 'CI_PROJECT_DIR',
        # Python system variables
        'PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED', 'PYTHON_SHA256',
        # GPG and other technical variables
        'GPG_KEY', 'GITHUB_PIPELINE_API_INPUT'
    }
    
    if key in system_vars:
        return False
    
    # System prefixes to exclude
    if key.startswith(('RUNNER_', 'GITHUB_', 'ACTIONS_', 'INPUT_', 'ImageOS', 'ImageVersion', 
                      'AGENT_', 'ANDROID_', 'JAVA_HOME_', 'GOROOT_', 'HOMEBREW_', 'XDG_',
                      'DOTNET_', 'PIPX_', 'GHCUP_')):
        # Allow specific exceptions
        pipeline_exceptions = {'GITHUB_TOKEN', 'GITHUB_USER_EMAIL', 'GITHUB_USER_NAME'}
        if key not in pipeline_exceptions:
            return False
    
    return True


def is_secret_variable(key):
    """
    Check if variable contains sensitive information.
    """
    secret_keywords = ['SECRET', 'KEY', 'TOKEN', 'PASSWORD', 'PRIVATE']
    return any(keyword in key.upper() for keyword in secret_keywords)


def main():
    """
    Main function to collect variables and output JSON.
    """
    print("🔍 Collecting all pipeline variables...")
    
    variables = get_all_pipeline_variables()
    
    if not variables:
        print("⚠️ No pipeline variables found")
        variables_json = "{}"
    else:
        print(f"📊 Found {len(variables)} pipeline variables:")
        for key, value in sorted(variables.items()):
            # Don't print sensitive values
            if is_secret_variable(key):
                print(f"  {key}: ***")
            else:
                print(f"  {key}: {value}")
        
        variables_json = json.dumps(variables, separators=(',', ':'))
    
    # Write to GITHUB_OUTPUT
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            # Use multiline output for large JSON
            f.write(f"variables_json<<EOF\n{variables_json}\nEOF\n")
        print("✅ Variables JSON written to GITHUB_OUTPUT")
    else:
        print("❌ GITHUB_OUTPUT not available")
        sys.exit(1)
    
    print(f"📝 Generated JSON length: {len(variables_json)} characters")


if __name__ == "__main__":
    main()
