# AccessPointObservation

Resource: /observations

Fields
- fingerprint_id
- bssid
- ssid
- rssi
- frequency
- channel
- band
- security

Rules
- RSSI in dBm.
- BSSID normalized.
- Duplicate BSSID entries are merged during preprocessing.