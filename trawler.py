import os
import sys
from trawler.container_image_inspector import ContainerImageInspector
from trawler.ui_handler import run_curses_ui

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 trawler.py <path_to_tar_or_tar.gz>")
        sys.exit(1)

    local_image_path = sys.argv[1]

    if not os.path.isfile(local_image_path):
        print(f"File not found: {local_image_path}")
        sys.exit(1)

    inspector = ContainerImageInspector(local_image_path=local_image_path)
    run_curses_ui(inspector)
