import base64
import os
import re
from pathlib import Path

from cryptography.fernet import Fernet
from envgenehelper import logger

from build_pipegene.scripts.cloud_passport.git import GitLabClient, GitRepoManager
from python.envgene.envgenehelper import openYaml
from python.envgene.envgenehelper.errors import ValidationError


def get_integration_config(integration_config_path) -> dict:
    integration_config = {}
    if integration_config_path.exists():
        integration_config = openYaml(integration_config_path)
        logger.info(f"integration_config = {integration_config}")
    else:
        logger.warning(f"Integration config missing: {integration_config_path}")
    return integration_config


def find_downstream_pipeline(pipeline_jobs, env_name) -> dict | None:
    expected = f"trigger-discovery-passport.{env_name.replace('_', '-')}-trigger"
    logger.info(f"Searching for downstream pipeline with names: "
                f"'trigger_discovery_passport' or '{expected}'")
    for item in pipeline_jobs:
        name = item.get("name", "")
        logger.debug(f"Checking job '{name}'")

        if name == "trigger_discovery_passport" or name == expected:
            downstream = item.get("downstream_pipeline", {})
            result = {
                "project_id": downstream.get("project_id"),
                "pipeline_id": downstream.get("id"),
                "ref": downstream.get("ref")
            }
            logger.info(f"Downstream pipeline found: {result}")
            return result
    logger.warning("Downstream pipeline not found")


def cred_id(val):
    match = re.search(r".*\('([^']+)'\)\.(\w+)", val)
    if match:
        cred_name = match.group(1)
        cred_property = match.group(2)
        return [cred_name, cred_property]
    else:
        raise ValueError(f"Value '{val}' does not match expected format")


def get_cred_config(cred_config_path: Path):
    if not cred_config_path.exists():
        raise FileNotFoundError(f"{cred_config_path} not found")
    key_bytes = base64.urlsafe_b64decode(os.getenv("SECRET_KEY"))
    encrypted_data = cred_config_path.read_bytes()
    decrypted_data = Fernet(key_bytes).decrypt(encrypted_data)
    cred_config_path.write_bytes(decrypted_data)
    return openYaml(cred_config_path)


def main():
    base_dir = os.getenv("CI_PROJECT_DIR")

    integration_config = get_integration_config(Path(f"{base_dir}/configuration/integration.yml"))
    cred_config = get_cred_config(Path(f"{base_dir}/configuration/credentials/credentials.yml"))

    self_token = cred_id(integration_config.get("self_token"))
    git_token = cred_config[self_token[0]]["data"][self_token[1]]

    repo = GitRepoManager(
        repo_path=base_dir,
        git_user_email=os.getenv("GITLAB_USER_EMAIL"),
        git_user_name=os.getenv("GITLAB_USER_LOGIN"),
        git_token=git_token,
        server_host=os.getenv("CI_SERVER_HOST"),
        project_path=os.getenv("CI_PROJECT_PATH"),
        branch=os.getenv("CI_COMMIT_REF_NAME")
    )
    repo.prepare_repo()

    gl = GitLabClient(
        token=git_token,
        api_url=os.getenv("CI_API_V4_URL")
    )

    project_id = os.getenv("CI_PROJECT_ID")
    pipeline_id = os.getenv("CI_PIPELINE_ID")
    env_name = os.getenv("ENV_NAME")

    pipeline_jobs = gl.get_pipeline_bridges(project_id, pipeline_id)
    logger.info(f"pipeline_jobs fetched: {pipeline_jobs}")

    downstream = find_downstream_pipeline(pipeline_jobs, env_name)
    if not downstream:
        raise ValidationError("Downstream pipeline not found")
    logger.info(f"Downstream: {downstream}")


if __name__ == "__main__":
    main()
