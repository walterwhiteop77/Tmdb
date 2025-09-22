import aiohttp
import asyncio
import logging
import io
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Optional, Tuple
import textwrap
import os

logger = logging.getLogger(__name__)

class PosterGenerator:
    """Service for generating movie/TV show posters with captions."""
    
    def __init__(self):
        self.session = None
        self.default_font_size = 24
        self.title_font_size = 32
        self.caption_padding = 20
        self.landscape_caption_height = 100
        
    async def _get_session(self):
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL."""
        if not url:
            return None
            
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return Image.open(io.BytesIO(image_data))
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
        
        return None
    
    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Get font with specified size."""
        try:
            # Try to use system fonts
            if bold:
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/System/Library/Fonts/Arial-Bold.ttf",
                    "C:\\Windows\\Fonts\\arialbd.ttf"
                ]
            else:
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/System/Library/Fonts/Arial.ttf",
                    "C:\\Windows\\Fonts\\arial.ttf"
                ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            
            # Fallback to default font
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()
    
    def _format_caption(self, template: str, data: Dict) -> str:
        """Format caption template with movie/TV data."""
        # Create a copy of data with safe defaults
        safe_data = {}
        for key, value in data.items():
            if isinstance(value, (str, int, float)):
                safe_data[key] = str(value)
            else:
                safe_data[key] = "N/A"
        
        # Add additional formatting for common fields
        if 'rating' in safe_data and safe_data['rating'] != "N/A":
            try:
                rating = float(safe_data['rating'])
                safe_data['rating'] = f"{rating:.1f}"
            except:
                pass
        
        try:
            return template.format(**safe_data)
        except KeyError as e:
            logger.warning(f"Template key {e} not found in data")
            return template
        except Exception as e:
            logger.error(f"Error formatting caption: {e}")
            return template
    
    def _draw_text_with_outline(self, draw: ImageDraw.Draw, position: Tuple[int, int], 
                               text: str, font: ImageFont.ImageFont, 
                               fill_color: str = "white", outline_color: str = "black", 
                               outline_width: int = 2) -> int:
        """Draw text with outline for better visibility."""
        x, y = position
        
        # Draw outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        
        # Draw main text
        draw.text(position, text, font=font, fill=fill_color)
        
        # Return height of text
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[3] - bbox[1]
    
    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> list:
        """Wrap text to fit within specified width."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, force it
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    async def generate_poster(self, movie_data: Dict, caption_template: str, 
                            landscape_mode: bool = False, 
                            landscape_caption: str = None) -> Optional[io.BytesIO]:
        """Generate poster with caption."""
        try:
            # Choose poster URL (prefer backdrop for landscape mode)
            if landscape_mode and movie_data.get('backdrop_url'):
                poster_url = movie_data['backdrop_url']
            else:
                poster_url = movie_data.get('poster_url')
            
            if not poster_url:
                logger.error("No poster URL available")
                return None
            
            # Download poster image
            poster_image = await self.download_image(poster_url)
            if not poster_image:
                logger.error("Failed to download poster image")
                return None
            
            # Convert to RGB if necessary
            if poster_image.mode != 'RGB':
                poster_image = poster_image.convert('RGB')
            
            if landscape_mode:
                return await self._generate_landscape_poster(
                    poster_image, movie_data, landscape_caption or caption_template
                )
            else:
                return await self._generate_portrait_poster(
                    poster_image, movie_data, caption_template
                )
            
        except Exception as e:
            logger.error(f"Error generating poster: {e}")
            return None
    
    async def _generate_portrait_poster(self, poster_image: Image.Image, 
                                      movie_data: Dict, caption_template: str) -> io.BytesIO:
        """Generate portrait poster with caption below."""
        # Format caption
        caption_text = self._format_caption(caption_template, movie_data)
        
        # Calculate dimensions
        poster_width, poster_height = poster_image.size
        
        # Create fonts
        font = self._get_font(self.default_font_size)
        
        # Calculate caption area height
        caption_lines = self._wrap_text(
            caption_text, font, poster_width - (2 * self.caption_padding)
        )
        
        line_height = font.getbbox("Test")[3] - font.getbbox("Test")[1] + 5
        caption_height = len(caption_lines) * line_height + (2 * self.caption_padding)
        
        # Create new image with space for caption
        total_height = poster_height + caption_height
        final_image = Image.new('RGB', (poster_width, total_height), color='black')
        
        # Paste poster
        final_image.paste(poster_image, (0, 0))
        
        # Draw caption
        draw = ImageDraw.Draw(final_image)
        y_offset = poster_height + self.caption_padding
        
        for line in caption_lines:
            self._draw_text_with_outline(
                draw, (self.caption_padding, y_offset), line, font
            )
            y_offset += line_height
        
        # Save to BytesIO
        output = io.BytesIO()
        final_image.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        return output
    
    async def _generate_landscape_poster(self, poster_image: Image.Image, 
                                       movie_data: Dict, caption_template: str) -> io.BytesIO:
        """Generate landscape poster with caption overlay."""
        # Format caption
        caption_text = self._format_caption(caption_template, movie_data)
        
        # Resize image to landscape if needed
        poster_width, poster_height = poster_image.size
        
        if poster_height > poster_width:
            # Convert portrait to landscape by cropping/resizing
            target_ratio = 16 / 9
            current_ratio = poster_width / poster_height
            
            if current_ratio < target_ratio:
                # Too tall, crop height
                new_height = int(poster_width / target_ratio)
                top = (poster_height - new_height) // 2
                poster_image = poster_image.crop((0, top, poster_width, top + new_height))
            else:
                # Too wide, crop width
                new_width = int(poster_height * target_ratio)
                left = (poster_width - new_width) // 2
                poster_image = poster_image.crop((left, 0, left + new_width, poster_height))
        
        # Update dimensions after cropping
        poster_width, poster_height = poster_image.size
        
        # Create overlay for caption
        overlay = Image.new('RGBA', (poster_width, poster_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Create semi-transparent background for caption
        caption_bg_height = self.landscape_caption_height
        draw.rectangle(
            [(0, poster_height - caption_bg_height), (poster_width, poster_height)],
            fill=(0, 0, 0, 180)  # Semi-transparent black
        )
        
        # Draw caption text
        font = self._get_font(self.default_font_size, bold=True)
        caption_lines = self._wrap_text(
            caption_text, font, poster_width - (2 * self.caption_padding)
        )
        
        line_height = font.getbbox("Test")[3] - font.getbbox("Test")[1] + 5
        total_text_height = len(caption_lines) * line_height
        start_y = poster_height - caption_bg_height + (caption_bg_height - total_text_height) // 2
        
        for i, line in enumerate(caption_lines):
            y_pos = start_y + (i * line_height)
            draw.text(
                (self.caption_padding, y_pos), 
                line, 
                font=font, 
                fill=(255, 255, 255, 255)
            )
        
        # Composite overlay onto poster
        final_image = Image.alpha_composite(
            poster_image.convert('RGBA'), overlay
        ).convert('RGB')
        
        # Save to BytesIO
        output = io.BytesIO()
        final_image.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        return output
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()

# Global poster generator instance
poster_generator = PosterGenerator()
