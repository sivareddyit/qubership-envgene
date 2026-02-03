from os import environ
import shutil

import pytest
from envgenehelper import *

from main import render_environment, cleanup_resulting_dir
from envgenehelper.test_helpers import TestHelpers

# Set to True to update expected test data with newly rendered output
UPDATE_TEST_DATA = False

test_data = [
    # (cluster_name, environment_name, template[, extra_templates_dirs])
    ("cluster-01", "env-01", "composite-prod"),
    ("cluster-01", "env-02", "composite-dev"),
    ("cluster-01", "env-03", "composite-dev"),
    ("cluster-01", "env-04", "simple"),
    ("cluster01", "env01", "test-01"),
    ("cluster01", "env03", "test-template-1"),
    ("cluster01", "env04", "test-template-2"),
    ("bgd-cluster","bgd-env","bgd"),
    ("bgd-cluster", "bgd-ns-artifacts-env", "bgd-ns-artifacts", {"peer": "test_data/test_templates_peer", "origin": "test_data/test_templates_origin"}),
    ("cluster03", "rpo-replacement-mode", "simple"),
]

base_dir = Path(__file__).resolve().parents[4]
g_templates_dirs = {
    'common': str((base_dir / "test_data/test_templates").resolve())
}
g_inventory_dir = str((base_dir / "test_data/test_environments").resolve())
g_output_dir = str((base_dir / "/tmp/test_environments").resolve())
g_base_dir = get_parent_dir_for_dir(g_inventory_dir)
environ['CI_PROJECT_DIR'] = g_base_dir
os.environ['CI_COMMIT_REF_NAME'] = "branch_name"


@pytest.fixture(autouse=True)
def change_test_dir(monkeypatch):
    monkeypatch.chdir(base_dir)


def _update_test_data(source_dir, generated_dir):
    source_path = Path(source_dir)
    generated_path = Path(generated_dir)

    # Directories and files to sync from generated to source
    dirs_to_sync = ["Applications", "Namespaces", "Profiles"]
    files_to_sync = ["cloud.yml", "tenant.yml", "bg_domain.yml", "composite_structure.yml"]

    for dir_name in dirs_to_sync:
        src = generated_path / dir_name
        dst = source_path / dir_name
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        elif dst.exists():
            shutil.rmtree(dst)

    for file_name in files_to_sync:
        src = generated_path / file_name
        dst = source_path / file_name
        if src.exists():
            shutil.copy2(src, dst)
        elif dst.exists():
            dst.unlink()

    logger.info(f"Updated test data in {source_dir}")


@pytest.mark.parametrize("test_entry", test_data)
def test_render_envs(test_entry):
    cluster_name, env_name, version = test_entry[0], test_entry[1], test_entry[2]
    extra_templates_dirs = test_entry[3] if len(test_entry) > 3 else None

    templates_dirs = dict(g_templates_dirs)
    if extra_templates_dirs:
        for k, v in extra_templates_dirs.items():
            templates_dirs[k] = str((base_dir / v).resolve())

    environ['CI_PROJECT_DIR'] = g_base_dir
    environ['FULL_ENV_NAME'] = cluster_name + '/' + env_name
    render_environment(env_name, cluster_name, templates_dirs, g_inventory_dir, g_output_dir, g_base_dir)
    source_dir = f"{g_inventory_dir}/{cluster_name}/{env_name}"
    generated_dir = f"{g_output_dir}/{cluster_name}/{env_name}"

    if UPDATE_TEST_DATA:
        _update_test_data(source_dir, generated_dir)
    else:
        files_to_compare = get_all_files_in_dir(source_dir)
        logger.info(dump_as_yaml_format(files_to_compare))
        TestHelpers.assert_dirs_content(source_dir, generated_dir, True, False)


def setup_test_dir(tmp_path):
    tmp_path.mkdir(exist_ok=True, parents=True)
    dirs = ["Applications", "Namespaces", "Profiles"]
    for d in dirs:
        (tmp_path / d).mkdir(exist_ok=True)
    files = ["cloud.yml", "tenant.yml", "bg_domain.yml", "composite_structure.yml"]
    for f in files:
        (tmp_path / f).write_text("text")
    (tmp_path / "keep.yml").write_text("text")
    (tmp_path / "keep").mkdir(exist_ok=True)
    return tmp_path


def test_cleanup_target_dir_removes_expected_items():
    target_dir = Path(g_output_dir) / "dump-cluster"
    setup_test_dir(target_dir)
    cleanup_resulting_dir(Path(target_dir))
    assert not (target_dir / "Applications").exists()
    assert not (target_dir / "Namespaces").exists()
    assert not (target_dir / "Profiles").exists()
    assert not (target_dir / "cloud.yml").exists()
    assert not (target_dir / "tenant.yml").exists()
    assert not (target_dir / "bg_domain.yml").exists()
    assert not (target_dir / "composite_structure.yml").exists()

    assert (target_dir / "keep.yml").exists()
    assert (target_dir / "keep").exists()

    delete_dir(target_dir)
