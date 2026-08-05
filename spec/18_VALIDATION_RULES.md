# Validation Rules

Organization
- name length 3..120
- code uppercase

Site
- timezone required

Building
- code required

Floor
- level integer

Grid
- cell_size > 0

Cell
- center_x >= 0
- center_y >= 0

Fingerprint
- minimum one observation

Observation
- RSSI between -100 and 0
- BSSID normalized

Model
- algorithm required