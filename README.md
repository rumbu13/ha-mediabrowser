# Media Browser - Emby/Jellyfin integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Community Forum][forum-shield]][forum]

_Home Assistant integration for [Emby][emby] and [Jellyfin][jellyfin]._


## Summary

This integration support both media server types, both of them using the same API with minor differences. The following
components are installed:
- A [media source][mediasource] for browsing your server(s) libraries
- Multiple [media players][mediaplayer], one for each connected session
- A [sensor][sensor] displaying number of active sessions
- Multiple [sensors][sensor], one for each library displaying number of items in your library
- Multiple [sensors][sensor] for upcoming media
- Multiple [buttons][button] used for rescanning, rebooting or stopping your server
- An enhanced [play media][play_media] service allowing you to play anything from your libraries based on various search criteria


This integration exposes a MediaBrowser server (Emby or Jellyfin) as a [media source][mediasource] in Home Assistant.
It will create also media players for each


**This integration will set up the following platforms.**



Platform | Name | Description
-- | -- | --
`sensor` | Sessions | Displays number of active sessions. Details of each session can be found in the attributes
`sensor` | Library name | For each library displays number of items. Last added items can be found in the attributes
`button` | Rescan | Rescans libraries
`button` | Restart | Restarts the server
`button` | Shutdown | Shutdown the server
`media_player` | Device name | Media player for each server session
`media_source` | Emby/Jellyfin | Media source that can be used to play media from the server



## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `mediabrowser`.
1. Download _all_ the files from the `custom_components/mediabrowser/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "mediabrowser"

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[emby]: https://emby.media
[jellyfin]: https://jellyfin.org
[buymecoffee]: https://www.buymeacoffee.com/rumbu13
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/rumbu13/ha-mediabrowser.svg?style=for-the-badge
[commits]: https://github.com/rumbu13/ha-mediabrowser/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/rumbu13/ha-mediabrowser.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-rumbu13-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/rumbu13/ha-mediabrowser.svg?style=for-the-badge
[releases]: https://github.com/rumbu13/ha-mediabrowser/releases

[mediasource]: https://www.home-assistant.io/integrations/#media-source
[mediaplayer]: https://www.home-assistant.io/integrations/#media-player
[sensor]: https://www.home-assistant.io/integrations/#sensor
[button]: https://www.home-assistant.io/integrations/#button
[play_media]: https://www.home-assistant.io/integrations/media_player/#service-media_playerplay_media
