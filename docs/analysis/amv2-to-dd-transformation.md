# AMv2 to DD Transformation

- [AMv2 to DD Transformation](#amv2-to-dd-transformation)
  - [Principles](#principles)
  - [AMv2 Assumptions](#amv2-assumptions)
  - [AMv2 to DD Transformation Algorithm](#amv2-to-dd-transformation-algorithm)
    - [Inputs](#inputs)
    - [Output](#output)
    - [Algorithm Steps](#algorithm-steps)
      - [Step 1: Extract Services from Docker Images](#step-1-extract-services-from-docker-images)
      - [Step 3: Extract App-Chart](#step-3-extract-app-chart)
      - [Step 4: Build DD Structure](#step-4-build-dd-structure)

This document describes the transformation rules from [Application Manifest v2 (AMv2)](/docs/analysis/application-manifest-v2-specification.md) to Deployment Descriptor (DD).

## Principles

1. All `nc:dd:<attribute-name>` properties are restored to their original DD fields
2. `application/vnd.docker.image` components are transformed into `DD.services[]` entries
   1. Standalone Docker images (`image_type = "image"`) are transformed into `DD.services[]` entries with `image_type = "image"`
   2. Docker images with associated Helm charts (`image_type = "service"`) are transformed into `DD.services[]` entries with `image_type = "service"`
3. `application/vnd.nc.helm.chart` components are transformed into:
   - `DD.charts[]` entry if property `nc:dd:type = "app-chart"` exists
4. Only components with `nc:dd:*` properties are processed (these are components that originated from DD)

## AMv2 Assumptions

1. AMv2 contains only one `application/vnd.nc.standalone-runnable` component
2. All `application/vnd.docker.image` components have `nc:dd:*` properties if they originated from DD
3. All `application/vnd.nc.helm.chart` components have `nc:dd:*` properties if they originated from DD
4. App-chart (umbrella chart) is identified by property `nc:dd:type = "app-chart"`

## AMv2 to DD Transformation Algorithm

### Inputs

1. AMv2 JSON document conforming to [JSON schema](/schemas/application-manifest-v2.schema.json)

### Output

1. DD JSON document

### Algorithm Steps

#### Step 1: Extract Services from Docker Images

For each `application/vnd.docker.image` component in AMv2 root `components` array:

1. Check if component has `nc:dd:*` properties
2. If yes:
   - Extract all `nc:dd:<attribute-name>` properties and restore to `DD.services[]` entry fields
3. If no:
   - ignore/skip the component

#### Step 3: Extract App-Chart

1. Find `application/vnd.nc.helm.chart` component with property `nc:dd:type = "app-chart"`
2. If found:
   - Extract all `nc:dd:<attribute-name>` properties and restore to `DD.charts[]` entry fields (according to Principle 1)
3. If not found:
   - `DD.charts[]` = empty array `[]`

#### Step 4: Build DD Structure

1. Create root DD object:
   - Set `services` = array of all `DD.services[]` entries from Step 1
   - Set `charts` = array from Step 3
   - Initialize other DD sections as empty objcts:
     - `metadata` = `{}`
     - `include` = `[]`
     - `infrastructures` = `[]`
     - `configurations` = `[]`
     - `frontends` = `[]`
     - `smartplug` = `[]`
     - `jobs` = `[]`
     - `libraries` = `[]`
     - `complexes` = `[]`
     - `additionalArtifacts` = `{}`
     - `descriptors` = `[]`
