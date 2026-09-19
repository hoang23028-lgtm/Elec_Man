export type Batch = {
  id: string;
  batch_code: string;
  original_folder_name: string;
  status: string;
  total_images: number;
  uploaded_images: number;
  processed_images: number;
  review_count: number;
  ok_count: number;
  ng_count: number;
  failed_count: number;
  created_at: string;
};
export type BatchImage = {
  image_id: string;
  original_filename: string;
  image_status: string;
  width: number;
  height: number;
  file_size: number;
  created_at: string;
  customer_id_ai: string | null;
  meter_reading_ai: string | null;
  final_confidence: number | null;
  review_status: string | null;
  final_customer_id: string | null;
  final_meter_reading: string | null;
};
export type UploadProgress = {
  total: number;
  uploaded: number;
  failed: number;
};
