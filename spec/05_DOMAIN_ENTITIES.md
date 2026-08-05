# Core Entities

## Organization
Top-level owner of the platform data.

## Site
A physical campus or location.

## Building
A physical building inside a site.

## Floor
A level inside a building.

## FloorPlan
Image representing the floor layout.

## Grid
Logical partition of a floor.

## Cell
Smallest positioning unit.

## Campaign
Collection session for fingerprints.

## Fingerprint
One WiFi scan associated with a cell.

## AccessPointObservation
Single AP observation inside one fingerprint.

## Dataset
Immutable training input, built from one or more Campaigns.

## ModelVersion
Versioned trained positioning model.

## User
Account with access to the platform.

Roles
- Administrator
- Operator
- Viewer

A User belongs to one Organization and acts as the `created_by` / `updated_by` reference on auditable entities.