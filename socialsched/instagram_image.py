import os
import io
import uuid
import textwrap
from PIL import Image, ImageDraw, ImageFont
from core.logger import log, send_notification
from core.settings import MEDIA_ROOT


def resize_image(image_path: str, target_width: int = 1080):
    img = Image.open(image_path)

    # Calculate new height to maintain aspect ratio
    original_width, original_height = img.size
    aspect_ratio = original_height / original_width
    new_height = int(target_width * aspect_ratio)

    # Resize the image
    resized_img = img.resize((target_width, new_height), Image.LANCZOS)
    resized_img.save(image_path)

    return image_path


def compress_image(image_path: str, quality: int = 75):
    img = Image.open(image_path)

    # Determine optimal format and extension
    img_format = img.format if img.format else "JPEG"

    min_quality = 20  # Don't go below this quality
    max_quality = 95
    target_size = 300000  # 300kb

    if img_format == "JPEG":
        # Binary search for optimal quality
        current_quality = quality  # Start with good quality
        min_q, max_q = min_quality, max_quality

        for _ in range(10):  # Max 10 iterations to find optimal quality
            img_byte_arr = io.BytesIO()
            img.save(
                img_byte_arr,
                format=img_format,
                optimize=True,
                quality=current_quality,
                progressive=True,
            )
            current_size = img_byte_arr.tell()

            if current_size <= target_size:
                # Try with higher quality
                min_q = current_quality
            else:
                # Try with lower quality
                max_q = current_quality

            # Next quality to try
            previous_quality = current_quality
            current_quality = (min_q + max_q) // 2

            # Stop if we're not making progress
            if current_quality == previous_quality:
                break

        img.save(
            image_path,
            format=img_format,
            optimize=True,
            quality=current_quality,
            progressive=True,
        )

    elif img_format == "PNG":
        # For PNG, try quantizing colors if needed
        img.save(image_path, format=img_format, optimize=True, compress_level=9)

        if os.path.getsize(image_path) > target_size:
            # Try color quantization for PNG
            if img.mode != "P":
                # Convert to palette mode with dithering for better quality
                img = img.convert("P", palette=Image.ADAPTIVE, colors=256)
                img.save(image_path, format=img_format, optimize=True, compress_level=9)

            # If still too large, reduce colors further
            if os.path.getsize(image_path) > target_size:
                for colors in [128, 64, 32]:
                    img = Image.open(image_path).convert(
                        "P", palette=Image.ADAPTIVE, colors=colors
                    )
                    img.save(
                        image_path,
                        format=img_format,
                        optimize=True,
                        compress_level=9,
                    )
                    if os.path.getsize(image_path) <= target_size:
                        break

    return image_path


def create_image_from_text(
    text: str,
    image_path: str = None,
    width: int = 1080,
    font_size: int = 40,
    padding: int = 40,
    background_color: str = "black",
    text_color: str = "white",
):

    if image_path is None:
        image_path = os.path.join(MEDIA_ROOT, f"{uuid.uuid4()}.png")

    font = None
    try:
        common_fonts = [
            "Roboto-Regular.ttf",
            "Arial.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
            "FreeSans.ttf",
            "Verdana.ttf",
            "verdana.ttf",
        ]

        for font_name in common_fonts:
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except IOError:
                continue

    except Exception:
        pass

    if font is None:
        font = ImageFont.load_default(size=font_size)

    # Calculate how much space we have for text
    text_width = width - (2.3 * padding)

    # Wrap text to fit width
    lines = textwrap.wrap(text, width=int(text_width / (font_size * 0.5)))

    # Calculate height based on number of lines
    line_height = font_size * 1.5
    text_height = len(lines) * line_height
    height = int(text_height + (2 * padding))

    # Create image
    image = Image.new("RGB", (width, height), color=background_color)
    draw = ImageDraw.Draw(image)

    # Draw text
    y_position = padding
    for line in lines:
        draw.text((padding, y_position), line, font=font, fill=text_color)
        y_position += line_height

    image.save(image_path)

    return image_path


def concat_image_vertically(
    image_path: str, top_image_path: str, bottom_image_path: str
):
    top_img = Image.open(top_image_path)
    bottom_img = Image.open(bottom_image_path)

    # Create a new image with the height being the sum of both images' heights
    combined_height = top_img.height + bottom_img.height
    combined_img = Image.new("RGB", (top_img.width, combined_height))

    # Paste the first image at the top
    combined_img.paste(top_img, (0, 0))

    # Paste the second image below the first one
    combined_img.paste(bottom_img, (0, top_img.height))

    combined_img.save(image_path)
    return image_path


def create_image(*, image_path: str = None, text: str = None):
    if image_path and not text:
        resized_image_path = resize_image(image_path)
        compressed_image_path = compress_image(resized_image_path)
        return compressed_image_path

    if text and not image_path:
        text_image_path = create_image_from_text(text)
        return text_image_path

    if text and image_path:
        text_image_path = create_image_from_text(text)
        resized_image_path = resize_image(image_path)
        concated_image_path = concat_image_vertically(
            image_path=image_path,
            top_image_path=text_image_path,
            bottom_image_path=resized_image_path,
        )
        os.remove(text_image_path)
        compressed_image_path = compress_image(concated_image_path)
        return compressed_image_path

    raise Exception("Image, text or both must be provided!")


def make_instagram_image(image_path: str = None, text: str = None):
    try:
        created_image_path = create_image(image_path=image_path, text=text)
        return os.path.basename(created_image_path)
    except Exception as err:
        log.exception(err)
        send_notification(email="ImPosting", message=str(err))
        return image_path
