import os

from PIL import Image, ImageChops



# Save the diff — black = same, white/colored = different

def get_pictures(user_id):
    """Gets the Picutres that ware taken, on the null index is the refrence Image"""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "../output")
    
    img1 = Image.open(os.path.join(output_dir, "0.png"))
    img2 = Image.open(os.path.join(output_dir, "0-0-Füllung-96%.png"))
    diff = ImageChops.difference(img1, img2)
    diff.save(os.path.join(output_dir, "diff.png"))





def main():
    get_pictures(0)

main()