<p align="center">
  <img src="https://raw.githubusercontent.com/Desi-Smart-RD/desi-home-assistant/master/custom_components/desi/brand/logo.png" width="120" alt="Desi Logo">
</p>

# Desi Smart Integration for Home Assistant

<p align="center">
  <a href="https://github.com/hacs/integration">
    <img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge" alt="HACS Custom">
  </a>
  <img src="https://img.shields.io/badge/Home%20Assistant-Compatible-blue.svg?style=for-the-badge&logo=home-assistant" alt="Home Assistant">
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="License MIT" />
</p>

This custom integration allows you to control and monitor your **Desi Alarm** and **Desi Smart Lock** systems directly from Home Assistant. Automate your home security and keep your peace of mind in one central dashboard.


## Features

- **Alarm Control Panel:** Arm (Away/Home) and Disarm your Desi alarm system.
- **Smart Lock:** Securely lock or unlock your Desi smart doors.
- **Door Status** If auto-closer is lined your smart lock you can know your door status opened or closed.
- **Smart Relays:** Control additional Desi modules and features.
- **Real-time Status:** Monitor door and alarm states instantly.


## Installation

### Method: HACS (Custom Repository)

[![](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Desi-Smart-RD&repository=desi-home-assistant&category=Integration)

1.  Navigate to **HACS** in your Home Assistant sidebar.
2.  Click the **three dots** in the top-right corner and select **Custom repositories**.
3.  **Repository:** `https://github.com/Desi-Smart-RD/desi-home-assistant.git`
4.  **Category:** Select `Integration` and click **Add**.
5.  Search for "Desi Smart" in HACS, click **Download**, and **Restart Home Assistant.**


##  Configuration

This integration is configured entirely via the Home Assistant UI (Config Flow). No YAML editing required:

1.  Go to **Settings** -> **Devices & Services**.
2.  Click **Add Integration** in the bottom right.
3.  Search for **"Desi Smart"**.
4.  Enter your Desi Login Web credentials to authenticate.
5.  Create an pin code for device control. Home Assistant will be ask before unlocking and disarm operations.


## Compatible Devices

| Device Name | Device Type |
| ----------- | ----------- |
| Utopic R    | AD Series         |
| Utopic R+   | ✓           |
| Utopic RX   | ✓           |
| Utopic RXe  | ✓           |
| Auto Closer | V3BL        |


##  Important Notes

> [!WARNING]  
> **Cloud Dependency:** This integration requires your Desi Smart system to be connected to the internet and cloud services to be active. It relies on the cloud API to communicate with your locks.

> [!CAUTION]  
> **Door Status:** Door Status is only available for locks with an auto-closer (V3BL) connected. If no auto-closer is connected, the door status will be shown as Unknown by default. Once an auto-closer is connected, the actual door state will be displayed as Opened or Closed.



##  Screenshots

<img src="https://raw.githubusercontent.com/Desi-Smart-RD/desi-home-assistant/master/custom_components/desi/assests/ha-images/home-page.png" width="650"> <img src="https://raw.githubusercontent.com/Desi-Smart-RD/desi-home-assistant/master/custom_components/desi/assests/ha-images/device-list.png" width="650"> 



##  Support and Contribution

If you experience any issues, please send an email to **[bilgi@desi.com.tr](mailto:bilgi@desi.com.tr)**, and our support team will assist you.


