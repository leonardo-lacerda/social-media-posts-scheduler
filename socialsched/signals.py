import time
from core.logger import log, send_notification
from PIL import Image, ImageOps
from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import PostModel


def make_image_for_instagram(src_img: str, dst_img: str = None):

    try:
        start = time.perf_counter()

        image = Image.open(src_img)

        if dst_img is None:
            dst_img = src_img

        if image.mode != "RGB":
            image = image.convert("RGB")

        MAX_WIDTH = 1080
        MAX_HEIGHT = 1350

        # Calculate resize ratio
        ratio = min(MAX_WIDTH / image.width, MAX_HEIGHT / image.height, 1)

        # Resize image if necessary
        if ratio < 1:
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.LANCZOS)
            log.debug(f"Resized image to: {image.width}x{image.height}")

        # Check aspect ratio for Instagram (between 4:5 and 1.91:1)
        aspect_ratio = image.width / image.height
        min_aspect = 4 / 5  # 0.8
        max_aspect = 1.91  # ~1.91

        if not (min_aspect <= aspect_ratio <= max_aspect):
            # Pad to closest valid aspect ratio (centered with white background)
            desired_width = image.width
            desired_height = image.height

            if aspect_ratio < min_aspect:
                # Too tall, need to pad width
                desired_width = int(image.height * min_aspect)
            elif aspect_ratio > max_aspect:
                # Too wide, need to pad height
                desired_height = int(image.width / max_aspect)

            log.debug(
                f"Padding to {desired_width}x{desired_height} for valid aspect ratio"
            )
            image = ImageOps.pad(
                image,
                (desired_width, desired_height),
                color=(255, 255, 255),
                centering=(0.5, 0.5),
            )

        # Save the final image
        image.save(dst_img, quality=95)  # Save as high quality

        log.debug(
            f"Saved Instagram-ready image as {dst_img}! Took {time.perf_counter() - start:.2f} seconds."
        )

        return dst_img
    except Exception as err:
        log.error(err)
        log.exception(err)
        send_notification("ImPosting", "Failed to make image for Instagram.")
        return src_img


@receiver(post_save, sender=PostModel)
def process_media_file_for_instagram(sender, instance, created, **kwargs):
    if instance.media_file and hasattr(instance.media_file, "path"):
        make_image_for_instagram(instance.media_file.path)
