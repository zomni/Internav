# Entity Specifications

## Organization
id
name
code
description

## Site
organization_id
name
timezone
address

## Building
site_id
name
code

## Floor
building_id
name
level
display_order

## FloorPlan
floor_id
image_path
width
height
scale

## Grid
floor_id
name
cell_size
status

## Cell
grid_id
row
column
center_x
center_y
walkable

## Campaign
floor_id
name
status
started_at
finished_at

## Fingerprint
campaign_id
cell_id
captured_at
device_id
sample_number
orientation
notes

## AccessPointObservation
fingerprint_id
bssid
ssid
rssi
frequency

## Dataset
version

## DatasetCampaign
dataset_id
campaign_id

## ModelVersion
dataset_id
algorithm
version
status
published_at