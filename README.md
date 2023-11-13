# perforce-blender-addon
A Blender 3.0+ addon that allows Perforce users to check-in / check-out files with a Blender UI panel. "p4" must be installed.

## Installation
Download the Python file and import it to Blender as an add-on.

## Features

* Warn users if they try to check-out a file that someone else has locked
* Warn users if their file is out of date
* Provide a side-panel GUI with buttons for **common p4 commands**
  * "Download updates": `p4 sync`
  * "Status check": plain-English translation of `p4 fstat`
  * "Mark this file for future upload": `p4 add`
  * "Enable editing in this file": `p4 edit`
  * "Upload new version": `p4 submit`
  * "Restore last uploaded version": `p4 revert`
  * "Open P4V program": `p4v`
* (Windows only) Warn users when they close a file that has been added or checked-out, but not submitted.
  * This prevents users from forgetting to check-in before going AFK.
* UI panel dynamically enables and disables buttons depending on `p4 fstat` info, to improve clarity
* UI panel **hides itself** when file is unsaved
* **Manual unlock tool** for files which are not in a workspace, or when `p4` is not installed

## Screenshots

## Future updates (aspirational)

* Repackage this addon into a .zip file
* Improve the UX of the N-panel
* Add loading bars for lag-intensive operations
* Create a separate text descriptor file to more easily edit tooltips
* Support popup windows on Mac and Linux by bundling `tkinter`
