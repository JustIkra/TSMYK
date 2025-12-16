"""
Service for extracting metrics from report images using AI Vision.

Implements the improved extraction approach with:
- Enhanced prompt with explicit examples
- Extraction of both labels and values
- Image preprocessing (transparent background to white)
- Validation and normalization
- Mapping labels to MetricDef codes
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_factory import create_ai_client, extract_text_from_response
from app.core.config import settings
from app.db.models import Report, ReportImage
from app.repositories.metric import ExtractedMetricRepository, MetricDefRepository
from app.repositories.participant_metric import ParticipantMetricRepository
from app.services.metric_mapping import get_metric_mapping_service
from app.services.vision_prompts import IMPROVED_VISION_PROMPT

logger = logging.getLogger(__name__)

# Regex for valid metric values: 1-10 with optional single decimal digit
VALUE_PATTERN = re.compile(r"^(?:10|[1-9])(?:[,.][0-9])?$")


@dataclass
class ExtractedMetricData:
    """Extracted metric data before saving to DB."""

    label: str  # Raw label from AI
    value: str  # Raw value from AI
    normalized_label: str  # Normalized label (uppercase, trimmed)
    normalized_value: Decimal  # Parsed decimal value
    confidence: float
    source_image: str  # Image filename for debugging


class MetricExtractionError(Exception):
    """Base error for metric extraction operations."""


class MetricExtractionService:
    """
    Service for extracting metrics from report images using AI Vision.

    Integrates the logic from extract_improved_prompt.py script.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize metric extraction service.

        Args:
            db: Database session
        """
        self.db = db
        self.metric_def_repo = MetricDefRepository(db)
        self.extracted_metric_repo = ExtractedMetricRepository(db)
        self.participant_metric_repo = ParticipantMetricRepository(db)
        self.mapping_service = get_metric_mapping_service()

        # Initialize AI client (auto-selects provider based on settings)
        logger.info(f"Initializing AI client with provider: {settings.ai_provider}")

        self.ai_client = create_ai_client()

        # Delay between requests (in seconds) to avoid rate limits
        self.request_delay = 0.5

        # Image combination limits - optimized for better OCR quality
        self.max_combined_width = 3000  # Reduced to preserve quality
        self.max_combined_height = 32000  # Large limit, will split into up to 12 groups
        self.max_images_per_group = 2  # Fewer images per group = better quality
        self.max_groups = 12  # Up to 12 groups for better extraction
        self.max_image_size_mb = 20  # Gemini Vision limit
        self.image_padding = 30  # Increased padding for better visual separation

    async def extract_metrics_from_report_images(
        self,
        report_id: UUID,
        images: list[ReportImage],
    ) -> dict[str, Any]:
        """
        Extract metrics from all images of a report.

        Args:
            report_id: Report UUID
            images: List of ReportImage instances

        Returns:
            Dict with extraction results:
            {
                "metrics_extracted": int,
                "metrics_saved": int,
                "errors": list[dict],
            }
        """
        logger.info(f"Starting metric extraction for report {report_id}, {len(images)} images")

        all_metrics: list[ExtractedMetricData] = []
        errors = []

        # Get report for participant_id
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError(f"Report not found: {report_id}")

        # Unified mapping: no report_type needed
        logger.info("Using unified metric mapping (no report_type)")

        # Load all metric definitions and create mapping by code
        metric_defs = await self.metric_def_repo.list_all(active_only=True)
        metric_def_by_code = {m.code: m for m in metric_defs}

        logger.info(f"Loaded {len(metric_defs)} active metric definitions")

        # Log optimization: number of requests before optimization
        requests_before_optimization = len(images)
        logger.info(
            f"Image processing optimization: {requests_before_optimization} images, "
            f"will combine into 1-2 requests"
        )

        # Handle edge cases
        if not images:
            logger.warning("No images provided for extraction")
            return {
                "metrics_extracted": 0,
                "metrics_saved": 0,
                "errors": [{"error": "No images provided"}],
            }

        if len(images) == 1:
            # Single image: process directly (no need to combine)
            logger.info("Single image, processing directly")
            img = images[0]
            try:
                image_data = await self._load_image_data(img)
                processed_data = self._preprocess_image(image_data)
                raw_metrics = await self._extract_metrics_with_retry(processed_data, str(img.id))
                logger.info(f"Extracted {len(raw_metrics)} raw metrics from image {img.id}")

                for metric in raw_metrics:
                    try:
                        extracted = self._validate_and_normalize(metric, str(img.id))
                        all_metrics.append(extracted)
                    except ValueError as e:
                        logger.warning(f"Validation failed for metric: {e}")
                        errors.append(
                            {
                                "image_id": str(img.id),
                                "metric": metric,
                                "error": str(e),
                            }
                        )
            except Exception as e:
                logger.error(f"Failed to extract metrics from image {img.id}: {e}")
                errors.append({"image_id": str(img.id), "error": str(e)})
        else:
            # Multiple images: combine and process together
            logger.info(f"Combining {len(images)} images for batch processing")

            try:
                # Load and preprocess all images
                processed_images: list[tuple[Image.Image, str]] = []
                for img in images:
                    try:
                        image_data = await self._load_image_data(img)
                        processed_data = self._preprocess_image(image_data)
                        # Open as PIL Image for combination (copy to avoid closing issues)
                        pil_image = Image.open(io.BytesIO(processed_data))
                        # Convert to RGB to ensure compatibility
                        if pil_image.mode != "RGB":
                            pil_image = pil_image.convert("RGB")
                        # Copy image to avoid file handle issues
                        pil_image = pil_image.copy()
                        processed_images.append((pil_image, str(img.id)))
                    except Exception as e:
                        logger.error(f"Failed to load/preprocess image {img.id}: {e}")
                        errors.append({"image_id": str(img.id), "error": str(e)})

                if not processed_images:
                    logger.error("No images successfully loaded for combination")
                    return {
                        "metrics_extracted": 0,
                        "metrics_saved": 0,
                        "errors": errors,
                    }

                # Combine images into groups (up to 4 groups)
                # Store image IDs for each group
                combined_groups_data: list[tuple[bytes, list[str]]] = []
                combined_groups_bytes = self._combine_images_into_groups(processed_images)

                # Create mapping: group -> list of image IDs in that group
                # Split image IDs evenly across groups
                num_groups = len(combined_groups_bytes)
                num_images = len(processed_images)
                images_per_group = (num_images + num_groups - 1) // num_groups

                for group_idx, group_bytes in enumerate(combined_groups_bytes):
                    start_idx = group_idx * images_per_group
                    end_idx = min(start_idx + images_per_group, num_images)
                    group_ids = [img_id for _, img_id in processed_images[start_idx:end_idx]]
                    combined_groups_data.append((group_bytes, group_ids))

                logger.info(
                    f"Combined {len(processed_images)} images into {len(combined_groups_data)} group(s)"
                )

                # Process each combined group
                for group_idx, (combined_image_data, group_image_ids) in enumerate(
                    combined_groups_data
                ):
                    try:
                        # Extract metrics from combined image
                        image_ids_str = ",".join(group_image_ids)
                        raw_metrics = await self._extract_metrics_with_retry(
                            combined_image_data, f"combined_group_{group_idx + 1}"
                        )

                        logger.info(
                            f"Extracted {len(raw_metrics)} raw metrics from combined group {group_idx + 1}"
                        )

                        # Validate and normalize all metrics
                        for metric in raw_metrics:
                            try:
                                # Use combined image IDs as source
                                extracted = self._validate_and_normalize(
                                    metric, f"combined_images_{image_ids_str}"
                                )
                                all_metrics.append(extracted)
                            except ValueError as e:
                                logger.warning(f"Validation failed for metric: {e}")
                                errors.append(
                                    {
                                        "image_ids": image_ids_str,
                                        "metric": metric,
                                        "error": str(e),
                                    }
                                )
                    except Exception as e:
                        logger.error(f"Failed to extract metrics from combined group {group_idx + 1}: {e}")
                        errors.append(
                            {
                                "group": group_idx + 1,
                                "error": str(e),
                            }
                        )

                # Log optimization results
                requests_after_optimization = len(combined_groups_data)
                logger.info(
                    f"Optimization result: {requests_before_optimization} requests -> "
                    f"{requests_after_optimization} requests "
                    f"({requests_before_optimization - requests_after_optimization} requests saved)"
                )

            except Exception as e:
                logger.error(f"Failed to combine and process images: {e}", exc_info=True)
                errors.append({"error": f"Image combination failed: {str(e)}"})

        # Save extracted metrics to database using YAML mapping
        metrics_saved = 0
        mapping_not_found_count = 0
        metric_def_not_found_count = 0
        unknown_labels = set()

        for metric in all_metrics:
            try:
                # Map label to metric code using unified YAML configuration
                metric_code = self.mapping_service.get_metric_code(metric.normalized_label)

                if not metric_code:
                    logger.warning(
                        f"No mapping found for label '{metric.normalized_label}'"
                    )
                    unknown_labels.add(metric.normalized_label)
                    mapping_not_found_count += 1
                    errors.append(
                        {
                            "label": metric.normalized_label,
                            "error": "mapping_not_found",
                        }
                    )
                    continue

                # Find MetricDef by code
                metric_def = metric_def_by_code.get(metric_code)

                if not metric_def:
                    logger.warning(
                        f"No MetricDef found for code '{metric_code}' "
                        f"(label: '{metric.normalized_label}')"
                    )
                    metric_def_not_found_count += 1
                    errors.append(
                        {
                            "label": metric.normalized_label,
                            "metric_code": metric_code,
                            "error": "metric_def_not_found",
                        }
                    )
                    continue

                # Save to extracted_metric table
                await self.extracted_metric_repo.create_or_update(
                    report_id=report_id,
                    metric_def_id=metric_def.id,
                    value=metric.normalized_value,
                    source="LLM",
                    confidence=Decimal(str(metric.confidence)),
                    notes=f"Extracted from image with improved prompt: {metric.source_image}",
                )

                # Upsert to participant_metric table
                await self.participant_metric_repo.upsert(
                    participant_id=report.participant_id,
                    metric_code=metric_code,
                    value=metric.normalized_value,
                    confidence=Decimal(str(metric.confidence)),
                    source_report_id=report_id,
                )

                metrics_saved += 1
                logger.debug(
                    f"Saved metric: {metric.normalized_label} -> {metric_code} "
                    f"= {metric.normalized_value} (participant_id={report.participant_id})"
                )

            except Exception as e:
                # Distinguish critical (DB-related) vs. non-critical errors
                is_critical = isinstance(e, (DBAPIError, IntegrityError, OperationalError))

                logger.error(
                    f"Failed to save metric {metric.normalized_label}: {e} "
                    f"(critical={is_critical})",
                    exc_info=is_critical,
                )

                errors.append(
                    {
                        "label": metric.normalized_label,
                        "value": str(metric.normalized_value),
                        "error": str(e),
                        "critical": is_critical,
                    }
                )

                # Re-raise critical errors to prevent setting status to EXTRACTED
                # when database operations fail
                if is_critical:
                    logger.error(
                        f"Critical database error while saving metric "
                        f"{metric.normalized_label}, aborting extraction"
                    )
                    raise

        # Log pool statistics (if using pool client)
        if hasattr(self.ai_client, 'get_pool_stats'):
            pool_stats = self.ai_client.get_pool_stats()
            logger.info("=" * 80)
            logger.info("AI API Key Pool Statistics:")
            logger.info(f"  Total keys: {pool_stats.total_keys}")
            logger.info(f"  Healthy keys: {pool_stats.healthy_keys}")
            logger.info(f"  Degraded keys: {pool_stats.degraded_keys}")
            logger.info(f"  Failed keys: {pool_stats.failed_keys}")
            logger.info(f"  Total requests: {pool_stats.total_requests}")
            logger.info(f"  Successful requests: {pool_stats.total_successes}")
            logger.info(f"  Failed requests: {pool_stats.total_failures}")

            # Calculate total rate limit errors from per-key stats
            total_rate_limit_errors = sum(
                key_stat.get("rate_limit_errors", 0) for key_stat in pool_stats.per_key_stats
            )
            logger.info(f"  Rate limited requests: {total_rate_limit_errors}")
            logger.info("=" * 80)

        # Log mapping statistics
        logger.info("=" * 80)
        logger.info("Metric Mapping Statistics:")
        logger.info(f"  Total metrics extracted: {len(all_metrics)}")
        logger.info(f"  Successfully saved: {metrics_saved}")
        logger.info(f"  Mapping not found: {mapping_not_found_count}")
        logger.info(f"  MetricDef not found: {metric_def_not_found_count}")
        logger.info(
            f"  Other errors: {len(errors) - mapping_not_found_count - metric_def_not_found_count}"
        )
        if unknown_labels:
            logger.warning(
                f"  Unknown labels ({len(unknown_labels)}): {sorted(unknown_labels)[:10]}"
            )
            if len(unknown_labels) > 10:
                logger.warning(f"    ... and {len(unknown_labels) - 10} more")
        logger.info("=" * 80)

        logger.info(
            f"Metric extraction complete for report {report_id}: "
            f"{len(all_metrics)} extracted, {metrics_saved} saved, {len(errors)} errors"
        )

        return {
            "metrics_extracted": len(all_metrics),
            "metrics_saved": metrics_saved,
            "errors": errors,
        }

    def _combine_images_into_groups(
        self, processed_images: list[tuple[Image.Image, str]]
    ) -> list[bytes]:
        """
        Combine images into groups based on max_images_per_group limit.
        Images are kept in original quality without resizing.

        Args:
            processed_images: List of (PIL Image, image_id) tuples

        Returns:
            List of combined image bytes (PNG format)
        """
        if not processed_images:
            return []

        # Keep images in original size - no resizing for better OCR quality
        original_images: list[Image.Image] = [img for img, _ in processed_images]

        # Split into groups by max_images_per_group (up to max_groups)
        max_per_group = getattr(self, 'max_images_per_group', 2)
        max_groups = getattr(self, 'max_groups', 6)
        num_images = len(original_images)

        if num_images <= max_per_group:
            # All images fit in one group
            return [self._combine_images_vertically(original_images)]

        # Calculate number of groups needed (up to max_groups)
        num_groups = min(max_groups, (num_images + max_per_group - 1) // max_per_group)
        images_per_group = (num_images + num_groups - 1) // num_groups

        logger.info(
            f"Splitting {num_images} images into {num_groups} groups "
            f"(~{images_per_group} images per group, original quality)"
        )

        combined_groups = []
        for i in range(num_groups):
            start_idx = i * images_per_group
            end_idx = min(start_idx + images_per_group, num_images)
            group_images = original_images[start_idx:end_idx]
            if group_images:
                combined_groups.append(self._combine_images_vertically(group_images))

        return combined_groups

    def _combine_images_vertically(self, images: list[Image.Image]) -> bytes:
        """
        Combine images vertically with padding on white background.
        Images are kept in original quality without compression.

        Args:
            images: List of PIL Images to combine

        Returns:
            Combined image bytes (PNG format)
        """
        if not images:
            raise ValueError("No images to combine")

        if len(images) == 1:
            # Single image - ensure white background
            img = images[0]
            if img.mode in ("RGBA", "LA", "P"):
                img = self._ensure_white_background(img)
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()

        # Calculate dimensions
        max_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        total_height += self.image_padding * (len(images) - 1)

        # Create combined image with white background
        combined = Image.new("RGB", (max_width, total_height), (255, 255, 255))

        # Paste images vertically with padding
        y_offset = 0
        for img in images:
            # Ensure white background for transparent images
            if img.mode in ("RGBA", "LA", "P"):
                img = self._ensure_white_background(img)
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Center image horizontally if narrower than max_width
            x_offset = (max_width - img.width) // 2
            combined.paste(img, (x_offset, y_offset))
            y_offset += img.height + self.image_padding

        # Save to bytes - no compression, original quality
        output = io.BytesIO()
        combined.save(output, format="PNG")
        combined_bytes = output.getvalue()

        # Log size info (no compression even if large)
        size_mb = len(combined_bytes) / (1024 * 1024)
        logger.info(f"Combined image size: {size_mb:.2f}MB ({max_width}x{total_height}px)")

        return combined_bytes

    def _ensure_white_background(self, img: Image.Image) -> Image.Image:
        """
        Convert image with transparency to RGB with white background.

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

    async def _load_image_data(self, img: ReportImage) -> bytes:
        """Load image data from storage."""
        # Import here to avoid circular dependency
        from app.services.storage import LocalReportStorage

        storage = LocalReportStorage(settings.file_storage_base)
        image_path = storage.resolve_path(img.file_ref.key)

        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        return image_path.read_bytes()

    def _preprocess_image(self, image_data: bytes) -> bytes:
        """
        Preprocess image: convert transparent background to white.

        Args:
            image_data: Original image bytes

        Returns:
            Processed image bytes (PNG)
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

    async def _extract_metrics_with_retry(
        self,
        image_data: bytes,
        image_name: str,
        max_retries: int = 3,
    ) -> list[dict[str, str]]:
        """
        Extract metrics with exponential backoff retry on 503 errors.

        Args:
            image_data: Image bytes (PNG)
            image_name: Image filename for logging
            max_retries: Maximum retry attempts

        Returns:
            List of dicts with 'label' and 'value' keys
        """
        for attempt in range(max_retries):
            try:
                return await self._extract_metrics_with_labels(image_data)
            except Exception as e:
                error_str = str(e)

                # Check if it's a 503 error
                if "503" in error_str or "Service Unavailable" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2^attempt seconds
                        delay = 2**attempt
                        logger.warning(
                            f"503 error for {image_name}, retrying in {delay}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for {image_name}: {e}")
                        raise
                else:
                    # Non-503 error, don't retry
                    logger.error(f"Non-retryable error for {image_name}: {e}")
                    raise

        return []

    async def _extract_metrics_with_labels(self, image_data: bytes) -> list[dict[str, str]]:
        """
        Extract metrics with labels using Gemini Vision API.

        Args:
            image_data: Image bytes (PNG)

        Returns:
            List of dicts with 'label' and 'value' keys
        """
        response = await self.ai_client.generate_from_image(
            prompt=IMPROVED_VISION_PROMPT,
            image_data=image_data,
            mime_type="image/png",
            response_mime_type="application/json",
            timeout=60,
        )

        # Parse response (handles both Gemini and OpenRouter formats)
        try:
            text = extract_text_from_response(response)
            logger.debug(f"AI Vision raw response text: {text[:2000] if len(text) > 2000 else text}")
            data = json.loads(text)
            logger.debug(f"Parsed JSON keys: {list(data.keys())}")
            metrics = data.get("metrics", [])

            if not isinstance(metrics, list):
                logger.warning(f"Response 'metrics' is not a list: {type(metrics)}")
                return []

            return metrics

        except (KeyError, json.JSONDecodeError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            return []

    def _validate_and_normalize(
        self, metric: dict[str, str], source_image: str
    ) -> ExtractedMetricData:
        """
        Validate and normalize extracted metric.

        Args:
            metric: Dict with 'label' and 'value'
            source_image: Source image identifier

        Returns:
            ExtractedMetricData with normalized values

        Raises:
            ValueError: If validation fails
        """
        label = metric.get("label", "").strip()
        value = metric.get("value", "").strip()

        if not label or not value:
            raise ValueError(f"Empty label or value: {metric}")

        # Validate value format
        if not VALUE_PATTERN.match(value):
            raise ValueError(f"Invalid value format: {value}")

        # Normalize label (uppercase)
        normalized_label = label.upper()

        # Parse value (replace comma with dot)
        value_normalized = value.replace(",", ".")
        try:
            decimal_value = Decimal(value_normalized)
        except Exception as e:
            raise ValueError(f"Failed to parse value '{value}': {e}") from e

        # Validate range [1, 10]
        if not (Decimal("1") <= decimal_value <= Decimal("10")):
            raise ValueError(f"Value out of range [1, 10]: {decimal_value}")

        return ExtractedMetricData(
            label=label,
            value=value,
            normalized_label=normalized_label,
            normalized_value=decimal_value,
            confidence=1.0,  # Default confidence for improved prompt
            source_image=source_image,
        )

    async def close(self):
        """Close resources."""
        await self.ai_client.close()
