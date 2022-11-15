import filecmp
import os
import shutil
import sys
import tempfile
import urllib.request


def url2path(url: str) -> str:
    return url.replace(":", "").replace("/", "-")


class Package:
    def __init__(self, name: str, version: str, sha1: str, filename: str) -> None:
        self.name = name
        self.version = version
        self.sha1 = sha1
        self.filename = filename

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Package):
            return False

        if self.name != other.name:
            return False

        if self.sha1 is not None and other.sha1 is not None:
            return self.sha1 == other.sha1

        return self.version == other.version

    def __str__(self) -> str:
        return f"{self.name}={self.version} ({self.sha1})"

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return int(self.sha1, 16)


class Repo:
    def __init__(self, url: str, dist: str, arch: str, components: list = None) -> None:
        self.url = url
        self.dist = dist
        self.arch = arch

        if components is None:
            self.components = ["main"]
        else:
            self.components = components

    def __str__(self) -> str:
        return f"Repo {self.url} {self.dist} {self.arch}"

    @staticmethod
    def from_config(config) -> "Repo":
        for required_option in ["url", "distribution", "architecture"]:
            if required_option not in config:
                raise ValueError(f"Missing required configuration option: {required_option}")

        components = config.get("components", None)
        repo = Repo(config["url"], config["distribution"], config["architecture"], components)

        return repo

    def check_updates(self, *, repo_created_callback: callable = None):
        for component in self.components:
            filename = f"cache/packages_{url2path(self.url)}" \
                f"_{self.dist}_{component}_binary-{self.arch}"

            if not os.path.exists(filename):
                print(f"Initial download of {self.url} with "
                      f" distribution={self.dist}"
                      f" architecture={self.arch}"
                      f" component={component}")

                self.download_package_list(component, filename)

                if callable(repo_created_callback):
                    repo_created_callback(filename, self)

            with tempfile.NamedTemporaryFile() as tmp:
                self.download_package_list(component, tmp.name)

                if self.check_package_list(filename, tmp.name):
                    packages_cached = self.parse_package_list(filename)
                    packages_downloaded = self.parse_package_list(tmp.name)

                    new_packages = set(packages_downloaded) - set(packages_cached)

                    # save new package list for later
                    shutil.copyfile(tmp.name, filename)

                    print(f"Found {len(new_packages)} new packages in {self.url} with"
                          f" distribution={self.dist}"
                          f" architecture={self.arch}"
                          f" component={component}")

                    return new_packages

    def check_package_list(self, list_cached: str, list_downloaded: str):
        return not filecmp.cmp(list_cached, list_downloaded)

    def download_package_list(self, component: str, filename: str) -> str:
        url = f"{self.url}/dists/{self.dist}/{component}/binary-{self.arch}/Packages"

        urllib.request.urlretrieve(url, filename)

        return filename

    def parse_package_list(self, package_list: str) -> list:
        packages = []

        with open(package_list, "r") as f:
            lookup = {"Package": "name",
                      "Version": "version",
                      "SHA1": "sha1",
                      "Filename": "filename"}

            entry = {}

            for line in f.readlines():
                if not line.strip():
                    # empty line found
                    try:
                        if entry:
                            # some attributes have been parsed, let's try to create a Package()
                            packages.append(Package(**entry))
                    except TypeError as te:
                        print(f"Failed to create list entry for package: {te}", file=sys.stderr)

                    entry = {}
                    continue
                try:
                    if line.startswith(" "):
                        # ignore text in Description, which starts with blanks
                        continue

                    key, value = line.split(":", 1)
                    if key in lookup:
                        entry[lookup[key]] = value.lstrip().rstrip()
                except ValueError as ve:
                    print(f"Failed to parse package data: {ve}", file=sys.stderr)

        return packages
