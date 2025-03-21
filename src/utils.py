def draw_bounding_box(draw, bounding_box, name):
    top, right, bottom, left = bounding_box
    draw.rectangle(((left, top), (right, bottom)), outline="blue", width=3)
    text_left, text_top, text_right, text_bottom = draw.textbbox(
        (left, bottom), name
    )
    draw.rectangle(
        ((text_left, text_top), (text_right, text_bottom)),
        fill="blue",
        outline="blue",
    )
    draw.text(
        (text_left, text_top),
        name,
        fill="white",
    )

def resize_image(image, width):
    aspect_ratio = image.height / image.width
    new_height = int(width * aspect_ratio)
    return image.resize((width, new_height), Image.ANTIALIAS)