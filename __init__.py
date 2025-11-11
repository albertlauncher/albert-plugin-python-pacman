# -*- coding: utf-8 -*-
#  Copyright (c) 2024 Manuel Schneider

import subprocess
from time import sleep
import pathlib

from albert import Action, StandardItem, PluginInstance, GeneratorQueryHandler, runTerminal, openUrl, makeComposedIcon, \
    makeGraphemeIcon, makeImageIcon

md_iid = "5.0"
md_version = "2.1.1"
md_name = "PacMan"
md_description = "Search, install and remove packages"
md_license = "MIT"
md_url = "https://github.com/albertlauncher/albert-plugin-python-pacman"
md_readme_url = "https://github.com/albertlauncher/albert-plugin-python-pacman/blob/main/README.md"
md_authors = ["@ManuelSchneid3r"]
md_bin_dependencies = ["pacman", "expac"]


class Plugin(PluginInstance, GeneratorQueryHandler):

    pkgs_url = "https://www.archlinux.org/packages/"

    def __init__(self):
        PluginInstance.__init__(self)
        GeneratorQueryHandler.__init__(self)

    @staticmethod
    def makeIcon():
        return makeComposedIcon(makeImageIcon(pathlib.Path(__file__).parent / "arch.svg"), makeGraphemeIcon("📦"))

    def synopsis(self, query):
        return "<package name>"

    def defaultTrigger(self):
        return "pac "

    def items(self, ctx):
        query = ctx.query.strip()

        # Update item on empty queries
        if not query:
            yield [
                StandardItem(
                    id="%s-update" % self.id,
                    text="Pacman package manager",
                    subtext="Enter the package you are looking for or hit enter to update.",
                    icon_factory=Plugin.makeIcon,
                    actions=[
                        Action("up-nc", "Update packages (no confirm)",
                               lambda: runTerminal("sudo pacman -Syu --noconfirm")),
                        Action("up", "Update packages", lambda: runTerminal("sudo pacman -Syu")),
                        Action("up-cache", "Update pacman cache", lambda: runTerminal("sudo pacman -Sy"))
                    ]
                )
            ]
            return

        # avoid rate limiting
        for _ in range(50):
            sleep(0.01)
            if not query.isValid:
                return

        # Get data. Results are sorted, so we can merge in O(n)
        proc_s = subprocess.Popen(["expac", "-Ss", "%n\t%v\t%r\t%d\t%u\t%E", query],
                                  stdout=subprocess.PIPE, universal_newlines=True)
        proc_q = subprocess.Popen(["expac", "-Qs", "%n", query], stdout=subprocess.PIPE, universal_newlines=True)
        proc_q.wait()

        items = []
        local_pkgs = set(proc_q.stdout.read().split('\n'))
        remote_pkgs = [tuple(line.split('\t')) for line in proc_s.stdout.read().split('\n')[:-1]]  # newline at end

        for pkg_name, pkg_vers, pkg_repo, pkg_desc, pkg_purl, pkg_deps in remote_pkgs:
            if query not in pkg_name:
                continue

            pkg_installed = True if pkg_name in local_pkgs else False

            actions = []
            if pkg_installed:
                actions.extend([
                    Action("rem", "Remove", lambda n=pkg_name: runTerminal("sudo pacman -Rs %s" % n)),
                    Action("reinst", "Reinstall", lambda n=pkg_name: runTerminal("sudo pacman -S %s" % n))
                ])
            else:
                actions.append(Action("inst", "Install", lambda n=pkg_name: runTerminal("sudo pacman -S %s" % n)))

            actions.append(Action("pkg_url", "Show on packages.archlinux.org",
                                  lambda r=pkg_repo, n=pkg_name: openUrl(f"{self.pkgs_url}{r}/x86_64/{n}/")))
            if pkg_purl:
                actions.append(Action("proj_url", "Show project website", lambda u=pkg_purl: openUrl(u)))

            item = StandardItem(
                id="%s_%s_%s" % (self.id, pkg_repo, pkg_name),
                icon_factory=Plugin.makeIcon,
                text="%s %s [%s]" % (pkg_name, pkg_vers, pkg_repo),
                subtext=f"{pkg_desc} [Installed]" if pkg_installed else f"{pkg_desc}",
                input_action_text=pkg_name,
                actions=actions
            )
            items.append(item)

        if items:
            yield items
        else:
            yield [
                StandardItem(
                    id="%s-empty" % self.id,
                    text="Search on archlinux.org",
                    subtext="No results found in the local database",
                    icon_factory=Plugin.makeIcon,
                    actions=[Action("search", "Search on archlinux.org", lambda: openUrl(f"{self.pkgs_url}?q={query}"))]
                )
            ]
