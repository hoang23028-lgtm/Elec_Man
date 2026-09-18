export type Batch = {
  id: string;
  batch_code: string;
  original_folder_name: string;
  status: string;
  total_images: number;
  uploaded_images: number;
  processed_images: number;
  review_count: number;
  failed_count: number;
  created_at: string;
};
export type UploadProgress = {
  total: number;
  uploaded: number;
  failed: number;
};
