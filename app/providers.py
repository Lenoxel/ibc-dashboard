from app.image_storage_provider import ImageStorageProvider
from app.cloudinary_provider import CloudinaryImageStorageProvider
import streamlit as st

image_storage_provider: ImageStorageProvider = CloudinaryImageStorageProvider(
    cloud_name=st.secrets["cloudinary"]["cloud_name"],
    api_key=st.secrets["cloudinary"]["api_key"],
    api_secret=st.secrets["cloudinary"]["api_secret"],
)
