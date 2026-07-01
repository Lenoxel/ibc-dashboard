from app.image_storage_provider import ImageStorageProvider

import cloudinary, cloudinary.uploader


class CloudinaryImageStorageProvider(ImageStorageProvider):
    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

    def upload_image(self, image_bytes: bytes) -> str:
        try:
            upload_result = cloudinary.uploader.upload(
                image_bytes,
                folder="member_photos",
                resource_type="image",
                overwrite=True,
            )

            if "version" in upload_result and "public_id" in upload_result:
                img_format = upload_result.get("format", "jpg")
                return f"image/upload/v{upload_result['version']}/{upload_result['public_id']}.{img_format}"

            return upload_result.get("secure_url")
        except Exception as e:
            print(f"Error uploading to Cloudinary: {e}")
            return None
