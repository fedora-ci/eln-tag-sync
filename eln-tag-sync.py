#!/usr/bin/python3

import argparse
import koji
import requests
import logging
import os


# Connect to Fedora Koji instance
session = koji.ClientSession('https://koji.fedoraproject.org/kojihub')
session.gssapi_login(keytab=os.getenv('KOJI_KEYTAB'))


def get_builds(tag, inherit=False):
    return session.listTagged(tag, latest=True, inherit=inherit)


def tag_build(tag, nvr):
    try:
        return session.tagBuild(tag, nvr)
    except Exception as e:
        # probably a protected package
        print(str(e))
        return None


def get_wanted_packages():
    """
    Fetches the list of desired sources from Content Resolver
    for each of the given 'arches'.
    """
    merged_packages = set()

    distro_url = "https://raw.githubusercontent.com/minimization/lists/main"
    distro_view = "c9s"
    arches = ["aarch64", "armv7hl", "ppc64le", "s390x", "x86_64"]
    which_source = ["source", "buildroot-source"]

    for arch in arches:
        for this_source in which_source:
            url = (
                "{distro_url}"
                "/view-{this_source}-package-name-list--view-{distro_view}--{arch}.txt"
            ).format(distro_url=distro_url, this_source=this_source, distro_view=distro_view, arch=arch)

            logging.debug("downloading {url}".format(url=url))

            r = requests.get(url, allow_redirects=True)
            for line in r.text.splitlines():
                merged_packages.add(line)

    logging.debug("Found a total of {} packages".format(len(merged_packages)))

    return merged_packages


def is_excluded(package):
    """
    Return True if package is permanently excluded from rebuild automation.
    """
    excludes = [
        "kernel",  # it takes too much infra resources to try kernel builds automatically
        "kernel-headers",  # In RHEL kernel-headers is a sub-package of kernel
        "kernel-tools",  # In RHEL kernel-tools is a sub-package of kernel
        "rubygems",  # In RHEL rubygems is a sub-package of ruby
        "rubygem-json",  # In RHEL rubygem-json is a sub-package of ruby
        "rubygem-minitest",  # In RHEL rubygem-minitest is a sub-package of ruby
        "rubygem-power_assert",  # In RHEL rubygem-power_assert is a sub-package of ruby
        "rubygem-rake",  # In RHEL rubygem-rake is a sub-package of ruby
        "rubygem-rdoc",  # In RHEL rubygem-rdoc is a sub-package of ruby
        "rubygem-test-unit",  # In RHEL rubygem-test-unit is a sub-package of ruby
        "shim",  # shim has its own building proceedure
    ]
    exclude_prefix = [
        "shim-",
    ]

    if package in excludes:
        return True
    for prefix in exclude_prefix:
        if package.startswith(prefix):
            return True
    return False


def is_on_hold(package):
    """
    Return True if package is temporarily on hold from rebuild automation.
    """
    hold = [
    ]
    hold_prefix = [
    ]

    if package in hold:
        return True
    for prefix in hold_prefix:
        if package.startswith(prefix):
            return True
    return False


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--srctag",
                        help="Name of the source tag",
                        default="f34")

    parser.add_argument("--desttag",
                        help="Name of the destination tag",
                        default="f34-cr-eln")

    args = parser.parse_args()

    wanted_packages = get_wanted_packages()

    source_builds = get_builds(args.srctag, inherit=True)
    dest_builds = get_builds(args.desttag)
    dest_nvrs = [x['nvr'] for x in dest_builds]

    not_wanted = 0
    excluded = 0
    tagged = 0
    errors = 0

    for source_build in source_builds:
        package = source_build['package_name']
        if package not in wanted_packages:
            # we don't want to sync this package
            not_wanted += 1
            continue
        if source_build['nvr'] in dest_nvrs:
            # this build is already in the dest tag
            continue
        if is_on_hold(package) or is_excluded(package):
            excluded += 1
            # the package is exluded from automation
            continue

        
        print(f"Tagging {source_build['nvr']} into {args.desttag}")
        result = tag_build(args.desttag, source_build['nvr'])
        if result:
            tagged += 1
        else:
            errors += 1

    print('\n\nFinal stats:\n')
    print(f'{not_wanted} packages filtered out as not wanted')
    print(f'{excluded} packages explicitly excluded from automation')
    print(f'{errors} packages failed to be tagged from {args.srctag} to {args.desttag}')
    print(f'{tagged} packages tagged from {args.srctag} to {args.desttag}')
