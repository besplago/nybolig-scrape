import tensorflow as tf
import tensorflow_hub as hub
import matplotlib.pyplot as plt
import numpy as np
import PIL.Image
import os
from tqdm import tqdm
import cv2

STYLE_IMAGE = "./starry_night.jpg"
CONTENT_IMAGES = "./output/part_1"
OUTPUT_FOLDER_PATH = "./output/stylized_part_1"
IMAGE_SIZE = 448


def load_img(path_to_img: str) -> tf.Tensor:
    max_dim = IMAGE_SIZE
    img = tf.io.read_file(path_to_img)
    img = tf.image.decode_image(img, channels=3)
    img = tf.image.convert_image_dtype(img, tf.float32)

    shape = tf.cast(tf.shape(img)[:-1], tf.float32)
    long_dim = max(shape)
    scale = max_dim / long_dim

    new_shape = tf.cast(shape * scale, tf.int32)

    img = tf.image.resize(img, new_shape)
    img = img[tf.newaxis, :]
    return img


def tensor_to_image(tensor: tf.Tensor) -> PIL.Image:
    tensor = tensor * 255
    tensor = np.array(tensor, dtype=np.uint8)
    if np.ndim(tensor) > 3:
        assert tensor.shape[0] == 1
        tensor = tensor[0]
    return PIL.Image.fromarray(tensor)


def stylize_image(content_path: str, style_path: str) -> tf.Tensor:
    """Stylize the image by applying the style of the style image to the content image"""
    content_image = load_img(content_path)
    style_image = load_img(style_path)

    hub_model = hub.load(
        "https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2"
    )
    stylized_image = hub_model(tf.constant(content_image), tf.constant(style_image))[0]
    return stylized_image


def cartoonize(content_path: str):
    """Cartoonize the image"""
    content_image: np.ndarray = cv2.imread(content_path)
    gray = cv2.cvtColor(content_image, cv2.COLOR_BGR2GRAY)
    blurImage = cv2.medianBlur(content_image, 1)

    edges = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9
    )

    color = cv2.bilateralFilter(content_image, 9, 200, 200)

    cartoon = cv2.bitwise_and(color, color, mask=edges)

    return cartoon


def color_filter(content_path: str, color: tuple):
    """Apply color filter to the image"""
    content_image: np.ndarray = cv2.imread(content_path)

    # Filter the image
    content_image[:, :, 2] = content_image[:, :, 2] * color[0]  # Red channel
    content_image[:, :, 1] = content_image[:, :, 1] * color[1]  # Green channel
    content_image[:, :, 0] = content_image[:, :, 0] * color[2]  # Blue channel

    return content_image


if __name__ == "__main__":
    if not os.path.exists(OUTPUT_FOLDER_PATH):
        os.makedirs(OUTPUT_FOLDER_PATH)

    for content_image in tqdm(
        os.listdir(CONTENT_IMAGES),
        desc="Stylizing images",
        unit="image",
    ):
        if not os.path.exists(f"{OUTPUT_FOLDER_PATH}/{content_image}"):
            os.makedirs(f"{OUTPUT_FOLDER_PATH}/{content_image}")
        content_path: str = f"{CONTENT_IMAGES}/{content_image}/0.jpg"

        red: tuple = (1, 0, 0)
        stylized_image = color_filter(content_path, red)
        cv2.imwrite(f"{OUTPUT_FOLDER_PATH}/{content_image}/0.jpg", stylized_image)

        # stylized_image = cartoonize(content_path)
        # cv2.imwrite(f"{OUTPUT_FOLDER_PATH}/{content_image}/0.jpg", stylized_image)

        # stylized_image = stylize_image(
        #     f"{CONTENT_IMAGES}/{content_image}/0.jpg",
        #     STYLE_IMAGE,
        # )
        # tensor_to_image(stylized_image).save(
        #     f"{OUTPUT_FOLDER_PATH}/{content_image}/0.jpg"
        # )
        for file in os.listdir(f"{CONTENT_IMAGES}/{content_image}"):
            if file != "0.jpg":
                os.system(
                    f"cp {CONTENT_IMAGES}/{content_image}/{file} {OUTPUT_FOLDER_PATH}/{content_image}"
                )

    print("All images stylized successfully!")
