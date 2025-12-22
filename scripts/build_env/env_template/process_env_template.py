import os
from pathlib import Path

import asyncio

from artifact_searcher.artifact import download_all_async
from artifact_searcher.utils.models import FileExtension, ArtifactInfo
from envgenehelper import crypt, openYaml, find_all_yaml_files_by_stem, fetch_cred_value, get_env_definition_path
from envgenehelper import logger
from artifact_searcher import artifact
from envgenehelper.config_helper import base_dir
from envgenehelper.env_helper import get_environment_name, get_cluster_name
from envgenehelper import get_env_definition


def split_artifact_appver(env_definition: dict):
    artifact_appver = env_definition['envTemplate'].get('artifact', '')
    logger.info(f"Environment template dd appver: {artifact_appver}")
    return artifact_appver.split(':')


def get_artifact_def(artifact_name: str):
    artifact_def_file_name = os.path.join(base_dir, 'configuration', 'artifact_definitions', artifact_name)
    artifact_def_file_path = next(iter(find_all_yaml_files_by_stem(artifact_def_file_name)), None)
    if artifact_def_file_path is None:
        raise FileNotFoundError(f"No configuration file found for {artifact_name} with .yaml or .yml extension")
    return openYaml(artifact_def_file_path)


def fetch_dd_template(artifact_def, artifact_version, cred_config):
    dd_template_url, _ = asyncio.run(artifact.check_artifact_async(artifact_def, FileExtension.JSON, artifact_version))
    if not dd_template_url:
        raise ValueError(
            f"[Application {artifact_def.name}:{artifact_version}]: URL to environment template deployment descriptor "
            f"could not be resolved"
        )
    logger.info(f"Resolved environment template deployment descriptor URL: {dd_template_url}")

    credentials_id = artifact_def['registry']['credentialsId']
    repository_username = cred_config[credentials_id]['data'].get('username')
    repository_password = cred_config[credentials_id]['data'].get('password')

    if repository_username is None or repository_password is None:
        raise ValueError(f"Username or password for registry '{artifact_def['registry']['name']}' is null")
    dd_config = artifact.download_json_content(dd_template_url, (repository_username, repository_password))
    logger.debug(f"environment template deployment descriptor: {dd_config}")
    return dd_config


def fetch_env_template(dd_template, artifact_def, artifact_version) -> ArtifactInfo:
    repository_url = dd_template['configurations'][0]['maven_repository']
    final_template_url = None
    if repository_url:
        artifact_tmp_str = dd_template['configurations'][0]['artifacts'][0]['id']
        # group_id, artifact_id, version = artifact_tmp_str.split(':') if artifact_tmp_str else []
        # TODO make searcher work with artifact_def
        final_template_url = asyncio.run(artifact.check_artifact_async(artifact_def, FileExtension.ZIP, version))
    # TODO cross check this case
    # else:
    #     final_template_url =
    #     group_id = artifact_def['groupId']
    #     artifact_id = artifact_def['artifactId']
    #     version = artifact_version
    #     repository_url =

    artifact_info = ArtifactInfo(app_name=artifact_def['name'], app_version=artifact_version, url=final_template_url)
    asyncio.run(download_all_async([artifact_info]))
    return artifact_info


def process_env_template() -> str:
    cred_config = crypt.decrypt_file(Path(f"{base_dir}/configuration/credentials/credentials.yml"))
    # template = Template(decrypted_creds)
    env_instances_dir = Path(f"{base_dir}/environments/{get_cluster_name()}/{get_environment_name()}")
    env_definition = get_env_definition(env_instances_dir)

    if 'artifact' in env_definition.get('envTemplate', {}):
        logger.info("Use template downloading new logic")
        artifact_name, artifact_version = split_artifact_appver(env_definition)
        artifact_def = get_artifact_def(artifact_name)

        artifact_is_zip = env_definition['envTemplate'].get('artifactIsZip', False)
        if not artifact_is_zip:
            dd_template = fetch_dd_template(artifact_def, artifact_version, cred_config)
            artifact_info = fetch_env_template(dd_template, artifact_def, artifact_version)
    else:
        logger.info("Use template downloading old logic")
        registry_config_path = Path(f"{base_dir}/configuration/registry.yml")
        registry_config = openYaml(registry_config_path)

        artifact_info = env_definition['envTemplate']['templateArtifact']['artifact']
        group_id = artifact_info['group_id']
        artifact_id = artifact_info['artifact_id']
        version = artifact_info['version']
        repository_type = artifact_info['repository']
        repository_template_type = artifact_info['templateRepository']
        registry_name = artifact_info['registry']

        template_repository_url = registry_config[registry_name][repository_template_type]
        repository_url = registry_config[registry_name][repository_type]

        repository_username = fetch_cred_value(registry_config[registry_name]['username'], cred_config)
        repository_password = fetch_cred_value(registry_config[registry_name]['password'], cred_config)

        # TODO download
    return artifact_latest_version
