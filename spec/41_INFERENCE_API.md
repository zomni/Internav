# Inference API

POST /inference

Input
- observations[]

Output
- predicted_cell
- confidence
- candidate_cells[]
- model_version
- inference_time_ms

The model predicts Cells, never coordinates.
Coordinates are resolved by the application using Cell metadata.