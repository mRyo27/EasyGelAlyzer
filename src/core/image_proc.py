from common import *
from PIL import Image, ImageOps, ImageEnhance

# OpenCV (cv2) is optional
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

def apply_clahe_pil(image):
    """Apply CLAHE-like adaptive histogram equalization to PIL image.
    Uses OpenCV if available, otherwise falls back to PIL's autocontrast.
    """
    if HAS_OPENCV:
        # Check image mode and apply CLAHE to luminance
        if image.mode == "RGB":
            img_lab = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(img_lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            img_lab_enhanced = cv2.merge((cl, a, b))
            enhanced_np = cv2.cvtColor(img_lab_enhanced, cv2.COLOR_LAB2RGB)
            return Image.fromarray(enhanced_np)
        else:
            img_np = np.array(image.convert("L"))
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced_np = clahe.apply(img_np)
            return Image.fromarray(enhanced_np).convert(image.mode)
    else:
        # Fallback to autocontrast
        return ImageOps.autocontrast(image, cutoff=2)

def apply_gamma_correction(image, gamma=0.5):
    """Apply gamma correction for dark area enhancement (gamma < 1.0)"""
    lut = [int(255 * ((i / 255.0) ** gamma)) for i in range(256)]
    if image.mode == "RGB":
        return image.point(lut * 3)
    else:
        return image.point(lut)

def preset_etbr(image):
    """EtBr Gel: Invert + Contrast enhancement (CLAHE)"""
    # Invert image (nucleic acids are typically white bands on black background, 
    # and inversion helps standard analysis).
    inv = ImageOps.invert(image.convert("RGB"))
    return apply_clahe_pil(inv)

def preset_coomassie(image):
    """Coomassie: Soft contrast enhancement"""
    # Soft contrast adjustment
    return ImageOps.autocontrast(image, cutoff=1)

def preset_silver(image):
    """Silver: Invert + Gamma correction (Dark enhancement)"""
    inv = ImageOps.invert(image.convert("RGB"))
    # Dark signal enhancement
    return apply_gamma_correction(inv, gamma=0.6)


def rolling_ball_background(image, radius=50):
    """Apply rolling‑ball background subtraction.

    Parameters
    ----------
    image : PIL.Image.Image
        Input image (RGB or L mode).
    radius : int, optional
        Radius of the structuring element in pixels. Larger values smooth
        larger background variations. Default is 50.

    Returns
    -------
    PIL.Image.Image
        Image with the estimated background removed (original minus background).
    """
    if not isinstance(radius, int) or radius < 1:
        raise ValueError("radius must be a positive integer")

    # Convert to appropriate mode for OpenCV processing
    if image.mode != "RGB":
        img = image.convert("RGB")
    else:
        img = image

    if HAS_OPENCV:
        # Use OpenCV morphological opening with a circular kernel
        import numpy as np
        import cv2
        img_np = np.array(img)
        # Create circular structuring element
        ksize = radius * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
        # Perform opening (erosion followed by dilation) to estimate background
        background = cv2.morphologyEx(img_np, cv2.MORPH_OPEN, kernel)
        # Subtract background
        corrected = cv2.subtract(img_np, background)
        return Image.fromarray(corrected)
    else:
        # Fallback: return original (no OpenCV) – callers can still use other preprocessing
        return img
