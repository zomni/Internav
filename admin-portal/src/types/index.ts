export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  organization_id: string | null;
  created_at: string;
  updated_at: string;
}

export type UserRole = 'Administrator' | 'Operator' | 'Viewer';

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse extends AuthTokens {
  user: User;
}

export interface Organization {
  id: string;
  name: string;
  code: string;
  description: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface Site {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  timezone: string;
  address: string | null;
  metadata: Record<string, string> | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface Building {
  id: string;
  site_id: string;
  name: string;
  code: string;
  description: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface Floor {
  id: string;
  building_id: string;
  name: string;
  level: number;
  display_order: number;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface FloorPlan {
  id: string;
  floor_id: string;
  image_path: string;
  width: number;
  height: number;
  scale: number;
  checksum: string;
  mime_type: string;
  version: number;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface Grid {
  id: string;
  floor_id: string;
  name: string;
  cell_size: number;
  status: GridStatus;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export type GridStatus = 'Draft' | 'Active' | 'Locked';

export interface Cell {
  id: string;
  grid_id: string;
  row: number;
  column: number;
  center_x: number;
  center_y: number;
  walkable: boolean;
}

export interface Campaign {
  id: string;
  floor_id: string;
  name: string;
  status: CampaignStatus;
  started_at: string | null;
  finished_at: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export type CampaignStatus = 'Draft' | 'Ready' | 'Collecting' | 'Paused' | 'Completed' | 'Archived';

export interface Dataset {
  id: string;
  name: string;
  status: DatasetStatus;
  fingerprint_count: number;
  observation_count: number;
  floor_count: number;
  metadata: Record<string, string> | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export type DatasetStatus = 'Draft' | 'Building' | 'Ready' | 'Archived';

export interface ModelVersion {
  id: string;
  dataset_id: string;
  floor_id: string;
  algorithm: string;
  version: number;
  status: ModelStatus;
  hyperparameters: Record<string, number> | null;
  metrics: Record<string, number> | null;
  training_time: number | null;
  checksum: string | null;
  published_at: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export type ModelStatus = 'Training' | 'Failed' | 'Ready' | 'Published' | 'Archived';

export interface Fingerprint {
  id: string;
  campaign_id: string;
  cell_id: string;
  observations: AccessPointObservation[];
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AccessPointObservation {
  bssid: string;
  ssid: string | null;
  rssi: number;
  frequency: number;
}

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  message: string;
  errors: string[];
  metadata: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
