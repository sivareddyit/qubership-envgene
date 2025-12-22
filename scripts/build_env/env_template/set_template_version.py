from pathlib import Path

from envgenehelper import beautifyYaml, writeYamlToFile, logger, getenv_with_error
from envgenehelper import get_env_definition
from envgenehelper.config_helper import base_dir
from envgenehelper.env_helper import get_cluster_name, get_environment_name


def update_version(env_definition_path, version_to_add):
    logger.info(f"Started version update to {version_to_add} in {env_definition_path}.")
    data = get_env_definition(env_instances_dir)

    if ":" in version_to_add:
        if 'envTemplate' in data:
            if 'templateArtifact' in data['envTemplate']:
                del data['envTemplate']['templateArtifact']
            data['envTemplate']['artifact'] = version_to_add
        else:
            logger.error(f"Bad env_definition structure in file {env_definition_path}.")
            raise ReferenceError(f"Can't update version in {env_definition_path}. See logs above.")
    else:
        if 'envTemplate' in data and 'templateArtifact' in data['envTemplate'] and 'artifact' in data['envTemplate'][
            'templateArtifact']:
            oldVersion = "undefined"
            if 'version' in data['envTemplate']['templateArtifact']['artifact']:
                oldVersion = data['envTemplate']['templateArtifact']['artifact']['version']
            data['envTemplate']['templateArtifact']['artifact']['version'] = version_to_add
            logger.info(f"Succesfully updated version from {oldVersion} to {version_to_add} in {env_definition_path}")
        else:
            logger.error(f"Bad env_definition structure in file {env_definition_path}.")
            raise ReferenceError(f"Can't update version in {env_definition_path}. See logs above.")
    writeYamlToFile(env_definition_path, data)
    beautifyYaml(env_definition_path)


if __name__ == "__main__":
    env_instances_dir = Path(f"{base_dir}/environments/{get_cluster_name()}/{get_environment_name()}")
    version_to_add = getenv_with_error("ENV_TEMPLATE_VERSION")
    update_version(env_instances_dir, version_to_add)
