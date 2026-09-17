# Image storage and uploads

Images are stored as server-generated UUID filenames below `STORAGE_ROOT`; the original filename is metadata only. The storage volume is not web-served. Preview access always goes through an authenticated API endpoint.

Each upload is one controlled HTTP request. The backend checks extension, supplied MIME type, file signature, safe Pillow decoding, decoded format, dimensions, pixel count, and configured size. It calculates SHA-256 while streaming to disk and rejects exact duplicates in the same batch. Thumbnails are generated separately; originals are never modified.
