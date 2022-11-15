# APT-Repository Monitor

By caching the repository's "Package" file locally, this tool monitors a list of APT repositories for new packages. When new packages are detected, a notification is sent via Teams (for each repository with new packages). 

## Usage

1. Configure your repositories and the webhook in `repository-monitor.yml`
2. Call script: `./watch.py` (eg. via cron job)