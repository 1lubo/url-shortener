import io

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer


class QRService:
    """Service for generating QR codes."""

    @staticmethod
    def generate_qr_code(
        data: str,
        size: int = 10,
        border: int = 2,
    ) -> bytes:
        """
        Generate a QR code PNG image for the given data.

        Args:
            data: The data to encode (typically a URL)
            size: Box size (pixels per module), default 10
            border: Border size (modules), default 2

        Returns:
            PNG image as bytes
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Create image with rounded corners for modern look
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
        )

        # Save to bytes buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer.getvalue()
