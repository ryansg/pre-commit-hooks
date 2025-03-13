# Puppetfile Dependency Checker

This pre-commit hook checks your `Puppetfile` dependencies against the Puppet Forge, ensuring that the versions specified in your `Puppetfile` meet the requirements of the modules' dependencies.

## What it Does

* **Verifies Dependency Versions:** Compares the dependency versions specified in your `Puppetfile` with the version requirements of the modules' dependencies as published on the Puppet Forge.
* **Detects Outdated Modules:** Identifies modules in your `Puppetfile` that are outdated compared to the latest versions on the Puppet Forge.
* **Finds Missing Dependencies:** Flags any dependencies required by Forge modules that are not present in your `Puppetfile`.
* **Displays Invalid Versions:** Highlights dependencies with versions that do not meet the requirements specified by the Forge.
* **Provides Detailed Output:** Displays the module name, Puppetfile tag, Forge version, and dependency information, with color-coded status messages.
* **Verbose Output:** Option for detailed debug output.
* **Print all modules:** Option to print all modules and their dependencies.

## How to Use

1.  **Install `pre-commit`:**

    ```bash
    pip install pre-commit
    ```

2.  **Add the Hook to Your `.pre-commit-config.yaml`:**

    Add the following entry to your `.pre-commit-config.yaml` file:

    ```yaml
    repos:
      - repo: https://github.com/ryansg/pre-commit-hooks.git # Replace with the URL of this hook's repository. Example: [https://github.com/your-username/puppetfile-dependency-check-hook](https://github.com/your-username/puppetfile-dependency-check-hook)
        rev: main  # Or a specific tag or commit hash (e.g., v1.0.0)
        hooks:
          - id: check-puppetfile-dependencies
    ```

    **Important:**

    * Replace `<YOUR_REPO_URL>` with the URL of the repository where this hook is hosted.
    * It's recommended to use a specific tag or commit hash for `rev` to ensure stability.

3.  **Install the Hook:**

    Run the following command in your repository's root directory:

    ```bash
    pre-commit install
    ```

4.  **Use the Hook:**

    The hook will now run automatically before each commit.

## Command-Line Options

* **`--verbose` or `-v`:** Enables verbose output, showing detailed debugging information.

    ```bash
    pre-commit run check-puppetfile-dependencies --all-files --verbose
    ```

* **`--print-all` or `-a`:** Prints all modules and their dependencies, regardless of whether there are errors.

    ```bash
    pre-commit run check-puppetfile-dependencies --all-files --print-all
    ```

## Example Output
```
poetry run python3 check_puppetfile_dependencies.py
Module: puppet-varnish
  Puppetfile Tag: 5.1.0
  Forge Version: 5.1.0
  Forge Dependencies:
    - puppetlabs-stdlib (>= 3.2.0 < 10.0.0)
    - puppetlabs-concat (>= 9.0.0 < 10.0.0)
    - puppetlabs-apt (>= 1.1.0 < 10.0.0) [Invalid - Provided:10.0.1]
    - puppetlabs-firewall (>= 7.0.0 < 8.0.0) [Invalid - Provided:8.1.3]
    - puppet-systemd (>= 3.2.0 < 7.0.0) [Invalid - Provided:8.1.0]
--------------------
Module: puppetlabs-apache
  Puppetfile Tag: 12.2.0
  Forge Version: 12.3.0 [Outdated]
  Forge Dependencies:
    - puppetlabs-stdlib (>= 4.13.1 < 10.0.0)
    - puppetlabs-concat (>= 2.2.1 < 10.0.0)
--------------------
Module: puppetlabs-firewall
  Puppetfile Tag: 8.1.3
  Forge Version: 8.1.4 [Outdated]
  Forge Dependencies:
    - puppetlabs-stdlib (>= 9.0.0 < 10.0.0)
--------------------
Module: saz-ssh
  Puppetfile Tag: 13.0.0
  Forge Version: 13.1.0 [Outdated]
  Forge Dependencies:
    - puppetlabs-stdlib (>= 9.0.0 < 10.0.0)
    - puppetlabs-concat (>= 2.2.0 < 10.0.0)
    - puppet-systemd (>= 3.7.0 < 9.0.0)
--------------------
Module: saz-sudo
  Puppetfile Tag: 9.0.0
  Forge Version: 9.0.2 [Outdated]
--------------------
Puppetfile has dependency errors. Please correct them.
```
