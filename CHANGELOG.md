# Changelog

<!-- markdownlint-disable MD024 -->
<!--
Possible Tags:
 - Added
 - Changed
 - Deprecated
 - Removed
 - Fixed
 - Security
-->
<!-- changelog-begin -->

## [Unreleased](https://github.com/DonalChilde/esi-auth/compare/0.3.0...dev)

<!-- Dont forget to:
    - Update the Unreleased compare version to latest release tag
    - Update compare/_previous_version_tag_
    - Delete <a></a> tag
    - Update issues and pull requests as needed.-->
<!-- Copy paste release notes below here -->
<!-- scriv-insert-here -->

<a id='changelog-0.3.0'></a>
## [0.3.0](https://github.com/DonalChilde/esi-auth/compare/0.0.0...0.3.0) —  2025-11-29

### Whats Changed in 0.3.0

Talk about the changes in general

### Added

* Allow passing arguments through get_settings to set app config.

  get_settings() will now accept an optional dictionary of app configuration settings, as well as other keyword
  arguments that will be passed into the pydantic BaseSettings class used to represent app settings.
  This will allow app settings to be configured programatically, useful for testing and third party app usage.

  While the primary source for app settings remains the env file, this allows overriding individual settings from inside the app.

## 0.0.0 - 2025-07-01

This is the start of something....

### Added

- Project Start

<https://keepachangelog.com/en/1.0.0/>

<!-- changelog-end -->
