
# Ansible replacement

- [Ansible replacement](#ansible-replacement)
  - [List of replacements](#list-of-replacements)
    - [1. `ansible.builtin.to_nice_yaml`](#1-ansiblebuiltinto_nice_yaml)
    - [2. `lookup('ansible.builtin.env', '<...>')`](#2-lookupansiblebuiltinenv-)
    - [3. `default()`](#3-default)
    - [4. `is defined`](#4-is-defined)
  - [Custom Jinja extensions](#custom-jinja-extensions)

Starting from version [TBD](TBD), Ansible is no longer used to render Environment templates (to generate Environment Instances). Now, only Jinja and Python are used for this purpose.

Processing Jinja templates works differently compared to previous setups that used Ansible.

> [!WARNING]
> Beginning November 2025, you must not use any Ansible-specific expressions or syntax in new or updated EnvGene templates.

To create templates, use only:

- [Native Jinja](https://jinja.palletsprojects.com/en/stable/)
- [EnvGene macros](/docs/template-macros.md)

To maintain backward compatibility and allow existing templates to function without Ansible, we have implemented automatic replacements for [certain Ansible functions](#list-of-replacements).

## List of replacements

Replacements are applied during the `env_build` job, right before the Environment template is rendered. Only the described cases are covered.

Any other Ansible-specific syntax not listed here is **not** replaced automatically.

The order of replacements matters and replacements are applied from top to bottom.

### 1. `ansible.builtin.to_nice_yaml`

Reason: Ansible's `ansible.builtin.to_nice_yaml` filter is not available in pure Jinja2.

Replace: `| ansible.builtin.to_nice_yaml(<...>)` → `| to_nice_yaml(<...>)`

Example:

```jinja
{{ data | ansible.builtin.to_nice_yaml(indent=2) }}
```

becomes

```jinja
{{ data | to_nice_yaml(indent=2) }}
```

### 2. `lookup('ansible.builtin.env', '<...>')`

Reason: Ansible's `lookup` plugin system is not available in pure Jinja2.

Replace: `lookup('ansible.builtin.env', '<...>')` → `env_vars.<...>`

Example:

```jinja
{{ lookup('ansible.builtin.env', 'HOME') }}
```

becomes

```jinja
{{ env_vars.HOME }}
```

>[!NOTE] Only lookups exactly like `'ansible.builtin.env'` with single quotes are supported.

### 3. `default()`

Reason: In Ansible, `default` filter treats empty strings, empty lists, and `None` as "false" and applies the default value. In pure Jinja2, `default` only applies to `undefined` variables. Adding `true` as the second argument makes Jinja2 behave like Ansible by treating empty values as falsy.

Replace: `| default('<...>')` → `| default('<...>', true)`

Example:

```jinja
{{ value | default('offsite') }}
```

becomes

```jinja
{{ value | default('offsite', true) }}
```

### 4. `is defined`

Replace: `{% <...> is defined %}` → `{% defined_path('<...>') %}`

Reason: Plain Jinja evaluates chained access left-to-right and may raise errors or yield unexpected results when intermediate objects are missing or `None`.

Example:

```jinja
{% if current_env.cloud_passport.cloud.CLOUD_PUBLIC_HOST is defined %}
  {{ current_env.cloud_passport.cloud.CLOUD_PUBLIC_HOST }}
{% endif %}
```

becomes

```jinja
{% if defined_path('current_env.cloud_passport.cloud.CLOUD_PUBLIC_HOST') %}
  {{ current_env.cloud_passport.cloud.CLOUD_PUBLIC_HOST }}
{% endif %}
```

## Custom Jinja extensions

- `urlsplit_filter` - Custom Jinja filter, a wrapper around Python's `urllib.parse.urlsplit`.

- `to_nice_yaml` - Custom Jinja filter that serializes a Python object into a "pretty" YAML string.

- `defined_path` - Custom Jinja test for safe checking of existence of an arbitrary nested path of any depth.
