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

This integration support both media server types. The following components are installed:
- [Media Source][mediasource] for browsing your server(s) libraries
- [Media Player][mediaplayer], one for each connected session
- [Session Sensor][sensor] for active sessions
- [Library Sensor][sensor], one for each library
- [Upcoming Media Sensor][sensor] one for each media type
- [Server Button][button] for rescanning, rebooting or stopping your server
- [Play Media Service][play_media] allowing you to play anything from your libraries based on various search criteria


## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `mediabrowser`.
1. Download _all_ the files from the `custom_components/mediabrowser/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "mediabrowser"

## Configuration

Configuration is done using user interface. The integration will try to detect automatically your server settings. 
If more than one server is found, a selection dialog will be displayed.

|Field|Example|Explanation|
|--|--|-----|
|Host|192.168.1.1|Host name or IP address of your server|
|Port|8096|Connection port, usually 8096 or 8192 if using SSL
|Use SSL|-|Check if your server uses a SSL connection
|API Key|fe6e72be02e04f2586cad47aca9077f9|API Key used to connect
|Name|My Flix|Optional name of you server. This will be used when creating entities or browsing media



_Troubleshoting: in order to detect your Emby or Jellyfin servers, please configure your server firewall to allow UDP incoming packets on port 7359_

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
