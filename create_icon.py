"""
Icon Generator for LocalSQL Explorer

Creates a professional icon with:
- Database/table symbol
- SQL query representation
- Modern gradient colors
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_localsql_icon(output_dir: Path, size: int = 256):
    """
    Create a professional icon for LocalSQL Explorer.
    
    Args:
        output_dir: Directory to save the icon
        size: Icon size (will create multiple sizes)
    """
    
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Define colors - Modern blue/teal theme
    primary_color = (41, 128, 185)      # Professional blue
    secondary_color = (52, 152, 219)    # Lighter blue
    accent_color = (26, 188, 156)       # Teal accent
    dark_color = (44, 62, 80)           # Dark blue-grey
    white = (255, 255, 255)
    
    # Calculate proportions
    margin = size * 0.1
    center_x = size / 2
    center_y = size / 2
    
    # Draw outer circle background with gradient effect
    for i in range(3):
        radius = size * 0.45 - (i * 2)
        alpha = 255 - (i * 20)
        color = (*primary_color, alpha)
        draw.ellipse(
            [center_x - radius, center_y - radius, 
             center_x + radius, center_y + radius],
            fill=color
        )
    
    # Draw database cylinder icon (stylized)
    db_width = size * 0.5
    db_height = size * 0.6
    db_x = center_x - db_width / 2
    db_y = center_y - db_height / 2
    ellipse_height = size * 0.12
    
    # Top ellipse (database top)
    draw.ellipse(
        [db_x, db_y, db_x + db_width, db_y + ellipse_height],
        fill=white, outline=dark_color, width=3
    )
    
    # Cylinder body
    draw.rectangle(
        [db_x, db_y + ellipse_height / 2, 
         db_x + db_width, db_y + db_height - ellipse_height / 2],
        fill=white
    )
    
    # Sides
    draw.line([db_x, db_y + ellipse_height / 2, 
               db_x, db_y + db_height - ellipse_height / 2],
              fill=dark_color, width=3)
    draw.line([db_x + db_width, db_y + ellipse_height / 2,
               db_x + db_width, db_y + db_height - ellipse_height / 2],
              fill=dark_color, width=3)
    
    # Bottom ellipse
    draw.ellipse(
        [db_x, db_y + db_height - ellipse_height,
         db_x + db_width, db_y + db_height],
        fill=white, outline=dark_color, width=3
    )
    
    # Add horizontal lines to represent data rows
    line_spacing = size * 0.08
    for i in range(3):
        y = db_y + ellipse_height + line_spacing * (i + 1)
        if y < db_y + db_height - ellipse_height:
            draw.line(
                [db_x + size * 0.08, y, db_x + db_width - size * 0.08, y],
                fill=primary_color, width=2
            )
    
    # Add SQL symbol/accent
    sql_size = size * 0.18
    sql_x = center_x + db_width * 0.25
    sql_y = center_y + db_height * 0.15
    
    # Draw small accent circle with "SQL" or magnifying glass
    draw.ellipse(
        [sql_x - sql_size / 2, sql_y - sql_size / 2,
         sql_x + sql_size / 2, sql_y + sql_size / 2],
        fill=accent_color, outline=white, width=2
    )
    
    # Add magnifying glass handle
    handle_length = sql_size * 0.6
    handle_angle = 45  # degrees
    import math
    angle_rad = math.radians(handle_angle)
    handle_end_x = sql_x + handle_length * math.cos(angle_rad)
    handle_end_y = sql_y + handle_length * math.sin(angle_rad)
    draw.line(
        [sql_x + sql_size / 3, sql_y + sql_size / 3,
         handle_end_x, handle_end_y],
        fill=accent_color, width=4
    )
    
    return img

def create_icon_set(output_dir: Path):
    """Create a complete icon set with multiple sizes."""
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Creating LocalSQL Explorer icons...")
    
    # Generate main icon
    sizes = [16, 32, 48, 64, 128, 256]
    icons = []
    
    for size in sizes:
        print(f"  Generating {size}x{size} icon...")
        icon = create_localsql_icon(output_dir, size)
        icons.append(icon)
        
        # Save individual PNG
        icon.save(output_dir / f"icon_{size}.png", 'PNG')
    
    # Save as ICO file (Windows)
    print("  Creating Windows .ico file...")
    icons[0].save(
        output_dir / "app_icon.ico",
        format='ICO',
        sizes=[(size, size) for size in sizes]
    )
    
    # Save main PNG at highest resolution
    print("  Creating main icon.png...")
    icons[-1].save(output_dir / "icon.png", 'PNG')
    
    print(f"\n✓ Icons created successfully in: {output_dir}")
    print(f"  - app_icon.ico (Windows)")
    print(f"  - icon.png (main PNG)")
    print(f"  - icon_*.png (various sizes)")

if __name__ == "__main__":
    # Create icons in the assets directory
    assets_dir = Path(__file__).parent / "assets"
    create_icon_set(assets_dir)
