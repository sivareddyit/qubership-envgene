import os
import re
from enum import StrEnum
from pathlib import Path

from deepmerge import always_merger
from envgenehelper import logger, openYaml, readYaml, writeYamlToFile, openFileAsString, copy_path, dumpYamlToStr, \
    create_yaml_processor
from jinja2 import Environment, FileSystemLoader, Template, ChainableUndefined, TemplateError, BaseLoader

from jinja_filters import JinjaFilters
from replace_ansible_stuff import replace_ansible_stuff

yml = create_yaml_processor()


class ContextKeys(StrEnum):
    env = "env"
    render_dir = "render_dir"
    env_vars = "env_vars"
    cloud_passport = "cloud_passport"
    templates_dir = "templates_dir"
    output_dir = "output_dir"
    cluster_name = "cluster_name"
    env_definition = "env_definition"
    current_env = "current_env"
    current_env_dir = "current_env_dir"
    current_env_template = "current_env_template"
    tenant = "tenant"
    env_template = "env_template"
    env_instances_dir = "env_instances_dir"
    cloud_passport_file_path = "cloud_passport_file_path"
    sd_config = "sd_config"
    sd_file_path = "sd_file_path"
    regdefs = "regdefs"
    appdefs = "appdefs"
    regdef_templates = "regdef_templates"
    appdef_templates = "appdef_templates"


AppDefs = "AppDefs"
RegDefs = "RegDefs"


def create_jinja_env(templates_dir: str = "") -> Environment:
    loader = FileSystemLoader(templates_dir) if templates_dir else BaseLoader()
    if templates_dir:
        env = Environment(
            loader=loader,
            undefined=ChainableUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
    else:
        env = Environment(
            undefined=ChainableUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
    JinjaFilters.register(env)
    return env


def get_inventory(context: dict) -> dict:
    inventory_path = Path(context[ContextKeys.env_instances_dir]) / "Inventory" / "env_definition.yml"
    env_definition = openYaml(filePath=inventory_path, safe_load=True)
    logger.info(f"env_definition = {env_definition}")
    return env_definition


def get_cloud_passport(context: dict) -> dict | None:
    cloud_passport_file_path = context.get(ContextKeys.cloud_passport_file_path, "").strip()
    if cloud_passport_file_path:
        cloud_passport_path = Path(cloud_passport_file_path)
        cloud_passport = openYaml(filePath=cloud_passport_path, safe_load=True)
        logger.info(f"cloud_passport = {cloud_passport}")
        return cloud_passport


def generate_config(context: dict) -> dict:
    templates_dir = Path(__file__).parent / "templates"
    template = create_jinja_env(str(templates_dir)).get_template("env_config.yml.j2")
    config = readYaml(text=template.render(context), safe_load=True)
    logger.info(f"config = {config}")
    return config


def load_env_template(context: dict):
    env_template_path_stem = f'{context["templates_dir"]}/env_templates/{context[ContextKeys.current_env][ContextKeys.env_template]}'
    env_template_path = next(iter(find_all_yaml_files_by_stem(env_template_path_stem)), None)
    if not env_template_path:
        raise ValueError(f'Template descriptor was not found in {env_template_path_stem}')

    env_template = openYaml(filePath=env_template_path, safe_load=True)
    logger.info(f"env_template = {env_template}")
    return env_template


def find_all_yaml_files_by_stem(path: str):
    file_paths = []
    for ext in ["yaml", "yml"]:
        file_path = Path(f"{path}.{ext}")
        if file_path.exists():
            file_paths.append(file_path)
    return file_paths


def validate_applications(sd_config: dict):
    applications = sd_config.get("applications", [])

    for app in applications:
        version = app.get("version")
        deploy_postfix = app.get("deployPostfix")

        if "version" not in app:
            raise ValueError(f"Missing 'version' in application: {app}")
        if "deployPostfix" not in app:
            raise ValueError(f"Missing 'deployPostfix' in application: {app}")
        if not isinstance(version, str):
            raise ValueError(f"'version' must be string in application: {app}")
        if not isinstance(deploy_postfix, str):
            raise ValueError(f"'deployPostfix' must be string in application: {app}")

        logger.info(f"Valid application: {app}")


def generate_ns_postfix(ns, ns_template_path) -> str:
    deploy_postfix = ns.get("deploy_postfix")
    if deploy_postfix:
        ns_template_name = deploy_postfix
    else:
        # get base name(deploy postfix) without extensions
        ns_template_name = Path(ns_template_path).name.replace(".yml.j2", "").replace(".yaml.j2", "")
    return ns_template_name


def generate_solution_structure(context: dict):
    sd_path_stem = f'{context[ContextKeys.current_env_dir]}/Inventory/solution-descriptor/sd'
    sd_path = next(iter(find_all_yaml_files_by_stem(sd_path_stem)), None)
    if sd_path:
        context[ContextKeys.sd_file_path] = str(sd_path)
        sd_config = openYaml(filePath=sd_path, safe_load=True)
        context[ContextKeys.sd_config] = sd_config
        if "applications" not in sd_config:
            raise ValueError("Missing 'applications' key in root")
        validate_applications(sd_config)

        namespaces = context[ContextKeys.current_env_template].get("namespaces", [])
        postfix_template_map = {}
        for ns in namespaces:
            namespace_template_path = Template(ns["template_path"]).render(context)
            postfix = generate_ns_postfix(ns, namespace_template_path)
            postfix_template_map[postfix] = namespace_template_path

        solution_structure = {}
        for app in sd_config["applications"]:
            app_version = app["version"]
            app_name, version = app_version.split(":", 1)
            postfix = app["deployPostfix"]

            ns_template_path = postfix_template_map.get(postfix)
            ns_name = None
            if ns_template_path:
                rendered_ns = render_from_file_to_obj(ns_template_path, context)
                ns_name = rendered_ns.get("name")

            small_dict = {
                app_name: {
                    postfix: {
                        "version": version,
                        "namespace": ns_name
                    }
                }
            }
            always_merger.merge(solution_structure, small_dict)

        logger.info(f"Rendered solution_structure: {solution_structure}")
        always_merger.merge(context[ContextKeys.current_env], {"solution_structure": solution_structure})


def render_from_file_to_file(src_template_path: str, target_file_path: str, context):
    template = openFileAsString(src_template_path)
    template = replace_ansible_stuff(template_str=template, template_path=src_template_path)
    rendered = create_jinja_env().from_string(template).render(context)
    writeYamlToFile(target_file_path, readYaml(rendered))


def render_from_file_to_obj(src_template_path, context) -> dict:
    template = openFileAsString(src_template_path)
    template = replace_ansible_stuff(template_str=template, template_path=src_template_path)
    rendered = create_jinja_env().from_string(template).render(context)
    return readYaml(rendered)


def render_from_obj_to_file(template, target_file_path, context):
    template = replace_ansible_stuff(template_str=dumpYamlToStr(template))
    rendered = create_jinja_env().from_string(template).render(context)
    writeYamlToFile(target_file_path, readYaml(rendered))


def generate_tenant_file(context: dict):
    logger.info(f"Generate Tenant yaml for {context[ContextKeys.tenant]}")
    tenant_file = f'{context[ContextKeys.current_env_dir]}/tenant.yml'
    tenant_tmpl_path = context[ContextKeys.current_env_template][ContextKeys.tenant]
    render_from_file_to_file(Template(tenant_tmpl_path).render(context), tenant_file, context)


def generate_override_template(context, template_override, template_path: Path, name):
    if template_override:
        logger.info(f"Generate override {template_path.stem} yaml for {name}")
        render_from_obj_to_file(template_override, template_path, context)


def generate_cloud_file(context: dict):
    cloud = calculate_cloud_name(context)
    cloud_template = context[ContextKeys.current_env_template]["cloud"]
    current_env_dir = context[ContextKeys.current_env_dir]
    cloud_file = f'{current_env_dir}/cloud.yml'
    is_template_override = isinstance(cloud_template, dict)
    if is_template_override:
        logger.info(f"Generate Cloud yaml for cloud {cloud} using cloud.template_path value")
        cloud_tmpl_path = cloud_template["template_path"]
        render_from_file_to_file(Template(cloud_tmpl_path).render(context), cloud_file, context)

        template_override = cloud_template.get("template_override")
        generate_override_template(context, template_override, Path(f'{current_env_dir}/cloud.yml_override'), cloud)
    else:
        logger.info(f"Generate Cloud yaml for cloud {cloud}")
        render_from_file_to_file(Template(cloud_template).render(context), cloud_file, context)


def generate_namespace_file(context: dict):
    namespaces = context[ContextKeys.current_env_template]["namespaces"]
    for ns in namespaces:
        ns_template_path = Template(ns["template_path"]).render(context)
        ns_template_name = generate_ns_postfix(ns, ns_template_path)
        logger.info(f"Generate Namespace yaml for {ns_template_name}")
        current_env_dir = context[ContextKeys.current_env_dir]
        ns_dir = f'{current_env_dir}/Namespaces/{ns_template_name}'
        namespace_file = f'{ns_dir}/namespace.yml'
        render_from_file_to_file(ns_template_path, namespace_file, context)

        generate_override_template(context, ns.get("template_override"), Path(f'{ns_dir}/namespace.yml_override'),
                                   ns_template_name)


def calculate_cloud_name(context):
    inv = context[ContextKeys.env_definition]["inventory"]
    cluster_name = context[ContextKeys.cluster_name]
    candidates = [
        inv.get("cloudName"),
        inv.get("passportCloudName", "").replace("-", "_") if inv.get("passportCloudName") else "",
        inv.get("cloudPassport", "").replace("-", "_") if inv.get("cloudPassport") else "",
        inv.get("environmentName", "").replace("-", "_"),
        f"{cluster_name}_{inv.get('environmentName', '')}".replace("-", "_")
        if cluster_name and inv.get("environmentName") else ""
    ]

    return next((c for c in candidates if c), "")


def get_template_name(template_path: Path) -> str:
    return (
        template_path.name
        .replace(".yml.j2", "")
        .replace(".yaml.j2", "")
    )


def generate_composite_structure(composite_structure, context):
    logger.info(f"Generate Composite Structure yaml for {composite_structure}")
    current_env_dir = context[ContextKeys.current_env_dir]
    cs_file = Path(current_env_dir) / "composite_structure.yml"
    cs_file.parent.mkdir(parents=True, exist_ok=True)
    render_from_file_to_file(Template(composite_structure).render(context), str(cs_file), context)


def generate_paramset_templates(context):
    render_dir = Path(context["render_parameters_dir"]).resolve()
    patterns = ["*.yml.j2", "*.yaml.j2"]

    paramset_templates = []
    for pattern in patterns:
        paramset_templates.extend(render_dir.rglob(pattern))
    logger.info(f"Total parameter set templates list found: {paramset_templates}")

    for template_path in paramset_templates:
        template_name = get_template_name(template_path)
        target_path = Path(str(template_path).replace(".yml.j2", ".yml").replace(".yaml.j2", ".yml"))

        try:
            logger.info(f"Try to render paramset {template_name}")
            render_from_file_to_file(Template(str(template_path)).render(context), target_path, context)
            logger.info(f"Successfully generated paramset: {template_name}")
            if template_path.exists():
                template_path.unlink()
        except TemplateError as e:
            logger.warning(f"Skipped paramset {template_name}. Error details: {e}")
            if target_path.exists():
                target_path.unlink()


def find_templates(templates_dir: str, def_type: str) -> list[Path]:
    search_path = Path(templates_dir) / def_type
    if not search_path.exists():
        logger.info(f"Directory with templates for {def_type} not found: {search_path}")
        return []

    patterns = ["*.yaml.j2", "*.yml.j2", "*.j2", "*.yaml", "*.yml"]
    templates = []

    for pattern in patterns:
        for f in search_path.rglob(pattern):
            if f.is_file():
                templates.append(f)

    logger.info(f"{def_type.capitalize()} Found: {len(templates)}")
    return templates


def ensure_directory(path: Path, mode: int = 0o755):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {path}")
    else:
        logger.info(f"Directory already exists: {path}")
    path.chmod(mode)
    logger.info(f"Set permissions {oct(mode)} for {path}")


def render_app_defs(context):
    for def_tmpl_path in context.get("appdef_templates"):
        app_def_str = openFileAsString(def_tmpl_path)
        matches = re.findall(
            r'^\s*(name|artifactId|groupId):\s*"([^"]+)"',
            app_def_str,
            flags=re.MULTILINE,
        )
        appdef_meta = dict(matches)
        ensure_valid_fields(appdef_meta, ["artifactId", "groupId", "name"])
        group_id = appdef_meta["groupId"]
        artifact_id = appdef_meta["artifactId"]
        context.update({
            "app_lookup_key": f"{group_id}:{artifact_id}",
            "groupId": group_id,
            "artifactId": artifact_id,
        })
        app_def_trg_path = f"{context[ContextKeys.current_env_dir]}/{AppDefs}/{appdef_meta.get("name")}.yml"
        render_from_file_to_file(def_tmpl_path, app_def_trg_path, context)


def render_reg_defs(context):
    for def_tmpl_path in context.get("regdef_templates"):
        reg_def_str = openFileAsString(def_tmpl_path)
        matches = re.findall(
            r'^\s*(name):\s*"([^"]+)"',
            reg_def_str,
            flags=re.MULTILINE,
        )
        regdef_meta = dict(matches)
        ensure_valid_fields(regdef_meta, ["name"])
        reg_def_trg_path = f"{context[ContextKeys.current_env_dir]}/{RegDefs}/{regdef_meta['name']}.yml"
        render_from_file_to_file(def_tmpl_path, reg_def_trg_path, context)


def ensure_required_keys(context, required: list[str]):
    missing = [var for var in required if var not in context]
    if missing:
        raise ValueError(
            f"Required variables: {', '.join(required)}. "
            f"Not found: {', '.join(missing)}"
        )
    logger.info(f"All required {required} variables are defined")


def ensure_valid_fields(context, fields: list[str]):
    invalid = []
    for field in fields:
        value = context.get(field)
        if not value:
            invalid.append(f"{field}={value!r}")

    if invalid:
        raise ValueError(
            f"Invalid or empty fields found: {', '.join(invalid)}. "
            f"Required fields: {', '.join(fields)}"
        )
    logger.info("All required fields are present and non-empty: %s", ", ".join(fields))


def set_appreg_def_overrides(context):
    output_dir = Path(context[ContextKeys.output_dir])
    cluster_name = context[ContextKeys.cluster_name]
    config_file_name = Path("configuration") / "appregdef_config"
    config_file_name_yaml = f"{config_file_name}.yaml"
    config_file_name_yml = f"{config_file_name}.yml"

    potential_config_files = [
        output_dir / cluster_name / config_file_name_yaml,
        output_dir / cluster_name / config_file_name_yml,
        output_dir.parent / config_file_name_yaml,
        output_dir.parent / config_file_name_yml,
    ]
    appregdef_config_paths = [f for f in potential_config_files if f.exists()]
    if appregdef_config_paths:
        appregdef_config = {}
        appregdef_config_path = appregdef_config_paths[0]
        try:
            appregdef_config = openYaml(appregdef_config_path)
            logger.info(f"Overrides applications/registries definitions config found at: {appregdef_config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config at: {appregdef_config_path}. Error: {e}")

        context[ContextKeys.appdefs]["overrides"] = appregdef_config.get(ContextKeys.appdefs, {}).get("overrides", {})
        context[ContextKeys.regdefs]["overrides"] = appregdef_config.get(ContextKeys.regdefs, {}).get("overrides", {})


def process_app_reg_defs(context):
    current_env_dir = context[ContextKeys.current_env_dir]
    templates_dir = context[ContextKeys.templates_dir]
    appdef_templates = find_templates(templates_dir, ContextKeys.appdefs)
    regdef_templates = find_templates(templates_dir, ContextKeys.regdefs)
    context[ContextKeys.appdef_templates] = appdef_templates
    context[ContextKeys.regdef_templates] = regdef_templates

    ensure_directory(Path(current_env_dir).joinpath(AppDefs))
    ensure_directory(Path(current_env_dir).joinpath(RegDefs))
    set_appreg_def_overrides(context)
    render_app_defs(context)
    render_reg_defs(context)


def generate_config_env(envvars: dict):
    context = {}
    env_vars = dict(os.environ)
    context[ContextKeys.env_vars] = {
        "CI_COMMIT_TAG": env_vars.get("CI_COMMIT_TAG"),
        "CI_COMMIT_REF_NAME": env_vars.get("CI_COMMIT_REF_NAME")
    }
    context.update(envvars)
    context[ContextKeys.env_definition] = get_inventory(context)

    cloud_passport = get_cloud_passport(context)
    if cloud_passport:
        context[ContextKeys.cloud_passport] = cloud_passport

    context["config"] = generate_config(context)
    current_env = context["config"]["environment"]
    context[ContextKeys.current_env] = current_env
    context["cloud"] = calculate_cloud_name(context)
    context[ContextKeys.tenant] = current_env.get("tenant", '')
    context["deployer"] = current_env.get('deployer', '')
    logger.info("current_env = %s", current_env)

    context["ND_CMDB_CONFIG_REF"] = os.environ.get('CI_COMMIT_SHORT_SHA', 'No SHA')
    context["ND_CMDB_CONFIG_REF_NAME"] = os.environ.get('CI_COMMIT_REF_NAME', 'No Ref Name')
    context["ND_CMDB_CONFIG_TAG"] = os.environ.get('CI_COMMIT_TAG', 'No Ref tag')
    context["ND_CDMB_REPOSITORY_URL"] = os.environ.get('CI_REPOSITORY_URL', 'No Ref URL')
    env_template = context.get(ContextKeys.env_template)
    if env_template:
        context["ND_CMDB_ENV_TEMPLATE"] = env_template
    else:
        context["ND_CMDB_ENV_TEMPLATE"] = context[ContextKeys.current_env][ContextKeys.env_template]

    current_env_dir = f'{context[ContextKeys.render_dir]}/{context[ContextKeys.env]}'
    context[ContextKeys.current_env_dir] = current_env_dir
    context[ContextKeys.current_env_template] = load_env_template(context)

    generate_solution_structure(context)
    generate_tenant_file(context)
    generate_cloud_file(context)
    generate_namespace_file(context)

    current_env_template = context[ContextKeys.current_env_template]
    composite_structure = current_env_template.get("composite_structure")
    if composite_structure:
        generate_composite_structure(composite_structure, context)

    env_specific_schema = current_env_template.get("envSpecificSchema")
    if env_specific_schema:
        copy_path(source_path=env_specific_schema, target_dir=current_env_dir)
    generate_paramset_templates(context)

    ensure_required_keys(context,
                         required=[ContextKeys.templates_dir, ContextKeys.env_instances_dir, ContextKeys.cluster_name,
                                   ContextKeys.current_env_dir])
    process_app_reg_defs(context)
