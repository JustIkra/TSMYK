"""
Utility functions for image preprocessing.

Common image manipulation operations used by metric extraction services.
Handles transparency, background replacement, and format conversion.
"""

from __future__ import annotations

import io

from PIL import Image


def ensure_white_background(img: Image.Image) -> Image.Image:
    """
    Convert image with transparency to RGB with white background.

    Handles various image modes:
    - RGBA: Composites on white background
    - LA: Grayscale with alpha -> composites on white
    - P: Palette mode -> checks for transparency, converts appropriately

    Args:
        img: PIL Image (may have transparency)

    Returns:
        RGB image with white background
    """
    if img.mode == "P":
        if "transparency" in img.info:
            img = img.convert("RGBA")
        else:
            return img.convert("RGB")

    if img.mode in ("RGBA", "LA"):
        # Create white background
        white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        if img.mode == "LA":
            # Convert LA to RGBA
            rgba_img = img.convert("RGBA")
            img = rgba_img
        # Composite on white background
        return Image.alpha_composite(white_bg, img).convert("RGB")

    return img.convert("RGB") if img.mode != "RGB" else img


def preprocess_image(image_data: bytes) -> bytes:
    """
    Preprocess image: convert transparent background to white, output as PNG.

    Handles transparent backgrounds by compositing on white:
    - RGBA images
    - LA (grayscale with alpha) images
    - Palette images with transparency

    Args:
        image_data: Original image bytes (any supported format)

    Returns:
        Processed image bytes in PNG format with RGB mode
    """
    with Image.open(io.BytesIO(image_data)) as img:
        # Handle transparent background: convert to white
        if img.mode in ("RGBA", "LA", "P"):
            # Handle palette mode with transparency
            if img.mode == "P":
                # Check if has transparency
                if "transparency" in img.info:
                    # Convert to RGBA first
                    img = img.convert("RGBA")
                else:
                    # No transparency, just convert to RGB
                    img = img.convert("RGB")

            # If still has alpha channel, composite on white background
            if img.mode in ("RGBA", "LA"):
                # Create white background in RGBA mode
                white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))

                # Convert image to RGBA if needed
                if img.mode == "LA":
                    # LA (grayscale with alpha) -> RGBA
                    rgba_img = Image.new("RGBA", img.size)
                    rgba_img.paste(img.convert("L"), (0, 0))
                    # Copy alpha channel
                    alpha = img.split()[1]
                    rgba_img.putalpha(alpha)
                    img = rgba_img
                elif img.mode != "RGBA":
                    img = img.convert("RGBA")

                # Composite image on white background
                img = Image.alpha_composite(white_bg, img).convert("RGB")
            else:
                # Already RGB
                img = img.convert("RGB")
        elif img.mode not in ("RGB", "L"):
            # Convert other modes to RGB
            img = img.convert("RGB")

        # Save to PNG
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
