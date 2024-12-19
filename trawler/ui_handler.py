import curses

def run_curses_ui(inspector):
    def main(stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        current_screen = 'layers'
        selected_layer = 0
        layer_offset = 0
        selected_file = 0
        file_offset = 0
        current_path = ''
        status_message = ""
        search_results = []
        max_y, max_x = stdscr.getmaxyx()
        search_across_layers = False
        prev_screen = ''

        total_layers = len(inspector.layers)

        def update_size():
            nonlocal max_y, max_x
            max_y, max_x = stdscr.getmaxyx()
        
        def truncate_addstr(y, x, prtstring, formatting=None):
            trunc_prtstring = (prtstring[:max_x - 4] + '...') if len(prtstring) > max_x - 4 else prtstring
            if formatting:
                stdscr.addstr(y, x, trunc_prtstring, formatting)
            else:
                stdscr.addstr(y, x, trunc_prtstring)

        def display_layers():
            stdscr.clear()
            update_size()
            truncate_addstr(0, 0, "=== Docker Image Layers ===", curses.A_BOLD)
            display_limit = max_y - 3

            for idx in range(display_limit):
                layer_idx = layer_offset + idx
                if layer_idx >= total_layers:
                    break
                layer_name = inspector.layers[layer_idx]
                command = inspector.get_layer_command(layer_name)

                if layer_idx == selected_layer:
                    stdscr.attron(curses.color_pair(1))
                    truncate_addstr(idx + 1, 0, f"Layer {layer_idx}: {command}")
                    stdscr.attroff(curses.color_pair(1))
                else:
                    truncate_addstr(idx + 1, 0, f"Layer {layer_idx}: {command}")

            full_command = inspector.get_layer_command(inspector.layers[selected_layer])
            truncated_full_command = (full_command[:max_x - 1] + '...') if len(full_command) > max_x - 1 else full_command
            if status_message:
                truncate_addstr(max_y - 2, 0, status_message, curses.color_pair(4))
            else:
                truncate_addstr(max_y - 2, 0, f"Layer {selected_layer} created by: {truncated_full_command}", curses.A_DIM)
            truncate_addstr(max_y - 1, 0, "Navigate with ↑/↓, Enter to select, 's' to search, 'q' to quit", curses.A_DIM)
            stdscr.refresh()

        def display_quit():
            stdscr.clear()
            update_size()
            truncate_addstr(0, 0, "=== Are you sure you want to quit? ===", curses.A_BOLD)
            truncate_addstr(max_y - 2, 0, status_message, curses.color_pair(4))
            truncate_addstr(max_y - 1, 0, "press 'q/Enter' to confirm, any other key to cancel", curses.A_DIM)
            stdscr.refresh()

        def display_files(files, layer_idx):
            stdscr.clear()
            update_size()
            truncate_addstr(0, 0, f"=== Files in Layer {layer_idx} ({current_path}) ===", curses.A_BOLD)
            display_limit = max_y - 3

            for idx in range(display_limit):
                file_idx = file_offset + idx
                if file_idx >= len(files):
                    break
                file = files[file_idx]
                display_name = file.name
                if file.isdir():
                    display_name += '/'
                    stdscr.attron(curses.color_pair(2))
                else:
                    stdscr.attron(curses.color_pair(3))
                if file_idx == selected_file:
                    stdscr.attron(curses.color_pair(1))
                    truncate_addstr(idx + 1, 0, display_name)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    truncate_addstr(idx + 1, 0, display_name)
                stdscr.attroff(curses.color_pair(2))
                stdscr.attroff(curses.color_pair(3))

            truncate_addstr(max_y - 2, 0, status_message, curses.color_pair(4))
            truncate_addstr(max_y - 1, 0, "Navigate with ↑/↓, Enter to open, 'e' to extract, 'b/←' to go back, 'q' to return", curses.A_DIM)
            stdscr.refresh()

        def navigate_directory(file):
            nonlocal current_path, selected_file, file_offset
            current_path = file.name  # Update the current path when entering a directory
            files = inspector.list_files_in_layer(selected_layer, current_path)
            selected_file = 0
            file_offset = 0
            return files

        def display_search_results(files, query):
            stdscr.clear()
            update_size()
            truncate_addstr(0, 0, f"=== Search Results for '{query}' ===", curses.A_BOLD)
            display_limit = max_y - 3

            for idx in range(display_limit):
                file_idx = file_offset + idx
                if file_idx >= len(files):
                    break
                file = files[file_idx]
                display_name = file.name  # Show full path of the file
                if file.isdir():
                    display_name += '/'
                    stdscr.attron(curses.color_pair(2))
                else:
                    stdscr.attron(curses.color_pair(3))
                if file_idx == selected_file:
                    stdscr.attron(curses.color_pair(1))
                    truncate_addstr(idx + 1, 0, display_name)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    truncate_addstr(idx + 1, 0, display_name)
                stdscr.attroff(curses.color_pair(2))
                stdscr.attroff(curses.color_pair(3))

            truncate_addstr(max_y - 2, 0, status_message, curses.color_pair(4))
            truncate_addstr(max_y - 1, 0, "Navigate with ↑/↓, Enter to open, 'b' to go back, 'q' to return", curses.A_DIM)
            stdscr.refresh()

        def display_search_results_across_layers(results, query, selected_file, file_offset):
            stdscr.clear()
            update_size()
            truncate_addstr(0, 0, f"=== Search Results for '{query}' ===", curses.A_BOLD)

            # Count total number of results
            total_results = [(layer_idx, file) for layer_idx, files in results.items() for file in files]
            total_files = len(total_results)

            # Display results with scroll support
            display_limit = max_y - 3  # Limit the number of lines we can display
            start_idx = file_offset
            end_idx = min(start_idx + display_limit, total_files)

            # Render only the visible portion
            current_line = 1
            for i in range(start_idx, end_idx):
                layer_idx, file = total_results[i]
                display_name = f"Layer {layer_idx}: {file.name}"

                if file.isdir():
                    display_name += '/'
                    stdscr.attron(curses.color_pair(2))
                else:
                    stdscr.attron(curses.color_pair(3))

                if i == selected_file:
                    stdscr.attron(curses.color_pair(1))
                    truncate_addstr(current_line, 0, display_name)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    truncate_addstr(current_line, 0, display_name)

                stdscr.attroff(curses.color_pair(2))
                stdscr.attroff(curses.color_pair(3))
                current_line += 1

            # Status message at the bottom
            truncate_addstr(max_y - 2, 0, status_message, curses.color_pair(4))
            truncate_addstr(max_y - 1, 0, "Navigate with ↑/↓, Enter to open, 'b' to go back, 'q' to return", curses.A_DIM)
            stdscr.refresh()


        while True:

            if current_screen == 'quit':
                display_quit()
                key = stdscr.getch()
                if key in [curses.KEY_ENTER, 10, 13, ord('q')]:
                    break
                elif key:
                    if prev_screen:
                        current_screen = prev_screen
                    else:
                        current_screen = 'layers'

            elif current_screen == 'layers':
                display_layers()
                key = stdscr.getch()
                if key == curses.KEY_UP:
                    if selected_layer > 0:
                        selected_layer -= 1
                    if selected_layer < layer_offset:
                        layer_offset -= 1
                    status_message = ""
                elif key == curses.KEY_DOWN:
                    if selected_layer < total_layers - 1:
                        selected_layer += 1
                    if selected_layer >= layer_offset + (max_y - 2):
                        layer_offset += 1
                    status_message = ""
                elif key in [curses.KEY_ENTER, 10, 13]:
                    current_path = ''
                    files = inspector.list_files_in_layer(selected_layer, current_path)
                    if not files:
                        status_message = f"No files found in Layer {selected_layer}."
                        stdscr.clear()
                        truncate_addstr(0, 0, status_message, curses.color_pair(4))
                        truncate_addstr(2, 0, "Press any key to continue.")
                        stdscr.refresh()
                        stdscr.getch()
                        status_message = ""
                        continue
                    current_screen = 'files'
                    selected_file = 0
                    file_offset = 0
                    status_message = ""
                elif key == ord('s'):
                    stdscr.clear()
                    truncate_addstr(max_y - 2, 0, "Enter search query: ")
                    stdscr.clrtoeol()
                    curses.echo()
                    search_query = stdscr.getstr(max_y - 2, len("Enter search query: ")).decode('utf-8').strip()
                    curses.noecho()
                    search_results = inspector.search_files_across_layers(search_query)
                    if search_results:
                        current_screen = 'search'
                        search_across_layers = True
                        selected_file = 0
                        file_offset = 0
                        status_message = f"Search results for '{search_query}'"
                        display_search_results_across_layers(search_results, search_query, selected_file, file_offset)
                    else:
                        status_message = f"No results found for '{search_query}'"
                elif key == ord('q'):
                    prev_screen = current_screen
                    current_screen = 'quit'
                    status_message = ""

            elif current_screen == 'files':
                display_files(files, selected_layer)
                key = stdscr.getch()
                if key == curses.KEY_UP:
                    if selected_file > 0:
                        selected_file -= 1
                    if selected_file < file_offset:
                        file_offset -= 1
                elif key == curses.KEY_DOWN:
                    if selected_file < len(files) - 1:
                        selected_file += 1
                    if selected_file >= file_offset + (max_y - 3):
                        file_offset += 1
                elif key in [curses.KEY_ENTER, 10, 13]:
                    if len(files):
                        file = files[selected_file]
                        if file.isdir():
                            status_message = ""
                            files = navigate_directory(file)
                        else:
                            status_message = f"{file.name} is a file, press 'e' to extract."
                elif key == ord('e'):
                    file = files[selected_file]
                    truncate_addstr(max_y - 2, 0, "Enter output directory (default: current): ")
                    stdscr.clrtoeol()
                    curses.echo()
                    output_dir = stdscr.getstr(max_y - 2, len("Enter output directory: ")).decode('utf-8').strip()
                    curses.noecho()
                    if not output_dir:
                        output_dir = '.'
                    status_message = inspector.extract_file_from_layer(selected_layer, file.name, output_dir)
                elif key == ord('s'):
                    stdscr.clear()
                    truncate_addstr(max_y - 2, 0, "Enter search query: ")
                    stdscr.clrtoeol()
                    curses.echo()
                    search_query = stdscr.getstr(max_y - 2, len("Enter search query: ")).decode('utf-8').strip()
                    curses.noecho()
                    search_results = inspector.search_files_in_layer(selected_layer, search_query, current_path)
                    if search_results:
                        current_screen = 'search'
                        selected_file = 0
                        file_offset = 0
                        status_message = f"Search results for '{search_query}'"
                    else:
                        status_message = f"No results found for '{search_query}'"
                elif key in [curses.KEY_LEFT, ord('b')]:
                    if current_path:
                        current_path = '/'.join(current_path.strip('/').split('/')[:-1])
                        files = inspector.list_files_in_layer(selected_layer, current_path)
                        selected_file = 0
                        file_offset = 0
                    else:
                        current_screen = 'layers'
                        status_message = ""
                elif key == ord('q'):
                    prev_screen = current_screen
                    current_screen = 'quit'
                    status_message = ""

            elif current_screen == 'search':
                if search_across_layers:
                    # Flatten the search results across layers for navigation
                    total_results = [(layer_idx, file) for layer_idx, files in search_results.items() for file in files]
                    display_search_results_across_layers(search_results, search_query, selected_file, file_offset)
                else:
                    # Search results within a single layer (list)
                    total_results = search_results
                    display_search_results(search_results, search_query)

                key = stdscr.getch()

                if key == curses.KEY_UP:
                    if selected_file > 0:
                        selected_file -= 1
                    if selected_file < file_offset:
                        file_offset -= 1
                elif key == curses.KEY_DOWN:
                    if selected_file < len(total_results) - 1:
                        selected_file += 1
                    if selected_file >= file_offset + (max_y - 3):
                        file_offset += 1
                elif key in [curses.KEY_ENTER, 10, 13]:
                    if search_across_layers:
                        # Navigate to the file in its layer when searching across layers
                        layer_idx, file = total_results[selected_file]
                        selected_layer = layer_idx
                        file_path = file.name
                    else:
                        # Navigate to the file within the same layer
                        file = total_results[selected_file]
                        file_path = file.name

                    # Get the directory path by removing the file name from the path
                    current_path = '/'.join(file_path.strip('/').split('/')[:-1])

                    # List files in the directory
                    files = inspector.list_files_in_layer(selected_layer, current_path)

                    # Find the index of the selected file in the folder
                    for i, f in enumerate(files):
                        if f.name == file_path:
                            selected_file = i
                            break
                    else:
                        selected_file = 0  # Fallback if the file is not found in the directory

                    # Switch to 'files' screen to display the folder contents and highlight the file
                    current_screen = 'files'
                    file_offset = max(0, selected_file - (max_y - 3) // 2)  # Center the selected file in the view
                    status_message = ""
                elif key in [curses.KEY_LEFT, ord('b')]:
                    current_screen = 'layers'
                    search_results = []
                    search_query = ""
                    status_message = ""
                elif key == ord('q'):
                    if search_across_layers:
                        current_screen = 'layers'
                    else:
                        current_screen = 'files'
                    search_results = []
                    search_query = ""
                    status_message = ""

    curses.wrapper(main)
