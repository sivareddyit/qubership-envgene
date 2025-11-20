import base64
import re

import requests
from cryptography.fernet import Fernet
from envgenehelper import logger
import os
from pathlib import Path

from build_pipegene.scripts.cloud_passport.GitRepoManager import GitRepoManager
from python.envgene.envgenehelper import yaml, readYaml, openYaml

env_name = os.getenv("ENV_NAME")
base_dir = os.getenv("CI_PROJECT_DIR")
envgen_debug = os.getenv("envgen_debug")

# path to discovery files
envs_directory_path = f"{base_dir}/environments"

dest_archive_path = "/tmp/archive.zip"
dest_unpack_files = "/tmp/passport"
passport_path = f"{base_dir}/configuration/group_vars/{env_name}"

# gitlab ci/cd variable for encrypt/decrypt sensitive data
instance_secret_key = os.getenv("SECRET_KEY")

cred_config_path = Path(f"{base_dir}/configuration/credentials/credentials.yml")
integration_config_path = Path(f"{base_dir}/configuration/integration.yml")

# if try to get passport from this repo
get_passport_job_name = "get_cloud_passport"
url_pipe_bridges = (
    f"{os.getenv('CI_API_V4_URL')}/projects/{os.getenv('CI_PROJECT_ID')}"
    f"/pipelines/{os.getenv('CI_PIPELINE_ID')}/bridges"
)

url_pipe_jobs = (
    f"{os.getenv('CI_API_V4_URL')}/projects/{os.getenv('downstream_project_id')}"
    f"/pipelines/{os.getenv('downstream_pipe_id')}/jobs"
)

# if try to get passport from discovery-tool repo
archive_url = (
    f"{os.getenv('CI_API_V4_URL')}/projects/{os.getenv('parent_project_id')}"
    f"/jobs/artifacts/{os.getenv('parent_pipe_branch')}/download"
    f"?job={os.getenv('parent_job_name')}"
)

gitlab_vars_api = (
    f"{os.getenv('CI_API_V4_URL')}/projects/{os.getenv('parent_project_id')}/variables"
)

header_text = (
    "The contents of this file is generated from Cloud Passport discovery procedure.\n"
    "Contents will be overwritten by next discovery.\n"
    "Please do not modify this file."
)
