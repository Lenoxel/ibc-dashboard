from abc import ABC, abstractmethod


class ImageStorageProvider(ABC):
    @abstractmethod
    def upload_image(self, image_data: bytes) -> str:
        """
        Uploads an image to the storage provider.

        :param image_data: The binary data of the image.
        :return: The URL or identifier of the uploaded image.
        """
        pass
