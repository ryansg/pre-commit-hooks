#!/usr/bin/env python3
import re
import requests
import argparse
import semver
import multiprocessing
import subprocess
import sys
import os

def get_forge_release_data(release_slug):
    """Queries the Puppet Forge API for release data using release slug."""
    try:
        api_url = f"https://forgeapi.puppet.com/v3/releases/{release_slug}"
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {release_slug}: {e}")
        return None

def get_forge_module_data(module_name):
    """Queries the Puppet Forge API for module data."""
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
    """Fetches module data from the Forge API using release slug and verifies against module endpoint."""
    module_name, data = module_info
    if not data['git_url'].startswith("https://github.com/"):
        return module_name, None
    release_slug = f"{module_name}-{data['tag']}"
    if module_name == 'puppet-resource_tree':
        release_slug = f"jake-resource_tree-{data['tag']}"
    forge_release_data = get_forge_release_data(release_slug)
    forge_module_data = get_forge_module_data(module_name)
    if forge_release_data and forge_module_data:
        current_version = forge_release_data.get('version')
        metadata = forge_release_data.get('metadata', {})
        dependencies = metadata.get('dependencies', [])
        module_endpoint_version = forge_module_data.get('current_release', {}).get('version')
        return module_name, {
            'tag': data['tag'],
            'current_version': current_version,
            'dependencies': dependencies,
            'module_endpoint_version': module_endpoint_version
        }
    else:
        print(f"Skipping {module_name} due to fetch error.")
        return module_name, None

def main():
    parser = argparse.ArgumentParser(description="Check Puppetfile dependencies against Puppet Forge.")
    parser.add_argument("puppetfile_path", nargs="?", default="Puppetfile", help="Path to the Puppetfile.") #Add this line
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument("-a", "--print-all", action="store_true", help="Print all modules and dependencies.")
    args = parser.parse_args()

    def parse_r10k_puppetfile(puppetfile_path):
        """Parses Puppetfile and extracts module, git URL, and tag."""
        module_data = {}
        invalid_tags = []
        try:
            with open(puppetfile_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    match = re.search(r"mod\s+'([^']+)',\s+:git\s*=>\s*'([^']+)',\s*:tag\s*=>\s*'([^']+)'", line)
                    if match:
                        module_name = match.group(1)
                        git_url = match.group(2)
                        tag = re.sub(r'^v', '', match.group(3), flags=re.IGNORECASE)
                        try:
                            semver.VersionInfo.parse(tag)
                            module_data[module_name] = {'tag': tag, 'git_url': git_url}
                        except ValueError:
                            invalid_tags.append((module_name, tag))
        except FileNotFoundError:
            print(f"Error: Puppetfile not found at {puppetfile_path}")
        except Exception as e:
            print(f"An error occurred: {e}")

        if invalid_tags:
            print("The following modules have invalid semver tags and were skipped:")
            for module, tag in invalid_tags:
                print(f"  - {module}: {tag}")
        return module_data

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
                    'forge_dependencies': forge_info['dependencies'],
                    'module_endpoint_version': forge_info['module_endpoint_version']
                }
            else:
                forge_deps = {dep['name'].replace('/', '-'): dep['version_requirement'] for dep in forge_info['dependencies']}
                differences[module_name] = {
                    'puppet_tag': puppet_tag,
                    'forge_version': forge_version,
                    'forge_dependencies': forge_info['dependencies'],
                    'module_endpoint_version': forge_info['module_endpoint_version']
                }
        return differences

    def compare_versions(puppet_dep_version, dep_version_requirement):
        """Compares a Puppetfile dependency version with a Forge dependency version requirement."""
        requirements = re.findall(r'([<>=]+)\s*([\d.]+)', dep_version_requirement)
        if not requirements:
            try:
                result = semver.match(puppet_dep_version, dep_version_requirement)
                return result
            except ValueError:
                return False

        for operator, version in requirements:
            try:
                if operator == '>=':
                    result = semver.compare(puppet_dep_version, version) >= 0
                    if not result:
                        return False
                elif operator == '>':
                    result = semver.compare(puppet_dep_version, version) > 0
                    if not result:
                        return False
                elif operator == '<=':
                    result = semver.compare(puppet_dep_version, version) <= 0
                    if not result:
                        return False
                elif operator == '<':
                    result = semver.compare(puppet_dep_version, version) < 0
                    if not result:
                        return False
                elif operator == '=':
                    result = semver.compare(puppet_dep_version, version) == 0
                    if not result:
                        return False
            except ValueError:
                return False
        return True

    def print_differences(module_differences, puppetfile_modules, verbose=False, print_all=False):
        """Prints module differences with color-coded status."""
        has_errors = False
        for module, diff in module_differences.items():
            puppet_tag = diff['puppet_tag']
            forge_version = diff['module_endpoint_version'] #Change to use module_endpoint_version
            outdated_version = "[Outdated]" if puppet_tag != forge_version else ""
            orange_outdated = f"\033[38;5;208m{outdated_version}\033[0m" if outdated_version else ""

            forge_deps = diff['forge_dependencies']
            puppet_deps = {k: v['tag'] for k, v in puppetfile_modules.items()}

            module_has_errors = False
            dependency_lines = []

            for dep in forge_deps:
                dep_name = dep['name'].replace('/', '-')
                dep_version = dep['version_requirement']

                if dep_name not in puppet_deps:
                    not_found = "[Not Found]"
                    red_not_found = f"\033[31m{not_found}\033[0m"
                    dependency_lines.append(f"    - {dep_name} ({dep_version}) {red_not_found} {orange_outdated if outdated_version else ''}")
                    module_has_errors = True
                    has_errors = True
                    if verbose:
                        print(f"Debug: Not Found - {dep_name}")
                else:
                    puppet_dep_version = puppet_deps.get(dep_name)
                    if not compare_versions(puppet_dep_version, dep_version):
                        invalid_version = f"[Invalid - Provided:{puppet_dep_version}]"
                        orange_invalid = f"\033[38;5;208m{invalid_version}\033[0m"
                        dependency_lines.append(f"    - {dep_name} ({dep_version}) {orange_invalid}")
                        module_has_errors = True
                        has_errors = True
                        if verbose:
                            print(f"Debug: Invalid - {dep_name}")
                    else:
                        dependency_lines.append(f"    - {dep_name} ({dep_version})")

            if module_has_errors or outdated_version or print_all:
                print(f"\033[1mModule: {module}\033[0m")
                print(f"    Puppetfile Tag: {puppet_tag}")
                print(f"    Forge Version: {forge_version} {orange_outdated}")
                if dependency_lines or print_all:
                    print("    Forge Dependencies:")
                    for line in dependency_lines:
                        print(line)
                print("-" * 20)
                if verbose:
                    print(f"Debug: module_has_errors: {module_has_errors}, outdated_version: {outdated_version}")
                    print(f"Debug: has_errors: {has_errors}")

        return has_errors

    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD', 'Puppetfile'], capture_output=True, text=True)
    changed_files = result.stdout.splitlines()

    if 'Puppetfile' in changed_files or args.print_all:
        puppetfile_path = 'Puppetfile'
        puppetfile_modules = parse_r10k_puppetfile(puppetfile_path)
        forge_modules = get_current_release_and_metadata(puppetfile_modules)
        module_differences = compare_modules(puppetfile_modules, forge_modules)

        has_errors = print_differences(module_differences, puppetfile_modules, args.verbose, args.print_all)

        if has_errors and not args.print_all:
            print("Puppetfile has dependency errors. Please correct them.")
            sys.exit(1)
        else:
            print("Puppetfile dependencies are valid.")
            sys.exit(0)
    else:
        print("No changes to Puppetfile, skipping dependency check.")
        sys.exit(0)

if __name__ == '__main__':
    main()
