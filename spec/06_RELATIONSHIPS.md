# Relationships

Organization 1..* Site

Site 1..* Building

Building 1..* Floor

Floor 1..1 FloorPlan

Floor 1..* Grid

Grid 1..* Cell

Floor 1..* Campaign

Campaign 1..* Fingerprint

Fingerprint 1..* AccessPointObservation

Campaign -> Dataset

Dataset -> ModelVersion