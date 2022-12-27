import abc
import re
import subprocess
import sys
import warnings
from shutil import which
from typing import Match, Optional, NamedTuple

from cleo.io.io import IO
from poetry.poetry import Poetry
from poetry.core.utils.helpers import module_name

from poem_plugins.base import BasePlugin
from poem_plugins.config import Config, VersionEnum


GIT_BIN = which('git')
WARNING_TEXT = (
    '"git" binary was not found, this plugin this will not work properly'
)
if GIT_BIN is None:
    warnings.warn(WARNING_TEXT)


class Version(NamedTuple):
    major: int
    minor: int
    patch: int
    commit: str

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}+g{self.commit}"


class IVersionPlugin(abc.ABC):
    @abc.abstractmethod
    def _should_be_used(self, config: Config) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_version(self, config: Config) -> Version:
        raise NotImplementedError


class BaseVersionPlugin(BasePlugin, IVersionPlugin, abc.ABC):
    VERSION_TEMPLATE = (
        "# THIS FILE WAS GENERATED BY \"{whoami}\"\n"
        "# NEWER EDIT THIS FILE MANUALLY\n"
        "\n"
        "version_info = ({major}, {minor}, {patch})\n"
        "__version__ = {version}\n"
    )

    def activate(self, poetry: Poetry, io: IO) -> None:
        config: Config = self.get_config(poetry)
        if not self._should_be_used(config):
            return
        try:
            version = self._get_version(config)
        except Exception as exc:
            io.write_error_line(f"<b>poem-plugins</b>: {exc}")
            raise exc

        io.write_line(
            f"<b>poem-plugins</b>: Setting version to: {version}"
        )
        poetry.package.version = version  # type: ignore

        package_name = module_name(poetry.package.name)
        with open(f"{package_name}/version.py", "w") as file:
            file.write(
                self.VERSION_TEMPLATE.format(
                    whoami=".".join((
                        self.__class__.__module__,
                        self.__class__.__name__
                    )),
                    major=version.major,
                    minor=version.minor,
                    patch=version.patch,
                    version=str(version),
                )
            )
        return


class GitLongVersionPlugin(BaseVersionPlugin):
    def _should_be_used(self, config: Config) -> bool:
        return config.version_plugin == VersionEnum.GIT_LONG

    def _get_version(self, config: Config) -> Version:
        if GIT_BIN is None:
            raise RuntimeError(WARNING_TEXT)

        result = subprocess.run(
            [GIT_BIN, "describe", "--long"],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )

        if result.returncode != 0:
            raise RuntimeError("Cannot found git version")

        match: Optional[Match[str]] = re.match(
            config.git_version_prefix + r'(\d+)\.(\d+)-(\d+)-(\S+)',
            result.stdout.strip()
        )

        if match is None:
            raise RuntimeError("Cannot parse git version")

        return Version(*match.groups())
