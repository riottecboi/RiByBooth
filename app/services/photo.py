from PIL import Image, ImageDraw, ImageFont
import base64
import io
import os
import uuid
from datetime import datetime
from typing import List
from app.config import settings
from app.models.session import LayoutType, OrientationType


class PhotoService:
    def create_collage(self, photos: List[str], layout: LayoutType, orientation: OrientationType) -> str:
        if not photos:
            raise ValueError("No photos provided")
        pil_images = []
        for photo_b64 in photos:
            img_data = base64.b64decode(photo_b64)
            img = Image.open(io.BytesIO(img_data))
            pil_images.append(img)

        print(f"Creating collage with {len(pil_images)} images for layout: {layout}, orientation: {orientation}")

        if layout == LayoutType.double:
            final_img = self._create_double_layout(pil_images, orientation)
        elif layout == LayoutType.quad:
            final_img = self._create_quad_layout(pil_images, orientation)
        elif layout == LayoutType.strip:
            final_img = self._create_strip_layout(pil_images, orientation)
        else:
            final_img = pil_images[0]

        final_img = self._add_timestamp(final_img)
        buffer = io.BytesIO()
        final_img.save(buffer, format='JPEG', quality=settings.photo_quality)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _create_double_layout(self, images: List[Image.Image], orientation: OrientationType) -> Image.Image:
        img1, img2 = images[0], images[1]

        if orientation == OrientationType.landscape:
            target_height = 600
            img1_ratio = img1.width / img1.height
            img2_ratio = img2.width / img2.height

            img1 = img1.resize((int(target_height * img1_ratio), target_height))
            img2 = img2.resize((int(target_height * img2_ratio), target_height))

            gap = 20
            total_width = img1.width + img2.width + gap * 3
            total_height = target_height + gap * 2

            final_img = Image.new('RGB', (total_width, total_height), 'white')
            final_img.paste(img1, (gap, gap))
            final_img.paste(img2, (img1.width + gap * 2, gap))
        else:
            target_width = 600
            img1_ratio = img1.height / img1.width
            img2_ratio = img2.height / img2.width

            img1 = img1.resize((target_width, int(target_width * img1_ratio)))
            img2 = img2.resize((target_width, int(target_width * img2_ratio)))

            gap = 20
            total_width = target_width + gap * 2
            total_height = img1.height + img2.height + gap * 3

            final_img = Image.new('RGB', (total_width, total_height), 'white')
            final_img.paste(img1, (gap, gap))
            final_img.paste(img2, (gap, img1.height + gap * 2))

        return final_img

    def _create_quad_layout(self, images: List[Image.Image], orientation: OrientationType) -> Image.Image:
        images = images[:4]

        if orientation == OrientationType.landscape:
            target_size = (400, 300)
            cols, rows = 2, 2
        else:
            target_size = (350, 250)
            cols, rows = 1, 4

        resized_images = [img.resize(target_size, Image.Resampling.LANCZOS) for img in images]

        gap = 20 if orientation == OrientationType.landscape else 15
        final_width = target_size[0] * cols + gap * (cols + 1)
        final_height = target_size[1] * rows + gap * (rows + 1)

        final_img = Image.new('RGB', (final_width, final_height), 'white')

        positions = []
        for row in range(rows):
            for col in range(cols):
                x = gap + col * (target_size[0] + gap)
                y = gap + row * (target_size[1] + gap)
                positions.append((x, y))

        for img, pos in zip(resized_images, positions):
            final_img.paste(img, pos)

        return final_img

    def _create_strip_layout(self, images: List[Image.Image], orientation: OrientationType) -> Image.Image:
        images = images[:8]

        if orientation == OrientationType.portrait:
            target_size = (280, 200)
            cols, rows = 2, 4
        else:
            target_size = (200, 280)
            cols, rows = 4, 2

        resized_images = [img.resize(target_size, Image.Resampling.LANCZOS) for img in images]

        gap = 15
        final_width = target_size[0] * cols + gap * (cols + 1)
        final_height = target_size[1] * rows + gap * (rows + 1)

        final_img = Image.new('RGB', (final_width, final_height), 'white')
        positions = []
        for row in range(rows):
            for col in range(cols):
                x = gap + col * (target_size[0] + gap)
                y = gap + row * (target_size[1] + gap)
                positions.append((x, y))

        for img, pos in zip(resized_images, positions):
            final_img.paste(img, pos)

        return final_img

    def _add_timestamp(self, img: Image.Image) -> Image.Image:
        draw = ImageDraw.Draw(img)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Try to load font
        font = None
        font_paths = [
            "arial.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]

        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, 24)
                break
            except:
                continue

        if not font:
            font = ImageFont.load_default()

        text_bbox = draw.textbbox((0, 0), timestamp, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        text_x = (img.width - text_width) // 2
        text_y = img.height - text_height - 20

        background_padding = 10
        background_bbox = [
            text_x - background_padding,
            text_y - background_padding,
            text_x + text_width + background_padding,
            text_y + text_height + background_padding
        ]

        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(background_bbox, fill=(0, 0, 0, 128))

        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        draw.text((text_x, text_y), timestamp, fill='white', font=font)

        return img

    def save_photo(self, photo_b64: str, filename: str = None) -> str:
        if filename is None:
            filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"

        filepath = os.path.join(settings.photos_dir, filename)

        img_data = base64.b64decode(photo_b64)
        with open(filepath, 'wb') as f:
            f.write(img_data)

        return filename

photo_service = PhotoService()