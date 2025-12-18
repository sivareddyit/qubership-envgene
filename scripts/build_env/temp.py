import os
from pathlib import Path

import asyncio
from envgenehelper import crypt, openYaml, find_all_yaml_files_by_stem
from envgenehelper import logger

from scripts.cloud_passport.main import fetch_cred_value

base_dir = os.getenv("CI_PROJECT_DIR")

cred_config = crypt.decrypt_file(Path(f"{base_dir}/configuration/credentials/credentials.yml"))
# template = Template(decrypted_creds)
cluster_name = os.getenv("CLUSTER_NAME")
environment_name = os.getenv("ENVIRONMENT_NAME")
envs_dir_path = Path(f"{base_dir}/environments")
env_def_path = Path(f"{envs_dir_path}/{cluster_name}/{environment_name}/Inventory/env_definition.yml")

env_definition = openYaml(env_def_path)

if 'artifact' in env_definition.get('envTemplate', {}):
    logger.info("Use template downloading new logic")
    artifact = env_definition['envTemplate'].get('artifact', '')
    artifact_name, artifact_version = artifact.split(':')

    artifact_def_file_name = os.path.join(base_dir, 'configuration', 'artifact_definitions', artifact_name)
    artifact_def_file_path = next(iter(find_all_yaml_files_by_stem(artifact_def_file_name)), None)
    if artifact_def_file_path is None:
        raise FileNotFoundError(f"No configuration file found for {artifact_name} with .yaml or .yml extension")
    artifact_def_config = openYaml(artifact_def_file_path)

    credentials_id = artifact_def_config['registry']['credentialsId']
    repository_username = cred_config[credentials_id]['data'].get('username')
    repository_password = cred_config[credentials_id]['data'].get('password')

    if repository_username is None or repository_password is None:
        raise ValueError(f"Username or password for registry '{artifact_def_config['registry']['name']}' is null.")

    repository_url = None

    artifact_is_zip = env_definition['envTemplate'].get('artifactIsZip', False)
    if not artifact_is_zip:
        repository_url = asyncio.run(
            artifact.check_artifact_async(app_def, artifact.FileExtension.JSON, artifact_version))

    group_id = artifact_def_config['groupId']
    artifact_id = artifact_def_config['artifactId']
    if not repository_url:
        repository_url = artifact_def_config['registry']['mavenConfig'].get('repositoryDomainName')

else:
    logger.info("Use old logic")
    registry_config_path = Path(f"{base_dir}/configuration/registry.yml")
    registry_config = openYaml(registry_config_path)
    artifact_info = env_definition['envTemplate']['templateArtifact']['artifact']

    group_id = artifact_info['group_id']
    artifact_id = artifact_info['artifact_id']
    version = artifact_info['version']

    repository_type = env_definition['envTemplate']['templateArtifact']['repository']
    repository_template_type = env_definition['envTemplate']['templateArtifact']['templateRepository']
    registry_name = env_definition['envTemplate']['templateArtifact']['registry']

    template_repository_url = registry_config[registry_name][repository_template_type]
    repository_url = registry_config[registry_name][repository_type]
    creds_id_username = fetch_cred_value(registry_config[registry_name]['username'], cred_config)
    creds_id_password = fetch_cred_value(registry_config[registry_name]['password'], cred_config)

    repository_username = cred_config[creds_id_username[0]]['data'][creds_id_username[1]]
    repository_password = cred_config[creds_id_password[0]]['data'][creds_id_password[1]]
