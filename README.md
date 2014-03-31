## make_munki_profile_pkg

Given a Configuration Profile as an argument, this script:
- builds a flat package that installs it to a configurable path
- creates a postinstall script to install the profile
  - (optionally removing the .mobileconfig file after installation)
- creates an uninstall script for Munki to allow the profile to be
  later removed
- optionally calls munkiimport to create a new pkginfo and import the pkg into
  the repo (when passing the ``-m`` option)

Run with `-h` to see the full help.

There are some additional options to tweak the pkg/Munki item name and package identifier, but currently no other options to configure the pkginfo keys you may wish to configure afterwards (minimum_os_version, requires, update_for, etc.).

If the package isn't installed to the boot volume (when using AutoDMG, for example), the profile will be copied to`` /private/var/db/ConfigurationProfiles/Setup`` so it will be installed at the next reboot.


### Rationale

OS X has a mechanism (the `profiles` utility) to install profiles given a Configuration Profile on disk. It can also remove a profile given either the path to the file, or the profile's identifier.

Coupled with the fact that we can package these data and instructions and version the package, we have at least a basic mechanism to consider that a profile has been installed.

The installation of the profile is done as a postinstall script within the package rather than a Munki `postinstall_script` so that the package is not limited to use with Munki. The removal of the package does make use of Munki's `uninstall_script` removal method, however.

If you would rather have a mechanism that can "enforce" that a profile is installed, and with exactly the contents you would expect, this is not it. This relies solely on the installer package receipt to consider the profile as being installed.

### Examples

No options are required:

```bash
➜ ./make_munki_profile_pkg.py suppress_ml_icloud_asst.mobileconfig

pkgbuild: Inferring bundle components from contents of /var/folders/8t/5trmslfj2cnd5gxkbmkbn5fj38qb2l/T/tmpsgtSN2
pkgbuild: Adding top-level postinstall script
pkgbuild: Wrote package to /var/folders/8t/5trmslfj2cnd5gxkbmkbn5fj38qb2l/T/tmpVNbN1Z/suppress_ml_icloud_asst-2014.03.21.pkg
Copying suppress_ml_icloud_asst-2014.03.21.pkg to /Volumes/munki_repo/pkgs/profiles/suppress_ml_icloud_asst-2014.03.21.pkg...
Saving pkginfo to /Volumes/munki_repo/pkgsinfo/profiles/suppress_ml_icloud_asst-2014.03.21.plist...
```

But, there are several you can set:

```bash
➜ ./make_munki_profile_pkg.py \
    --format-name "Profile_%%filename" \
    --installed-path /Library/MyGreatOrg/Profiles \
    --version 10.8 \
    --pkg-prefix org.my.great \
    --delete-after-install \
    --munki-repo-destination "defaults/profiles" \
    suppress_ml_icloud_asst.mobileconfig

pkgbuild: Inferring bundle components from contents of /var/folders/8t/5trmslfj2cnd5gxkbmkbn5fj38qb2l/T/tmpdhHNxn
pkgbuild: Adding top-level postinstall script
pkgbuild: Wrote package to /var/folders/8t/5trmslfj2cnd5gxkbmkbn5fj38qb2l/T/tmpw2N1dL/Profile_suppress_ml_icloud_asst-10.8.pkg
Copying Profile_suppress_ml_icloud_asst-10.8.pkg to /Volumes/munki_repo/pkgs/defaults/profiles/Profile_suppress_ml_icloud_asst-10.8.pkg...
Saving pkginfo to /Volumes/munki_repo/pkgsinfo/defaults/profiles/Profile_suppress_ml_icloud_asst-10.8.plist...
```

In the latter case, the package's postinstall script:

```bash
#!/bin/sh

/usr/bin/profiles -I -F /Library/MyGreatOrg/Profiles/suppress_ml_icloud_asst.mobileconfig

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

