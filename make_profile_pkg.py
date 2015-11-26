#!/usr/bin/python
#
# make_profile_pkg.py
#
# Tim Sutton, 2014

import optparse
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile

from pipes import quote
from string import Template
from time import localtime
from xml.parsers.expat import ExpatError

default_name_format_string = "%filename%"
default_installed_path = "/usr/local/share"
default_pkg_prefix = "com.github.makeprofilepkg"
default_repo_destination = "profiles"

def main():
    usage = "%prog [options] path/to/mobileconfig/file"
    o = optparse.OptionParser(usage=usage)
    m_opts = optparse.OptionGroup(o, "Munki options")
    m_opts.add_option("-m", "--munki-import", action="store_true",
        default=False,
        help=("Import resulting package into Munki. "))
    m_opts.add_option("-d", "--munki-repo-destination", default=default_repo_destination,
        help=("Destination directory in Munki repo. Defaults to '%s'. "
              % default_repo_destination))
    o.add_option_group(m_opts)

    o.add_option("-o", "--output-dir", default=os.getcwd(),
        help=("Output directory for built package and uninstall script. "
              "Directory must already exist. Defaults to the current "
              "working directory."))
    o.add_option("-f", "--format-name", default=default_name_format_string,
        metavar="FORMAT-STRING",
        help=("A format string specifying the desired file/pkginfo name, which "
              "may contain tokens that are substituted. Current tokens "
              "supported are '%filename%' (name component of file's basename), "
              "and '%id%' (profile's PayloadIdentifier key). "
              "Defaults to '%filename%'."))
    o.add_option("-p", "--installed-path", default=default_installed_path,
        help=("Installed path for the profile. Defaults to '%s'. "
            % default_installed_path))
    o.add_option("--pkg-prefix", default=default_pkg_prefix,
        help=("Installer pkg identifier prefix. Defaults to '%s'. "
              % default_pkg_prefix))
    o.add_option("-U", dest="username", metavar="USERNAME",
        help=("Includes a '-U <username>' option that will be passed to the "
              "`profiles` command. Please see the `profiles` manpage for "
              "more details on the -U option. This is also only supported on "
              "10.11 and up, and the package may fail if installed on an "
              "earlier OS version."))
    o.add_option("-v", "--version",
        help=("Version of the built pkg. Defaults to 'YYYY.MM.DD' "
              "derived from today's date."))
    o.add_option("--delete-after-install", action="store_true",
        default=False,
        help=("Configure pkg postinstall script to remove mobileconfig file "
              "after installation."))
    o.add_option("--sign",
        help=("Sign the resulting package with the specified identity."))

    opts, args = o.parse_args()

    if len(args) < 1:
        o.print_help()
        sys.exit(1)
    if not opts.installed_path.startswith("/"):
        print >> sys.stderr, (
            "WARNING: Omitted leading slash for --installed-path %s, "
            "automatically adding one." % opts.installed_path)
        opts.installed_path = "/" + opts.installed_path

    profile_path = args[0]
    pkgbuild = "/usr/bin/pkgbuild"
    munkiimport = "/usr/local/munki/munkiimport"
    security = "/usr/bin/security"
    req_executables = [pkgbuild]
    if opts.munki_import:
        req_executables.append(munkiimport)
    for executable in req_executables:
        if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
            sys.exit("A required exeuctable, '%s', could not be found "
                     "or is not executable!" % executable)

    output_dir = opts.output_dir
    if not os.path.isdir(output_dir) or not os.access(output_dir, os.W_OK):
        sys.exit("Output directory '%s' either doesn't exist or is not writable!"
            % output_dir)

    # Grab the profile's identifier for use later in the uninstall_script
    try:
        pdata = plistlib.readPlist(profile_path)
    except ExpatError as e:
        print >> sys.stderr, (
            "Profile is either malformed or signed. Attempting to "
            "unsign the profile. Message: %s" % e.message)
        try:
            profile_data = subprocess.check_output([
                security,
                "cms",
                "-D",
                "-i", profile_path])
            pdata = plistlib.readPlistFromString(profile_data)
        except subprocess.CalledProcessError as e:
            print >> sys.stderr, (
                "Profile could not be unsigned.")
            sys.exit("Error %s: %s" % (e.returncode, e.message))
    try:
        profile_identifier = pdata["PayloadIdentifier"]
    except KeyError:
        sys.exit("Expected 'PayloadIdentifier' key in profile, but none found!")
    except ExpatError as e:
        print >> sys.stderr, (
            "Profile is malformed.")
        sys.exit("Error: %s" % e.message)

    # Grab other profile metadata for use in Munki's pkginfo
    profile_display_name = pdata.get("PayloadDisplayName")
    profile_description = pdata.get("PayloadDescription", '')

    # Version
    version = opts.version
    if not version:
        now = localtime()
        version = "%04d.%02d.%02d" % (now.tm_year, now.tm_mon, now.tm_mday)

    # Naming of item
    profile_name = os.path.basename(profile_path).split(".mobileconfig")[0]
    replaced_template = Template(re.sub("%(?P<token>.+?)%", "${\g<token>}", opts.format_name))
    templatables = {
        "filename": profile_name,
        "id": profile_identifier
    }
    item_name = replaced_template.safe_substitute(templatables)

    # Installer package-related
    pkg_filename = "%s-%s.pkg" % (item_name, version)
    pkg_identifier = "%s.%s" % (opts.pkg_prefix, item_name)

    pkg_output_path = os.path.join(output_dir, pkg_filename)

    root = tempfile.mkdtemp()
    pkg_payload_destination = os.path.join(root, opts.installed_path.lstrip("/"))
    profile_installed_path = os.path.join(
        opts.installed_path, os.path.basename(profile_path))
    os.makedirs(pkg_payload_destination)
    shutil.copy(profile_path, pkg_payload_destination)

    # -- postinstall script
    script_root = tempfile.mkdtemp()
    script_path = os.path.join(script_root, "postinstall")

    config_profile = profile_name + '.mobileconfig'

    additional_opts = ""
    if opts.username:
        additional_opts += "-U %s" % opts.username

    install_script = """#!/bin/sh
if [ "$3" = "/" ] ; then
    /usr/bin/profiles -I -F %s %s
else
    /bin/mkdir -p "$3/private/var/db/ConfigurationProfiles/Setup"
    /bin/cp %s %s
    /bin/rm -f "$3/private/var/db/ConfigurationProfiles/Setup/.profileSetupDone"
fi
""" % (
    quote(profile_installed_path),
    quote(additional_opts),
    "\"$3\"" + quote(profile_installed_path),
    "\"$3\"" + quote('/private/var/db/ConfigurationProfiles/Setup/' + config_profile)
    )

    if opts.delete_after_install:
        install_script += """\n/bin/rm -f %s""" % quote(profile_installed_path)
    with open(script_path, "w") as fd:
        fd.write(install_script)
    os.chmod(script_path, 0755)

    # thanks, frogor
    cmd = [pkgbuild,
           "--root", root,
           "--identifier", pkg_identifier,
           "--version", version,
           "--scripts", script_root,
           pkg_output_path]

    if opts.sign:
        # Use slice assignment to insert an additional option before the final argument
        cmd[-1:] = ["--sign", opts.sign, pkg_output_path]

    subprocess.call(cmd)

    # -- uninstaller script
    uninstall_script_path = os.path.join(output_dir, "%s_uninstall.sh" % item_name)
    uninstall_script = """#!/bin/sh

/usr/bin/profiles -R -p %s
/bin/rm -f %s
/usr/sbin/pkgutil --forget %s
""" % (quote(profile_identifier), quote(profile_installed_path), quote(pkg_identifier))
    with open(uninstall_script_path, "w") as fd:
        fd.write(uninstall_script)

    # -- installcheck_script
    installcheck_script_path = os.path.join(output_dir, "%s_installcheck.sh" % item_name)
    installcheck_script = """#!/bin/bash

# The version of the package
PKG_VERSION="%s"

# The identifier of the package
PKG_ID="%s"

# The identifier of the profile
PROFILE_ID="%s"

# The version installed from pkgutil
VERSION_INSTALLED=`/usr/sbin/pkgutil --pkg-info "$PKG_ID" | grep version | sed 's/^[^:]*: //'`

if ( /usr/bin/profiles -P | /usr/bin/grep -q $PROFILE_ID ); then
    # Profile is present, check the version
    if [ "$VERSION_INSTALLED" = "$PKG_VERSION" ]; then
        # Correct version, all good
        exit 1
    else
        exit 0
    fi
else
    # Profile isn't there, need to install
    exit 0
fi
""" % (version, pkg_identifier, profile_identifier)
    with open(installcheck_script_path, "w") as fd:
        fd.write(installcheck_script)

    # -- munkiimport it?
    if opts.munki_import:
        subprocess.call([
            munkiimport,
            "--nointeractive",
            "--displayname", profile_display_name or item_name,
            "--description", profile_description,
            "--subdirectory", opts.munki_repo_destination,
            "--uninstall-script", uninstall_script_path,
            "--installcheck-script", installcheck_script_path,
            "--minimum-os-version", "10.7",
            pkg_output_path
            ]
        )

if __name__ == '__main__':
    main()
