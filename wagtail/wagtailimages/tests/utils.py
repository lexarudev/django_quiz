import PIL.Image
from six import BytesIO

from django.core.files.images import ImageFile

from wagtail.wagtailimages.models import get_image_model


Image = get_image_model()


def get_test_image_file(filename='test.png', width=640, height=480):
    f = BytesIO()
    image = PIL.Image.new('RGB', (width, height), 'white')
    image.save(f, 'PNG')
    return ImageFile(f, name=filename)
