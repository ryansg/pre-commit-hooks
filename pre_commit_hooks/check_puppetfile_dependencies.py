#!/usr/bin/env python3

import re
import requests
import argparse
import semver
import multiprocessing
import subprocess
import sys
import os

def parse_r10k_puppetfile(puppetfile_path):
    """Parses Puppetfile and extracts module, git URL, and tag."""
    module_data = {}
    try:
        with open(puppetfile_path, 'r') as f:
            for line in f:
                line = line.strip()
                match = re.search(r"mod\s+'([^']+)',\s+:git\s*=>\s*'([^']+)',\s*:tag\s*=>\s*'([^']+)'", line)
                if match:
                    module_name = match.group(1)
                    git_url = match.group(2)
                    tag = re.sub(r'^v', '', match.group(3), flags=re.IGNORECASE)
                    module_data[module_name] = {'tag': tag, 'git_url': git_url}
    except FileNotFoundError:
        print(f"Error: Puppetfile not found at {puppetfile_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return module_data

def get_forge_data(module_name):
    """Queries the Puppet Forge API for module data, renaming 'puppet-resource_tree'."""
    try:
        if module_name == 'puppet-resource_tree':
            module_name = 'jake-resource_tree'
        api_url = f"https://forgeapi.puppet.com/v3/modules/{module_name}"
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {module_name}: {e}")
        return None

def fetch_module_data(module_info):
    """Fetches module data from the Forge API."""
    module_name, data = module_info
    if not data['git_url'].startswith("https://github.com/"):
        return module_name, None  # Skip if not GitHub URL
    forge_data = get_forge_data(module_name)
    if forge_data:
        current_release = forge_data.get('current_release')
        if current_release:
            current_version = current_release.get('version')
            metadata = current_release.get('metadata', {})
            dependencies = metadata.get('dependencies', [])
            return module_name, {
                'tag': data['tag'],
                'current_version': current_version,
                'dependencies': dependencies
            }
        else:
            print(f"No current release found for {module_name}")
            return module_name, None
    else:
        print(f"Skipping {module_name} due to fetch error.")
        return module_name, None

def get_current_release_and_metadata(module_data):
    """Gets current release version and metadata from Forge data using multiprocessing."""
    results = {}
    with multiprocessing.Pool() as pool:
        module_infos = list(module_data.items())
        module_results = pool.map(fetch_module_data, module_infos)
        for module_name, module_result in module_results:
            if module_result:
                results[module_name] = module_result
    return results

def compare_modules(puppetfile_modules, forge_modules):
    """Compares modules in Puppetfile and Forge, showing differences."""
    differences = {}
    for module_name, forge_info in forge_modules.items():
        puppet_tag = puppetfile_modules[module_name]['tag']
        forge_version = forge_info['current_version']

        if puppet_tag != forge_version:
            differences[module_name] = {
                'puppet_tag': puppet_tag,
                'forge_version': forge_version,
                'forge_dependencies': forge_info['dependencies']
            }
        else:
            forge_deps = {dep['name'].replace('/', '-'): dep['version_requirement'] for dep in forge_info['dependencies']}
            differences[module_name] = {
                'puppet_tag': puppet_tag,
                'forge_version': forge_version,
                'forge_dependencies': forge_info['dependencies']
            }
    return differences

def compare_versions(puppet_dep_version, dep_version_requirement):
    """Compares a Puppetfile dependency version with a Forge dependency version requirement."""
    requirements = re.findall(r'([<>=]+)\s*([\d.]+)', dep_version_requirement)
    if not requirements:
        try:
            return semver.match(puppet_dep_version, dep_version_requirement)
        except ValueError:
            return False

    for operator, version in requirements:
        try:
            if operator == '>=':
                if not semver.compare(puppet_dep_version, version) >= 0:
                    return False
            elif operator == '>':
                if not semver.compare(puppet_dep_version, version) > 0:
                    return False
            elif operator == '<=':
                if not semver.compare(puppet_dep_version, version) <= 0:
                    return False
            elif operator == '<':
                if not semver.compare(puppet_dep_version, version) < 0:
                    return False
            elif operator == '=':
                if not semver.compare(puppet_dep_version, version) == 0:
                    return False
        except ValueError:
            return False
    return True

def print_differences(module_differences, puppetfile_modules):
    """Prints module differences with color-coded status."""
    has_errors = False
    for module, diff in module_differences.items():
        puppet_tag = diff['puppet_tag']
        forge_version = diff['forge_version']
        outdated_version = "[Outdated]" if puppet_tag != forge_version else ""
        orange_outdated = f"\033[38;5;208m{outdated_version}\033[0m" if outdated_version else ""

        forge_deps = diff['forge_dependencies']
        puppet_deps = {k: v['tag'] for k, v in puppetfile_modules.items()}

        has_outdated_or_not_found = False
        dependency_lines = []

        for dep in forge_deps:
            dep_name = dep['name'].replace('/', '-')
            dep_version = dep['version_requirement']

            if dep_name not in puppet_deps:
                not_found = "[Not Found]"
                red_not_found = f"\033[31m{not_found}\033[0m"
                dependency_lines.append(f"    - {dep_name} ({dep_version}) {red_not_found} {orange_outdated if puppet_tag != forge_version else ''}")
                has_outdated_or_not_found = True
                has_errors=True
            else:
                puppet_dep_version = puppet_deps.get(dep_name)
                if not compare_versions(puppet_dep_version, dep_version):
                    invalid_version = f"[Invalid - Provided:{puppet_dep_version}]"
                    orange_invalid = f"\033[38;5;208m{invalid_version}\033[0m"
                    dependency_lines.append(f"    - {dep_name} ({dep_version}) {orange_invalid}")
                    has_outdated_or_not_found = True
                    has_errors=True
                else:
                    dependency_lines.append(f"    - {dep_name} ({dep_version})")

        if has_outdated_or_not_found or outdated_version :
            print(f"Module: {module}")
            print(f"  Puppetfile Tag: {puppet_tag}")
            print(f"  Forge Version: {forge_version} {orange_outdated}")
            print("  Forge Dependencies:")
            for line in dependency_lines:
                print(line)
            print("-" * 20)
            has_errors = True
    return has_errors

if __name__ == '__main__':
    result = subprocess.run(['git', 'diff', '--name-only', '--cached', 'Puppetfile'], capture_output=True, text=True)
    changed_files = result.stdout.splitlines()

    if 'Puppetfile' in changed_files:
        puppetfile_path = 'Puppetfile'
        puppetfile_modules = parse_r10k_puppetfile(puppetfile_path)
        forge_modules = get_current_release_and_metadata(puppetfile_modules)
        module_differences = compare_modules(puppetfile_modules, forge_modules)

        has_errors = print_differences(module_differences, puppetfile_modules)

        if has_errors:
            print("Puppetfile has dependency errors. Please correct them.")
            sys.exit(1)
        else:
            print("Puppetfile dependencies are valid.")
            sys.exit(0)
    else:
        print("No changes to Puppetfile, skipping dependency check.")
        sys.exit(0)
