# Feature Engineering

Input

- BSSID
- RSSI
- Frequency
- Channel

Pipeline

1. Normalize BSSID
2. Remove duplicates
3. Handle missing APs
4. Vectorize observations
5. Normalize RSSI
6. Persist feature metadata

The feature pipeline must be versioned independently.