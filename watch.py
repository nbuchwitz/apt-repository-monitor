#!/usr/bin/env python3

import sys
from typing import List, Union

import yaml
import requests

from repository_monitor import Package, Repo


def new_package_notification(webhook_url: str, repository: str, distribution: str, architecture: str, packages: List[Package]):
    title = f"📦 Neue Pakete im APT-Repository ({distribution} / {architecture})"
    text = f"Es wurden {len(packages)} neue Pakete im APT-Repository {repository} veröffentlicht.\nDie Liste aller Änderungen findet sich unter https://kunbus-gmbh.atlassian.net/wiki/spaces/EN/pages/3264774241/Rolling+Release+Notes"
    facts = [
        {
            "name": package.name,
            "value": package.version
        } for package in packages
    ]

    return notification(webhook_url, title, text, facts)


def notification(webhook_url: str, title: str, text: str, facts: list):
    response = requests.post(
        url=webhook_url,
        headers={"Content-Type": "application/json"},
        json={
            "themeColor": "#ff9900",
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "activitySubtitle": text,
                "facts": facts
            }],
        },
    )

    return response.status_code


def load_config() -> Union[str, List[Package]]:
    with open("repository-monitor.yml", "r") as config:
        try:
            config = yaml.safe_load(config)

            repositories = []
            webhook_url = config.get("webhook_url")

            for repo in config.get("repositories"):
                repositories.append(Repo.from_config(repo))

            return webhook_url, repositories
        except (ValueError, yaml.YAMLError) as exc:
            raise Exception(f"Invalid configuration: {exc}")


if __name__ == "__main__":
    try:
        webhook_url, repos = load_config()
    except Exception as exc:
        print(f"Could not load configuration: {exc}", file=sys.stderr)
        sys.exit(1)

    def repo_created_callback(filename, repo: Repo):
        title = f"💡 Neues APT-Repository in Beobachtungsliste ({repo.dist} / {repo.arch})"
        text = f"Es wurden wurde ein neues Repository {repo.url} zur Beobachtungsliste hinzugefügt."

        notification(webhook_url, title, text, [])

    try:
        for repo in repos:
            new_packages = repo.check_updates(repo_created_callback=repo_created_callback)

            if new_packages:
                rc = new_package_notification(
                    webhook_url,
                    repo.url,
                    repo.dist,
                    repo.arch,
                    new_packages
                )
    except Exception as exc:
        print(f"Could not check for new packages: {exc}", file=sys.stderr)
        sys.exit(2)
