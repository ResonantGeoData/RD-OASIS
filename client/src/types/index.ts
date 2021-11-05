export interface Paginated<T> {
  count: number;
  next: string;
  previous: string;
  results: T[];
}

export interface Model {
  id: number;
  created: string;
  modified: string;
}

export interface DockerImage extends Model {
  name: string;
  image_id: string | null;
  image_file: number | null;
}

export interface Algorithm extends Model {
  name: string;
  environment: {[key: string]: string};
  command: string;
  entrypoint: string | null;
  gpu: boolean;
  docker_image: number;
  input_dataset: number[];
}

export interface Task extends Model {
  status: 'created' | 'queued' | 'running' | 'failed' | 'success';
  algorithm: number;
}

export interface ChecksumFile extends Model {
  name: string;
  description: string | null;
  status: 'created' | 'queued' | 'running' | 'failed' | 'success' | 'skipped';
  file: string;
  url: string;
  download_url: string;
  type: 1 | 2;
  failure_reason: string | null;
  checksum: string;
  validate_checksum: boolean;
  last_validation: boolean;
  collection: number | null;
  created_by: number | null;
}
