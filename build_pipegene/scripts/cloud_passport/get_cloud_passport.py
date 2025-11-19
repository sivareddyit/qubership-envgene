import base64
import re

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

discovery_job_name = "trigger_discovery_passport"
auto_discovery_job_name = f"trigger-discovery-passport.{env_name.replace('_', '-')}-trigger"

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


def cred_id(val):
    match = re.search(r".*\('([^']+)'\)\.(\w+)", val)
    if match:
        cred_name = match.group(1)
        cred_property = match.group(2)
        return [cred_name, cred_property]
    else:
        raise ValueError(f"Value '{val}' does not match expected format")


integration_config = {}

if integration_config_path.exists():
    integration_config = openYaml(integration_config_path)
    logger.info(f"integration_config = {integration_config}")
else:
    logger.warning(f"Integration config missing: {integration_config_path}")

if not cred_config_path.exists():
    raise FileNotFoundError(f"{cred_config_path} not found")
key_bytes = base64.urlsafe_b64decode(instance_secret_key)
fernet = Fernet(key_bytes)
encrypted_data = cred_config_path.read_bytes()
decrypted_data = fernet.decrypt(encrypted_data)
cred_config_path.write_bytes(decrypted_data)
cred_config = openYaml(cred_config_path)

self_token = cred_id(integration_config.get("self_token"))
gitlab_token = cred_id(integration_config['cp_discovery']['gitlab']['token'])


ci_project_dir = os.getenv("CI_PROJECT_DIR")
ci_commit_ref = os.getenv("CI_COMMIT_REF_NAME")
git_user_email = os.getenv("GITLAB_USER_EMAIL")
git_user_name = os.getenv("GITLAB_USER_LOGIN")
ci_server_host = os.getenv("CI_SERVER_HOST")
ci_project_path = os.getenv("CI_PROJECT_PATH")
git_token = cred_config[self_token[0]]['data'][self_token[1]]

manager = GitRepoManager(
    repo_path=ci_project_dir,
    git_user_email=git_user_email,
    git_user_name=git_user_name,
    git_token=git_token,
    server_host=ci_server_host,
    project_path=ci_project_path,
    branch=ci_commit_ref
)

manager.prepare_repo()
