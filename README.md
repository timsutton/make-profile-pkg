## Make Profile Pkg

Given a Configuration Profile as an argument, this script:
- builds a flat package that installs the profile to a configurable path
- creates a postinstall script to install the profile:
  - (optionally removing the .mobileconfig file after installation)
- saves an uninstall script for the profile alongside the package
- optionally imports the pkg into a Munki repo (see the `-m` option)

Run with `-h` to see the full help.

If the package isn't installed to the boot volume (when using [AutoDMG](https://github.com/MagerValp/AutoDMG), for example), the profile will be also copied to `/private/var/db/ConfigurationProfiles/Setup` so it will be instead be installed when the volume is next booted.


### Rationale

OS X has a mechanism (the `profiles` utility) to install profiles given a Configuration Profile on disk. It can also remove a profile given either the path to the file, or the profile's identifier.

Coupled with the fact that we can package these data and instructions and version the package, we can use built-in mechanisms to install the profile and/or check whether this profile has been installed.


### Munki-specific use

The packages are built to be just as useful without Munki, but if you do import them into Munki, the `uninstall_method` and `uninstall_script` keys will be set appropriately.

If you would rather have a mechanism that can "enforce" that a profile is installed, and with exactly the contents you would expect, this is not it. This relies solely on the installer package receipt to consider the profile as being installed.


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
    PROFILES_SETUP=private/var/db/ConfigurationProfiles/Setup
    /bin/mkdir -p "$3/$PROFILES_SETUP"
    /bin/cp "$3/Library/MyGreatOrg/Profiles/suppress_ml_icloud_asst.mobileconfig" "$3/$PROFILES_SETUP/suppress_ml_icloud_asst.mobileconfig"
    /bin/rm -f "$3/$PROFILES_SETUP/.profileSetupDone"
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
    <string></string>
    <key>display_name</key>
    <string>Profile_suppress_ml_icloud_asst-10.8</string>
    <key>installed_size</key>
    <integer>4</integer>
    <key>installer_item_hash</key>
    <string>fb975facf67986ad3f71f3face884cc46301606f22ccfb6b50834509ba507215</string>
    <key>installer_item_location</key>
    <string>defaults/profiles/Profile_suppress_ml_icloud_asst-10.8.pkg</string>
    <key>installer_item_size</key>
    <integer>2</integer>
    <key>minimum_os_version</key>
    <string>10.5.0</string>
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

