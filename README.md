<p align="center">
  <img src="https://raw.githubusercontent.com/Desi-Smart-RD/desi-home-assistant/master/custom_components/desi/brand/logo.png" width="120" alt="Desi Logo">
</p>

# Desi Smart Integration for Home Assistant
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![version](https://img.shields.io/github/v/release/Desi-Smart-RD/desi-home-assistant?style=for-the-badge)](https://github.com/Desi-Smart-RD/desi-home-assistant/releases/tag/v1.0.2)

This custom integration allows you to control and monitor your **Desi Alarm** and **Desi Smart Lock** systems directly from Home Assistant. Automate your home security and keep your peace of mind in one central dashboard.

---

## ✨ Features

- **🚨 Alarm Control Panel:** Arm (Away/Home) and Disarm your Desi alarm system.
- **🔐 Smart Lock:** Securely lock or unlock your Desi smart doors.
- **⚡ Smart Relays:** Control additional Desi modules and features.
- **📱 Real-time Status:** Monitor door and alarm states instantly.

---

## 🚀 Installation

### HACS

While this integration is pending official HACS inclusion, you can add it as a custom repository:

1.  Navigate to **HACS** in your Home Assistant sidebar.
2.  Click the **three dots** in the top-right corner and select **Custom repositories**.
3.  **Repository:** `https://github.com/Desi-Smart-RD/desi-home-assistant.git`
4.  **Category:** Select `Integration` and click **Add**.
5.  Search for "Desi Smart" in HACS, click **Download**, and **Restart Home Assistant.**


## ⚙️ Configuration

This integration is configured entirely via the Home Assistant UI (Config Flow). No YAML editing required:

1.  Go to **Settings** -> **Devices & Services**.
2.  Click **Add Integration** in the bottom right.
3.  Search for **"Desi Smart"**.
4.  Enter your Desi Login Web credentials to authenticate.

## 🔒 Compatible Devices

COMPATIBLE WITH Utopic R (Device Type AD), Utopic R+, Utopic RX, and Utopic RXe.

## 📸 Screenshots

<img src="https://raw.githubusercontent.com/Desi-Smart-RD/desi-home-assistant/master/custom_components/desi/assests/ha-images/home-page.png" width="650"> <img src="https://raw.githubusercontent.com/Desi-Smart-RD/desi-home-assistant/master/custom_components/desi/assests/ha-images/device-list.png" width="650"> 

---

## ⚠️ Important Notes

- **Cloud Dependency:** This integration requires your Desi system to be connected to the internet and cloud services to be active.

---

## 🤝 Support and Contribution

If you encounter any bugs or have feature requests, please feel free to open an [Issue](https://github.com/Desi-Smart-RD/desi-home-assistant.git).

