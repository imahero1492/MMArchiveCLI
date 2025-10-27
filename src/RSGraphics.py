"""
RSGraphics - General Graphics Utilities
Direct Python conversion from RSGraphics.pas

Copyright (c) Rozhenko Sergey
http://sites.google.com/site/sergroj/
sergroj@mail.ru
"""

import math
from typing import Tuple, List, Optional, Callable
from PIL import Image
import struct


class TRSXForm:
    """2D transformation matrix"""
    def __init__(self):
        self.eM11: float = 1.0
        self.eM12: float = 0.0
        self.eM21: float = 0.0
        self.eM22: float = 1.0
    
    def try_inverse(self) -> bool:
        """Try to inverse matrix in place"""
        d = self.eM11 * self.eM22 - self.eM21 * self.eM12
        if d == 0:
            return False
        d = 1.0 / d
        x = d * self.eM11
        self.eM11 = d * self.eM22
        self.eM22 = x
        d = -d
        self.eM12 = d * self.eM12
        self.eM21 = d * self.eM21
        return True
    
    def try_inverse_to(self, dest: 'TRSXForm') -> bool:
        """Try to inverse matrix to destination"""
        d = self.eM11 * self.eM22 - self.eM21 * self.eM12
        if d == 0:
            return False
        d = 1.0 / d
        dest.eM11 = d * self.eM22
        dest.eM22 = d * self.eM11
        d = -d
        dest.eM12 = d * self.eM12
        dest.eM21 = d * self.eM21
        return True
    
    def inverse(self):
        """Inverse matrix in place"""
        if not self.try_inverse():
            raise Exception("The determinant is zero")
    
    def inverse_to(self, dest: 'TRSXForm'):
        """Inverse matrix to destination"""
        if not self.try_inverse_to(dest):
            raise Exception("The determinant is zero")
    
    def set_e(self):
        """Set to identity matrix"""
        self.eM11 = 1.0
        self.eM22 = 1.0
        self.eM12 = 0.0
        self.eM21 = 0.0
    
    def set_rotate(self, angle: float):
        """Set rotation matrix"""
        self.eM11 = math.cos(angle)
        self.eM22 = self.eM11
        self.eM12 = math.sin(angle)
        self.eM21 = -self.eM12
    
    def set_scale(self, x: float, y: float):
        """Set scale matrix"""
        self.eM11 = x
        self.eM12 = 0.0
        self.eM21 = 0.0
        self.eM22 = y
    
    def set_transform(self, o1: Tuple[int, int], x1: Tuple[int, int], y1: Tuple[int, int],
                      o2: Tuple[int, int], x2: Tuple[int, int], y2: Tuple[int, int]):
        """Set transformation from two coordinate systems"""
        a1 = TRSXForm()
        a1.eM11 = x1[0] - o1[0]
        a1.eM21 = o1[1] - x1[1]
        a1.eM12 = y1[0] - o1[0]
        a1.eM22 = o1[1] - y1[1]
        
        a2 = TRSXForm()
        a2.eM11 = x2[0] - o2[0]
        a2.eM21 = o2[1] - x2[1]
        a2.eM12 = y2[0] - o2[0]
        a2.eM22 = o2[1] - y2[1]
        
        a1.inverse()
        result = a1.mul(a2)
        self.eM11 = result.eM11
        self.eM12 = result.eM12
        self.eM21 = result.eM21
        self.eM22 = result.eM22
    
    def rotate(self, angle: float):
        """Apply rotation"""
        a = TRSXForm()
        a.eM11 = math.cos(angle)
        a.eM22 = a.eM11
        a.eM12 = math.sin(angle)
        a.eM21 = -a.eM12
        result = a.mul(self)
        self.eM11 = result.eM11
        self.eM12 = result.eM12
        self.eM21 = result.eM21
        self.eM22 = result.eM22
    
    def scale(self, x: float, y: float):
        """Apply scale"""
        self.eM11 *= x
        self.eM12 *= x
        self.eM21 *= y
        self.eM22 *= y
    
    def mul(self, v: 'TRSXForm') -> 'TRSXForm':
        """Multiply matrices"""
        result = TRSXForm()
        result.eM11 = self.eM11 * v.eM11 + self.eM12 * v.eM21
        result.eM12 = self.eM11 * v.eM12 + self.eM12 * v.eM22
        result.eM21 = self.eM21 * v.eM11 + self.eM22 * v.eM21
        result.eM22 = self.eM21 * v.eM12 + self.eM22 * v.eM22
        return result


class TRSHLS:
    """HLS color representation"""
    def __init__(self, hue: int = 0, lum: int = 0, sat: int = 0):
        self.hue: int = hue  # 0-240
        self.lum: int = lum  # 0-240
        self.sat: int = sat  # 0-240


def rs_rgb_to_hls(c: int) -> TRSHLS:
    """Convert RGB to HLS"""
    HLS_UNDEF = 160
    
    r = c & 0xFF
    g = (c >> 8) & 0xFF
    b = (c >> 16) & 0xFF
    
    result = TRSHLS()
    
    if r < g:
        if b >= g:
            k = b - r
            if k == 0:
                result.hue = HLS_UNDEF
            else:
                result.hue = ((r - g) * 240 + (240 * 4 + 3) * k) // (6 * k)
            i = b + r
        else:
            if b <= r:
                k = g - b
                if k == 0:
                    result.hue = HLS_UNDEF
                else:
                    result.hue = ((b - r) * 240 + (240 * 2 + 3) * k) // (6 * k)
                i = g + b
            else:
                k = g - r
                if k == 0:
                    result.hue = HLS_UNDEF
                else:
                    result.hue = ((b - r) * 240 + (240 * 2 + 3) * k) // (6 * k)
                i = g + r
    else:
        if b < g:
            k = r - b
            if k == 0:
                i = HLS_UNDEF
            else:
                i = ((g - b) * 240 + 3 * k) // (6 * k)
            
            if i < 0:
                result.hue = 240 + i
            else:
                result.hue = i
            i = r + b
        else:
            if b >= r:
                k = b - g
                if k == 0:
                    result.hue = HLS_UNDEF
                else:
                    result.hue = ((r - g) * 240 + (240 * 4 + 3) * k) // (6 * k)
                i = b + g
            else:
                k = r - g
                if k == 0:
                    j = HLS_UNDEF
                else:
                    j = ((g - b) * 240 + 3 * k) // (6 * k)
                
                if j < 0:
                    result.hue = 240 + j
                else:
                    result.hue = j
                i = r + g
    
    result.lum = (i * 240 + 255) // (2 * 255)
    
    if k == 0:
        result.sat = 0
    else:
        if i <= 255:
            result.sat = (k * (240 * 2) + i) // (i * 2)
        else:
            result.sat = (k * (240 * 2) + 2 * 255 - i) // (4 * 255 - i * 2)
    
    return result


def rs_hls_to_rgb(hls: TRSHLS) -> int:
    """Convert HLS to RGB"""
    if hls.lum == 0:
        return 0
    
    if hls.sat == 0:
        m1 = (hls.lum * 255 + 120) // 240
        return m1 | (m1 << 8) | (m1 << 16)
    
    if hls.lum <= 120:
        m2 = hls.lum * (hls.sat + 240)
    else:
        m2 = hls.lum * (240 - hls.sat) + hls.sat * 240
    
    m1 = 2 * 240 * hls.lum - m2
    
    def m3(x: int) -> int:
        return (40 * 255 * m1 + x * (m2 - m1) * 255 + 240 * 240 * 20) // (240 * 240 * 40)
    
    h = hls.hue // 40
    if h == 0:
        return ((m2 * 255 + 240 * 240 // 2) // (240 * 240)) | \
               (m3(hls.hue) << 8) | \
               ((m1 * 255 + 240 * 240 // 2) // (240 * 240) << 16)
    elif h == 1:
        return m3(40 * 2 - hls.hue) | \
               ((m2 * 255 + 240 * 240 // 2) // (240 * 240) << 8) | \
               ((m1 * 255 + 240 * 240 // 2) // (240 * 240) << 16)
    elif h == 2:
        return ((m1 * 255 + 240 * 240 // 2) // (240 * 240)) | \
               ((m2 * 255 + 240 * 240 // 2) // (240 * 240) << 8) | \
               (m3(hls.hue - 40 * 2) << 16)
    elif h == 3:
        return ((m1 * 255 + 240 * 240 // 2) // (240 * 240)) | \
               (m3(40 * 4 - hls.hue) << 8) | \
               ((m2 * 255 + 240 * 240 // 2) // (240 * 240) << 16)
    elif h == 4:
        return m3(hls.hue - 40 * 4) | \
               ((m1 * 255 + 240 * 240 // 2) // (240 * 240) << 8) | \
               ((m2 * 255 + 240 * 240 // 2) // (240 * 240) << 16)
    elif h == 5:
        return ((m2 * 255 + 240 * 240 // 2) // (240 * 240)) | \
               ((m1 * 255 + 240 * 240 // 2) // (240 * 240) << 8) | \
               (m3(40 * 6 - hls.hue) << 16)
    else:
        return 0


def rs_adjust_lum(c: int, change_by: int) -> int:
    """Adjust luminance"""
    a = rs_rgb_to_hls(c)
    i = a.lum + change_by
    if i < 0:
        i = 0
    elif i > 240:
        i = 240
    a.lum = i
    return rs_hls_to_rgb(a)


def rs_get_intensity(c: int) -> int:
    """Get color intensity (average of min and max RGB)"""
    r = c & 0xFF
    g = (c >> 8) & 0xFF
    b = (c >> 16) & 0xFF
    
    min_val = min(r, g, b)
    max_val = max(r, g, b)
    return (min_val + max_val) // 2


def rs_adjust_intensity(c: int, change_by: int) -> int:
    """Adjust color intensity"""
    r = c & 0xFF
    g = (c >> 8) & 0xFF
    b = (c >> 16) & 0xFF
    
    max_val = max(r, g, b)
    sum_val = r + g + b
    
    if sum_val == 0:
        if change_by > 0:
            return change_by | (change_by << 8) | (change_by << 16)
        else:
            return 0
    
    j = 256 + change_by * (256 * 2) // sum_val
    if max_val * j > 0xFFFF:
        j = 0xFFFF // max_val
    
    if j <= 0:
        return 0
    
    return ((j * r) >> 8) | (((j * g) >> 8) << 8) | (((j * b) >> 8) << 16)


def rs_swap_color(c: int) -> int:
    """Swap RGB to BGR"""
    return ((c & 0xFF) << 16) | (c & 0xFF00) | ((c >> 16) & 0xFF)


def rs_mix_colors(color1: int, color2: int, weight1: int, weight2: int = None) -> int:
    """Mix two colors with weight (0-255) or separate weights"""
    if weight2 is None:
        weight2 = 256 - weight1
        weight1 += 1
    else:
        total = weight1 + weight2
        weight1 = weight1 * 256 // total
        weight2 = 256 - weight1
    
    return (((weight1 * (color1 & 0xFF00) + weight2 * (color2 & 0xFF00)) >> 16) << 8) | \
           (((weight1 * (color1 & 0xFF00FF) + weight2 * (color2 & 0xFF00FF)) & 0xFF00FF00) >> 8)


def rs_mix_colors_rgb(color1: int, color2: int, weight1: int, weight2: int = None) -> int:
    """Mix two RGB colors with weight (0-255) or separate weights"""
    if weight2 is None:
        weight2 = 256 - weight1
        weight1 += 1
    else:
        total = weight1 + weight2
        weight1 = weight1 * 256 // total
        weight2 = 256 - weight1
    
    return (((weight1 * (color1 & 0xFF00) + weight2 * (color2 & 0xFF00)) >> 16) << 8) | \
           (((weight1 * (color1 & 0xFF00FF) + weight2 * (color2 & 0xFF00FF)) & 0xFF00FF00) >> 8)


def rs_mix_colors_norm(color1: int, color2: int, weight1: int) -> int:
    """Mix two colors normalized (weight 0-256)"""
    weight2 = 256 - weight1
    
    return (((weight1 * (color1 & 0xFF00) + weight2 * (color2 & 0xFF00)) >> 16) << 8) | \
           (((weight1 * (color1 & 0xFF00FF) + weight2 * (color2 & 0xFF00FF)) & 0xFF00FF00) >> 8)





def rs_mix_colors_array(colors: List[int], weights: List[int]) -> int:
    """Mix multiple colors with weights"""
    per = sum(weights)
    r = sum((colors[i] & 0xFF) * weights[i] for i in range(len(colors)))
    g = sum(((colors[i] >> 8) & 0xFF) * weights[i] for i in range(len(colors)))
    b = sum(((colors[i] >> 16) & 0xFF) * weights[i] for i in range(len(colors)))
    
    return (r // per) | ((g // per) << 8) | ((b // per) << 16)


def rs_mix_colors_rgb_ptr(colors: bytes, weights: bytes, length: int) -> int:
    """Mix colors from byte buffers (no step)"""
    per = 0
    r = g = b = 0
    
    for i in range(length):
        w = int.from_bytes(weights[i*4:(i+1)*4], 'little')
        c = int.from_bytes(colors[i*4:(i+1)*4], 'little')
        per += w
        r += (c & 0xFF) * w
        g += ((c >> 8) & 0xFF) * w
        b += ((c >> 16) & 0xFF) * w
    
    return (r // per) | ((g // per) << 8) | ((b // per) << 16)


def rs_mix_colors_rgb_ptr_step(colors: bytes, step: int, weights: bytes, length: int) -> int:
    """Mix colors from byte buffers with step"""
    per = 0
    r = g = b = 0
    
    for i in range(length):
        offset = i * step
        w = int.from_bytes(weights[i*4:(i+1)*4], 'little')
        c = int.from_bytes(colors[offset:offset+4], 'little')
        per += w
        r += (c & 0xFF) * w
        g += ((c >> 8) & 0xFF) * w
        b += ((c >> 16) & 0xFF) * w
    
    return (r // per) | ((g // per) << 8) | ((b // per) << 16)


def rs_mix_colors_ptr(colors: bytes, weights: bytes, length: int) -> int:
    """Mix colors from byte buffers (handles system colors)"""
    per = 0
    r = g = b = 0
    
    for i in range(length):
        w = int.from_bytes(weights[i*4:(i+1)*4], 'little')
        c = int.from_bytes(colors[i*4:(i+1)*4], 'little', signed=True)
        if c < 0:
            c = c & 0xFFFFFF
        per += w
        r += (c & 0xFF) * w
        g += ((c >> 8) & 0xFF) * w
        b += ((c >> 16) & 0xFF) * w
    
    return (r // per) | ((g // per) << 8) | ((b // per) << 16)


def rs_mix_colors_rgb_norm_ptr(colors: bytes, weights: bytes, length: int) -> int:
    """Mix colors normalized from byte buffers (no step)"""
    result = 0
    
    for i in range(length):
        w = int.from_bytes(weights[i*4:(i+1)*4], 'little')
        c = int.from_bytes(colors[i*4:(i+1)*4], 'little')
        result += (((w * (c & 0xFF00)) >> 16) << 8) | \
                  (((w * (c & 0xFF00FF)) & 0xFF00FF00) >> 8)
    
    return result


def rs_mix_colors_rgb_norm_ptr_step(colors: bytes, step: int, weights: bytes, length: int) -> int:
    """Mix colors normalized from byte buffers with step"""
    result = 0
    
    for i in range(length):
        offset = i * step
        w = int.from_bytes(weights[i*4:(i+1)*4], 'little')
        c = int.from_bytes(colors[offset:offset+4], 'little')
        result += (((w * (c & 0xFF00)) >> 16) << 8) | \
                  (((w * (c & 0xFF00FF)) & 0xFF00FF00) >> 8)
    
    return result


def rs_mix_colors_norm_ptr(colors: bytes, weights: bytes, length: int) -> int:
    """Mix colors normalized from byte buffers (handles system colors)"""
    result = 0
    
    for i in range(length):
        w = int.from_bytes(weights[i*4:(i+1)*4], 'little')
        c = int.from_bytes(colors[i*4:(i+1)*4], 'little', signed=True)
        if c < 0:
            c = c & 0xFFFFFF
        result += (((w * (c & 0xFF00)) >> 16) << 8) | \
                  (((w * (c & 0xFF00FF)) & 0xFF00FF00) >> 8)
    
    return result


def rs_mix_colors_norm_array(colors: List[int], weights: List[int]) -> int:
    """Mix colors normalized with arrays"""
    result = 0
    
    for i in range(len(colors)):
        c = colors[i]
        w = weights[i]
        result += (((w * (c & 0xFF00)) >> 16) << 8) | \
                  (((w * (c & 0xFF00FF)) & 0xFF00FF00) >> 8)
    
    return result


def rs_grayscale(img: Image.Image) -> Image.Image:
    """Convert image to grayscale"""
    return img.convert('L')


def rs_grayscale_spec(img: Image.Image, light: int, dark: int) -> Image.Image:
    """Convert to grayscale with custom light/dark colors"""
    gray = img.convert('L')
    result = Image.new('RGB', img.size)
    
    light_r, light_g, light_b = light & 0xFF, (light >> 8) & 0xFF, (light >> 16) & 0xFF
    dark_r, dark_g, dark_b = dark & 0xFF, (dark >> 8) & 0xFF, (dark >> 16) & 0xFF
    
    pixels = []
    for y in range(img.height):
        for x in range(img.width):
            intensity = gray.getpixel((x, y))
            r = (light_r * intensity + dark_r * (255 - intensity)) // 255
            g = (light_g * intensity + dark_g * (255 - intensity)) // 255
            b = (light_b * intensity + dark_b * (255 - intensity)) // 255
            pixels.append((r, g, b))
    
    result.putdata(pixels)
    return result


def rs_gradient_v(img: Image.Image, rect: Tuple[int, int, int, int], up_color: int, down_color: int):
    """Draw vertical gradient"""
    x1, y1, x2, y2 = rect
    width = x2 - x1
    height = y2 - y1
    
    for y in range(height):
        weight = (y * 255) // max(height - 1, 1)
        color = rs_mix_colors(down_color, up_color, weight)
        r, g, b = color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF
        for x in range(width):
            img.putpixel((x1 + x, y1 + y), (r, g, b))


def rs_gradient_h(img: Image.Image, rect: Tuple[int, int, int, int], left_color: int, right_color: int):
    """Draw horizontal gradient"""
    x1, y1, x2, y2 = rect
    width = x2 - x1
    height = y2 - y1
    
    for x in range(width):
        weight = (x * 255) // max(width - 1, 1)
        color = rs_mix_colors(right_color, left_color, weight)
        r, g, b = color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF
        for y in range(height):
            img.putpixel((x1 + x, y1 + y), (r, g, b))


def rs_gradient_v32(img: Image.Image, rect: Tuple[int, int, int, int], up_color: int, down_color: int):
    """Draw vertical gradient (deprecated, use rs_gradient_v)"""
    rs_gradient_v(img, rect, up_color, down_color)


def rs_gradient_h32(img: Image.Image, rect: Tuple[int, int, int, int], left_color: int, right_color: int):
    """Draw horizontal gradient (deprecated, use rs_gradient_h)"""
    rs_gradient_h(img, rect, left_color, right_color)


def rs_simple_rotate_32(img: Image.Image, rotation: int, rect: Tuple[int, int, int, int] = None) -> Image.Image:
    """Simple rotation (90, 180, 270 degrees) or flip"""
    if rect:
        img = img.crop(rect)
    
    if rotation == 1:  # 90 degrees
        return img.transpose(Image.ROTATE_270)
    elif rotation == 2:  # 180 degrees
        return img.transpose(Image.ROTATE_180)
    elif rotation == 3:  # 270 degrees
        return img.transpose(Image.ROTATE_90)
    elif rotation == 4:  # H flip
        return img.transpose(Image.FLIP_LEFT_RIGHT)
    elif rotation == 6:  # V flip (4 + 180)
        return img.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        return img.copy()


def rs_transform_32(img: Image.Image, form: TRSXForm, no_color: int = 0,
                    preserve_no_color: bool = False, rect: Tuple[int, int, int, int] = None,
                    cut_rect: bool = False) -> Image.Image:
    """Transform image using matrix"""
    if rect:
        if cut_rect:
            img = img.crop(rect)
            rect = None
    
    # Calculate bounds
    if rect:
        corners = [
            (rect[0], rect[1]),
            (rect[2], rect[1]),
            (rect[0], rect[3]),
            (rect[2], rect[3])
        ]
    else:
        corners = [
            (0, 0),
            (img.width, 0),
            (0, img.height),
            (img.width, img.height)
        ]
    
    inv_form = TRSXForm()
    form.inverse_to(inv_form)
    
    # Transform corners to find output size
    transformed = []
    for x, y in corners:
        tx = form.eM11 * x + form.eM12 * y
        ty = form.eM21 * x + form.eM22 * y
        transformed.append((tx, ty))
    
    min_x = int(min(t[0] for t in transformed))
    max_x = int(max(t[0] for t in transformed))
    min_y = int(min(t[1] for t in transformed))
    max_y = int(max(t[1] for t in transformed))
    
    out_width = max_x - min_x + 1
    out_height = max_y - min_y + 1
    
    result = Image.new('RGB', (out_width, out_height), no_color)
    
    # Transform each pixel
    for out_y in range(out_height):
        for out_x in range(out_width):
            src_x = inv_form.eM11 * (out_x + min_x) + inv_form.eM12 * (out_y + min_y)
            src_y = inv_form.eM21 * (out_x + min_x) + inv_form.eM22 * (out_y + min_y)
            
            ix, iy = int(src_x), int(src_y)
            if 0 <= ix < img.width and 0 <= iy < img.height:
                result.putpixel((out_x, out_y), img.getpixel((ix, iy)))
    
    return result


def rs_load_pic(path: str, pixel_format: str = 'RGB') -> Image.Image:
    """Load picture from file"""
    return Image.open(path).convert(pixel_format)


def rs_load_bitmap(path: str) -> Image.Image:
    """Load bitmap with Delphi bug fixes (RLE8, negative height)"""
    return Image.open(path)


def rs_get_pixel_format(img: Image.Image) -> str:
    """Get pixel format of image"""
    return img.mode


def rs_buffer_to_bitmap(buf: bytes, width: int, height: int, pixel_format: str = 'RGB', 
                         rect: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
    """Convert buffer to bitmap"""
    img = Image.frombytes(pixel_format, (width, height), buf)
    if rect:
        x1, y1, x2, y2 = rect
        img = img.crop((x1, y1, x2, y2))
    return img


def rs_bitmap_to_buffer(img: Image.Image, rect: Optional[Tuple[int, int, int, int]] = None) -> bytes:
    """Convert bitmap to buffer"""
    if rect:
        x1, y1, x2, y2 = rect
        img = img.crop((x1, y1, x2, y2))
    return img.tobytes()


def rs_mix_pic_color_32(mix_to: Image.Image, mix_pic: Image.Image, color: int, 
                         weight1: int, weight2: int) -> Image.Image:
    """Mix picture with solid color"""
    if mix_pic.size[1] == 0:
        return mix_to if mix_to == mix_pic else mix_pic.copy()
    
    total = weight1 + weight2
    w1 = weight1 * 256 // total
    w2 = 256 - w1
    
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    
    if mix_to != mix_pic:
        result = Image.new('RGB', mix_pic.size)
    else:
        result = mix_to
    
    pixels = list(mix_pic.getdata())
    result_pixels = []
    
    for p in pixels:
        if isinstance(p, tuple):
            pr, pg, pb = p[0], p[1], p[2]
        else:
            pr = pg = pb = p
        
        nr = ((pr * w1 + r * w2) >> 8)
        ng = ((pg * w1 + g * w2) >> 8)
        nb = ((pb * w1 + b * w2) >> 8)
        result_pixels.append((nr, ng, nb))
    
    result.putdata(result_pixels)
    return result


def rs_mix_pics(img1: Image.Image, img2: Image.Image, weight1: int, weight2: int) -> Image.Image:
    """Mix two images with weights"""
    if img1.size != img2.size:
        raise ValueError("Images must have same size")
    
    result = Image.new(img1.mode, img1.size)
    total = weight1 + weight2
    w1 = weight1 * 256 // total
    w2 = 256 - w1
    
    pixels1 = list(img1.getdata())
    pixels2 = list(img2.getdata())
    result_pixels = []
    
    for p1, p2 in zip(pixels1, pixels2):
        if isinstance(p1, tuple):
            mixed = tuple((p1[i] * w1 + p2[i] * w2) >> 8 for i in range(len(p1)))
        else:
            mixed = (p1 * w1 + p2 * w2) >> 8
        result_pixels.append(mixed)
    
    result.putdata(result_pixels)
    return result


def rs_transparent_random(img: Image.Image, transparent_color: int, transparency):
    """Apply random transparency (transparency can be int 0-255 or grayscale Image)"""
    import random
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    pixels = list(img.getdata())
    tr, tg, tb = transparent_color & 0xFF, (transparent_color >> 8) & 0xFF, (transparent_color >> 16) & 0xFF
    
    if isinstance(transparency, Image.Image):
        # Use grayscale bitmap as transparency map
        trans_pixels = list(transparency.convert('L').getdata())
        for i in range(min(len(pixels), len(trans_pixels))):
            if random.randint(0, 255) < trans_pixels[i]:
                pixels[i] = (tr, tg, tb, 0)
    else:
        # Use fixed transparency value
        for i in range(len(pixels)):
            if random.randint(0, 255) < transparency:
                pixels[i] = (tr, tg, tb, 0)
    
    img.putdata(pixels)


def rs_transparent_fixed(img: Image.Image, transparent_color: int, step: int = 1):
    """Apply fixed pattern transparency"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    pixels = list(img.getdata())
    tr, tg, tb = transparent_color & 0xFF, (transparent_color >> 8) & 0xFF, (transparent_color >> 16) & 0xFF
    width = img.width
    
    for y in range(img.height):
        for x in range(0, width, step):
            idx = y * width + x
            if idx < len(pixels):
                pixels[idx] = (tr, tg, tb, 0)
    
    img.putdata(pixels)


def rs_change_gray_pic(img: Image.Image, add: int):
    """Change grayscale picture brightness"""
    if img.mode != 'L':
        raise ValueError("Image must be grayscale")
    
    pixels = list(img.getdata())
    result = []
    
    for p in pixels:
        new_val = p + add
        if new_val < 0:
            new_val = 0
        elif new_val > 255:
            new_val = 255
        result.append(new_val)
    
    img.putdata(result)


def rs_draw_mono_bmp(canvas_img: Image.Image, bmp: Image.Image, color: int, x: int, y: int):
    """Draw monochrome bitmap with color (ROP_DSPDxax operation)"""
    # Convert to monochrome
    mono = bmp.convert('1')
    
    # Extract color components
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    
    # Apply ROP_DSPDxax: (Dest XOR Pattern) AND Source XOR Dest
    # Simplified: where bitmap is white (1), apply brush color
    for py in range(bmp.height):
        for px in range(bmp.width):
            if mono.getpixel((px, py)):
                canvas_img.putpixel((x + px, y + py), (r, g, b))


def rs_draw_mask(canvas_img: Image.Image, bmp: Image.Image, color: int, x: int, y: int):
    """Draw mask with color using alpha channel or luminance"""
    # Extract mask (alpha channel or convert to grayscale)
    if bmp.mode == 'RGBA':
        mask = bmp.split()[3]
    else:
        mask = bmp.convert('L')
    
    # Extract color components
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    
    # Apply color with mask transparency
    for py in range(bmp.height):
        for px in range(bmp.width):
            alpha = mask.getpixel((px, py))
            if alpha > 0:
                # Get destination pixel
                dest = canvas_img.getpixel((x + px, y + py))
                if isinstance(dest, tuple):
                    dr, dg, db = dest[0], dest[1], dest[2]
                else:
                    dr = dg = db = dest
                
                # Blend with mask alpha
                nr = (r * alpha + dr * (255 - alpha)) // 255
                ng = (g * alpha + dg * (255 - alpha)) // 255
                nb = (b * alpha + db * (255 - alpha)) // 255
                canvas_img.putpixel((x + px, y + py), (nr, ng, nb))


def rs_draw_disabled(canvas_img: Image.Image, bmp: Image.Image, color: int, x: int, y: int):
    """Draw disabled bitmap (grayscale with highlight/shadow effect)"""
    # Convert to grayscale
    gray = bmp.convert('L')
    
    # Extract color components
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    
    # Draw with disabled effect (lighter version offset by 1 pixel, then darker main)
    # First pass: draw highlight (offset +1, +1 with lighter color)
    light_r = min(255, r + 85)
    light_g = min(255, g + 85)
    light_b = min(255, b + 85)
    
    for py in range(bmp.height):
        for px in range(bmp.width):
            intensity = gray.getpixel((px, py))
            if intensity > 128:  # Only draw where bitmap has content
                if x + px + 1 < canvas_img.width and y + py + 1 < canvas_img.height:
                    canvas_img.putpixel((x + px + 1, y + py + 1), (light_r, light_g, light_b))
    
    # Second pass: draw main (darker)
    dark_r = r // 2
    dark_g = g // 2
    dark_b = b // 2
    
    for py in range(bmp.height):
        for px in range(bmp.width):
            intensity = gray.getpixel((px, py))
            if intensity > 128:
                canvas_img.putpixel((x + px, y + py), (dark_r, dark_g, dark_b))


def rs_any_transform_32(img: Image.Image, transform_proc: Callable, 
                        width: int, height: int, no_color: int = 0,
                        clip_rect: Tuple[int, int, int, int] = None,
                        preserve_no_color: bool = False,
                        user_data = None) -> Image.Image:
    """Transform image using custom procedure"""
    result = Image.new('RGB', (width, height), no_color)
    
    for y in range(height):
        for x in range(width):
            if clip_rect:
                if not (clip_rect[0] <= x < clip_rect[2] and clip_rect[1] <= y < clip_rect[3]):
                    continue
            
            src_pos = transform_proc(user_data, (x, y), img, result) if user_data is not None else transform_proc(x, y, img, result)
            
            if isinstance(src_pos, tuple) and len(src_pos) == 2:
                if isinstance(src_pos[0], float):
                    src_x, src_y = int(src_pos[0]), int(src_pos[1])
                else:
                    src_x, src_y = src_pos
                
                if 0 <= src_x < img.width and 0 <= src_y < img.height:
                    pixel = img.getpixel((src_x, src_y))
                    if not preserve_no_color or pixel != no_color:
                        result.putpixel((x, y), pixel)
    
    return result


def rs_transform_smooth_proc(per: List[int], col: List[int], all_p: int) -> int:
    """Bilinear color interpolation"""
    if all_p < 255:
        return rs_mix_colors_array(col, per)
    else:
        total = sum(per)
        r = sum((col[i] & 0xFF) * per[i] for i in range(len(col))) // total
        g = sum(((col[i] >> 8) & 0xFF) * per[i] for i in range(len(col))) // total
        b = sum(((col[i] >> 16) & 0xFF) * per[i] for i in range(len(col))) // total
        return r | (g << 8) | (b << 16)


def rs_transform_smart_proc(per: List[int], col: List[int], all_p: int, mix: int) -> int:
    """Smart color interpolation with nearest neighbor"""
    aa = rs_transform_smooth_proc(per, col, all_p)
    
    # Find closest color
    min_diff = float('inf')
    closest_idx = 0
    for i in range(len(col)):
        if per[i] != 0:
            diff = abs((aa & 0xFF) - (col[i] & 0xFF)) + \
                   abs(((aa >> 8) & 0xFF) - ((col[i] >> 8) & 0xFF)) + \
                   abs(((aa >> 16) & 0xFF) - ((col[i] >> 16) & 0xFF))
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
    
    if mix == 0:
        return col[closest_idx]
    else:
        return rs_mix_colors_rgb(aa, col[closest_idx], mix)


def rs_transform_smart_proc2(per: List[int], col: List[int], all_p: int, mix: int) -> int:
    """Smart color interpolation v2"""
    aa = rs_transform_smooth_proc(per, col, all_p)
    
    # Find color with highest weight
    max_weight = 0
    best_idx = 0
    for i in range(len(per)):
        if per[i] > max_weight:
            max_weight = per[i]
            best_idx = i
    
    return rs_mix_colors_rgb(aa, col[best_idx], mix)


__all__ = [
    'TRSXForm',
    'TRSHLS',
    'rs_rgb_to_hls',
    'rs_hls_to_rgb',
    'rs_adjust_lum',
    'rs_get_intensity',
    'rs_adjust_intensity',
    'rs_swap_color',
    'rs_mix_colors',
    'rs_mix_colors_rgb',
    'rs_mix_colors_norm',

    'rs_mix_colors_array',
    'rs_mix_colors_rgb_ptr',
    'rs_mix_colors_rgb_ptr_step',
    'rs_mix_colors_ptr',
    'rs_mix_colors_rgb_norm_ptr',
    'rs_mix_colors_rgb_norm_ptr_step',
    'rs_mix_colors_norm_ptr',
    'rs_mix_colors_norm_array',
    'rs_grayscale',
    'rs_grayscale_spec',
    'rs_gradient_v',
    'rs_gradient_h',
    'rs_gradient_v32',
    'rs_gradient_h32',
    'rs_simple_rotate_32',
    'rs_transform_32',
    'rs_load_pic',
    'rs_load_bitmap',
    'rs_get_pixel_format',
    'rs_buffer_to_bitmap',
    'rs_bitmap_to_buffer',
    'rs_mix_pic_color_32',
    'rs_mix_pics',
    'rs_transparent_random',
    'rs_transparent_fixed',
    'rs_change_gray_pic',
    'rs_draw_mono_bmp',
    'rs_draw_mask',
    'rs_draw_disabled',
    'rs_any_transform_32',
    'rs_transform_smooth_proc',
    'rs_transform_smart_proc',
    'rs_transform_smart_proc2',
]
