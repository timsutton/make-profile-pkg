## Make Profile Pkg

Given a Configuration Profile as an argument, this script:
- builds a flat package that installs the profile to a configurable path
- creates a postinstall script to install the profile:
  - (optionally removing the .mobileconfig file after installation)
- saves an uninstall script for the profile alongside the package
- optionally imports the pkg into a Munki repo (see the `-m` option)
  - *note*: see the 'Munki-specific use' section below regarding Munki's native support for handling configuration profiles

Run with `-h` to see the full help.

If the package isn't installed to the boot volume (when using [AutoDMG](https://github.com/MagerValp/AutoDMG), for example), the profile will be also copied to `/private/var/db/ConfigurationProfiles/Setup` so it will be instead be installed when the volume is next booted.


### Rationale

OS X has a mechanism (the `profiles` utility) to install profiles given a Configuration Profile on disk. It can also remove a profile given either the path to the file, or the profile's identifier.

Coupled with the fact that we can package these data and instructions and version the package, we can use built-in mechanisms to install the profile and/or check whether this profile has been installed.

Read even more backstory [here](http://macops.ca/how-to-package-profiles).


### Munki-specific use

*Note*: As of [Munki 2.2](https://github.com/munki/munki/releases/tag/v2.2.0.2399), Munki can natively import configuration profiles. I would recommend that if you are only planning to deploy a profile using Munki to use its native support rather than this tool. This tool is still useful for building installer packages for use in differentscenarios. See Armin Briegel's [blog post](http://scriptingosx.com/2015/01/push-settings-with-munkis-new-profile-support) for a good example of how this works (specifically towards the bottom, "Importing the Profile into Munki."

The packages are built to be just as useful without Munki, but if you do import them into Munki, the following additional keys will be set appropriately:
- `description`, `display_name` (taken from the profile's `PayloadDisplayName` and `PayloadDescription` keys)
- `installcheck_script` (see below)
- `minimum_os_version` (Profiles require Lion or newer)
- `uninstall_method` and `uninstall_script`

Additionally, the Munki pkginfo will use the `installcheck_script` mechanism to check whether the profile is actually installed on the machine, rather than only checking for an installer package receipt. This allows Munki to ensure that the profile is installed even if a user should later remove it after the initial installation. The script is borrowed from [Graham Gilbert's sample script](https://github.com/grahamgilbert/mactech_2014/blob/effbfbfad4f1dfa9328287127c40a9051dcd4cb2/Profile/installcheck_script_v2.sh) from a session at MacTech 2014.


### Examples

No options are required:

```bash
➜ ./make_profile_pkg.py suppress_ml_icloud_asst.mobileconfig

pkgbuild: Inferring bundle components from contents of /var/folders/8t/5trmslfj2cnd5gxkbmkbn5fj38qb2l/T/tmpaiPyN5
pkgbuild: Adding top-level postinstall script
pkgbuild: Wrote package to /Users/tsutton/git/github/make-profile-pkg/suppress_ml_icloud_asst-2014.04.17.pkg
```

But, there are several you can set:

```bash
➜ ./make_profile_pkg.py \
    --format-name "Profile_%filename%" \
    --installed-path /Library/MyGreatOrg/Profiles \
    --version 10.8 \
    --pkg-prefix org.my.great \
    --delete-after-install \
    --munki-repo-destination "defaults/profiles" \
    --munki-import \
    suppress_ml_icloud_asst.mobileconfig

pkgbuild: Inferring bundle components from contents of /var/folders/8t/5trmslfj2cnd5gxkbmkbn5fj38qb2l/T/tmp_LwP92
pkgbuild: Adding top-level postinstall script
pkgbuild: Wrote package to /Users/tsutton/git/github/make-profile-pkg/Profile_suppress_ml_icloud_asst-10.8.pkg
Copying Profile_suppress_ml_icloud_asst-10.8.pkg to /Volumes/munki_repo/pkgs/defaults/profiles/Profile_suppress_ml_icloud_asst-10.8.pkg...
Saving pkginfo to /Volumes/munki_repo/pkgsinfo/defaults/profiles/Profile_suppress_ml_icloud_asst-10.8.plist...
```

In the latter case, here's what the package's postinstall script looks like:

```bash
#!/bin/sh
if [ "$3" = "/" ] ; then
    /usr/bin/profiles -I -F /Library/MyGreatOrg/Profiles/suppress_ml_icloud_asst.mobileconfig
else
    /bin/mkdir -p "$3/private/var/db/ConfigurationProfiles/Setup"
    /bin/cp "$3"/Library/MyGreatOrg/Profiles/suppress_ml_icloud_asst.mobileconfig "$3"/private/var/db/ConfigurationProfiles/Setup/suppress_ml_icloud_asst.mobileconfig
    /bin/rm -f "$3/private/var/db/ConfigurationProfiles/Setup/.profileSetupDone"
fi

/bin/rm -f /Library/MyGreatOrg/Profiles/suppress_ml_icloud_asst.mobileconfig
```


... and the generated pkginfo:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>autoremove</key>
    <false/>
    <key>catalogs</key>
    <array>
        <string>testing</string>
    </array>
    <key>description</key>
    <string>Custom: com.apple.SetupAssistant</string>
    <key>display_name</key>
    <string>MCXToProfile: com.apple.SetupAssistant</string>
    <key>installcheck_script</key>
    <string>#!/bin/bash

# The version of the package
PKG_VERSION="10.8"

# The identifier of the package
PKG_ID="org.my.great.Profile_suppress_ml_icloud_asst"

# The identifier of the profile
PROFILE_ID="suppress_ml_icloud_asst"

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
</string>
    <key>installed_size</key>
    <integer>4</integer>
    <key>installer_item_hash</key>
    <string>b968f5dd9fed506e6592cb26887034c1346339a4dc3e4312e292f40f094e9cb7</string>
    <key>installer_item_location</key>
    <string>defaults/profiles/Profile_suppress_ml_icloud_asst-10.8.pkg</string>
    <key>installer_item_size</key>
    <integer>4</integer>
    <key>minimum_os_version</key>
    <string>10.7</string>
    <key>name</key>
    <string>Profile_suppress_ml_icloud_asst</string>
    <key>receipts</key>
    <array>
        <dict>
            <key>installed_size</key>
            <integer>4</integer>
            <key>packageid</key>
            <string>org.my.great.Profile_suppress_ml_icloud_asst</string>
            <key>version</key>
            <string>10.8</string>
        </dict>
    </array>
    <key>uninstall_method</key>
    <string>uninstall_script</string>
    <key>uninstall_script</key>
    <string>#!/bin/sh

/usr/bin/profiles -R -p suppress_ml_icloud_asst
/bin/rm -f /Library/MyGreatOrg/Profiles/suppress_ml_icloud_asst.mobileconfig
/usr/sbin/pkgutil --forget org.my.great.Profile_suppress_ml_icloud_asst
</string>
    <key>uninstallable</key>
    <true/>
    <key>version</key>
    <string>10.8</string>
</dict>
</plist>
```

### Signing Packages

Output packages can be optionally signed using the `--sign` option.  A valid identity must be provided.  To find valid identities that can be used for signing:  
`/usr/bin/security find-identity -p basic -v`

Note that if you use Apple developer certificates, you must use an Installer type certificate to sign packages using `pkgbuild`.  Note also that if you use a certificate that is untrusted on client machines, your package will not install.

Use the common name of a valid identity to pass to the `--sign` argument:  
```bash
 ./make_profile_pkg.py \
    --format-name "Profile_%filename%" \
    --installed-path /Library/MyGreatOrg/Profiles \
    --version 10.8 \
    --pkg-prefix org.my.great \
    --delete-after-install \
    --munki-repo-destination "defaults/profiles" \
    --munki-import \
    --sign "3rd Party Mac Developer Installer"
    suppress_ml_icloud_asst.mobileconfig

pkgbuild: Inferring bundle components from contents of /var/folders/8t/5trmslfj2cnd5gxkbmkbn5fj38qb2l/T/tmp_LwP92
pkgbuild: Adding top-level postinstall script
pkgbuild: Signing package with identity "3rd Party Mac Developer Installer" from keychain /Users/tsutton/Library/Keychains/login.keychain
pkgbuild: Adding certificate "Apple Worldwide Developer Relations Certification Authority"
pkgbuild: Adding certificate "Apple Root CA"
pkgbuild: Wrote package to /Users/tsutton/git/github/make-profile-pkg/Profile_suppress_ml_icloud_asst-10.8.pkg
Copying Profile_suppress_ml_icloud_asst-10.8.pkg to /Volumes/munki_repo/pkgs/defaults/profiles/Profile_suppress_ml_icloud_asst-10.8.pkg...
Saving pkginfo to /Volumes/munki_repo/pkgsinfo/defaults/profiles/Profile_suppress_ml_icloud_asst-10.8.plist...
```

You will be prompted to approve the use of your identity by `pkgbuild` and `security`.  These settings can be changed in Keychain Access by selecting your private key associated with the certificate and choosing File -> Get Info -> Access Control.