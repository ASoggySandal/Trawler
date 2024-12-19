import os
import json
import tarfile

class ContainerImageInspector:
    def __init__(self, local_image_path=None):
        self.layers = []
        self.layer_commands = []  # Store layer commands in order from history
        self.local_image_path = local_image_path
        if local_image_path:
            self._load_local_image(local_image_path)

    def _load_local_image(self, local_image_path):
        """Load a local container image file, extract layers, and retrieve commands."""
        print(f"Loading image from {local_image_path}...")

        mode = 'r:gz' if local_image_path.endswith(('.tar.gz', '.tgz')) else 'r'
        with tarfile.open(local_image_path, mode) as tar:
            manifest_file = tar.extractfile("manifest.json")
            manifest_data = json.load(manifest_file)
            config_file_name = manifest_data[0]["Config"]
            layer_paths = manifest_data[0]["Layers"]

            self.layers = [os.path.dirname(layer_path) for layer_path in layer_paths]

            config_file = tar.extractfile(config_file_name)
            config_data = json.load(config_file)

            history = config_data.get("history", [])
            layer_index = 0

            for history_entry in history:
                is_empty = history_entry.get("empty_layer", False)
                if not is_empty:
                    if layer_index < len(self.layers):
                        layer_name = self.layers[layer_index]
                        created_by = history_entry.get("created_by", "Unknown command")
                        self.layer_commands.append((layer_name, created_by))
                        layer_index += 1

    def get_layer_command(self, layer_name):
        """Return the command associated with a layer, skipping empty layers."""
        for name, command in self.layer_commands:
            if name == layer_name:
                return command
        return "Unknown command"

    def list_files_in_layer(self, layer_idx, current_path=''):
        """List all files in a specific layer, optionally in a directory."""
        layer_name = self.layers[layer_idx]
        mode = 'r:gz' if self.local_image_path.endswith(('.tar.gz', '.tgz')) else 'r'
        with tarfile.open(self.local_image_path, mode) as tar:
            layer_files = [m for m in tar.getmembers() if m.name.startswith(layer_name) and 'layer.tar' in m.name]
            if layer_files:
                layer_tar = tar.extractfile(layer_files[0])
                if layer_tar is None:
                    return []
                with tarfile.open(fileobj=layer_tar) as layer_tarfile:
                    files = layer_tarfile.getmembers()
                    filtered_files = [
                        f for f in files if f.name.startswith(current_path)
                        and f.name != current_path
                        and '/' not in f.name[len(current_path):].strip('/')
                    ]
                    return sorted(filtered_files, key=lambda x: (not x.isdir(), x.name.lower()))
        return []

    def search_files_in_layer(self, layer_idx, query, current_path=''):
        """Search for files or folders by name in the current layer, showing full paths."""
        layer_name = self.layers[layer_idx]
        mode = 'r:gz' if self.local_image_path.endswith(('.tar.gz', '.tgz')) else 'r'
        with tarfile.open(self.local_image_path, mode) as tar:
            layer_files = [m for m in tar.getmembers() if m.name.startswith(layer_name) and 'layer.tar' in m.name]
            if layer_files:
                layer_tar = tar.extractfile(layer_files[0])
                if layer_tar is None:
                    return []
                with tarfile.open(fileobj=layer_tar) as layer_tarfile:
                    files = layer_tarfile.getmembers()
                    filtered_files = [
                        f for f in files if f.name.startswith(current_path)
                        and query.lower() in f.name.lower()
                    ]
                    return filtered_files
        return []

    def extract_file_from_layer(self, layer_idx, file_name, output_dir='.'):
        """Extract a specific file or folder from the layer.tar in a given layer."""
        layer_name = self.layers[layer_idx]
        mode = 'r:gz' if self.local_image_path.endswith(('.tar.gz', '.tgz')) else 'r'
        with tarfile.open(self.local_image_path, mode) as tar:
            layer_files = [m for m in tar.getmembers() if m.name.startswith(layer_name) and 'layer.tar' in m.name]
            if layer_files:
                layer_tar = tar.extractfile(layer_files[0])
                if layer_tar is None:
                    return f"Could not extract layer.tar from layer {layer_name}"
                with tarfile.open(fileobj=layer_tar) as layer_tarfile:
                    try:
                        member = layer_tarfile.getmember(file_name)
                        if member.isdir():
                            layer_tarfile.extractall(path=output_dir, members=[m for m in layer_tarfile.getmembers() if m.name.startswith(file_name)])
                            return f"Extracted directory {file_name} to {output_dir}"
                        else:
                            output_path = os.path.join(output_dir, os.path.basename(file_name))
                            with open(output_path, 'wb') as f:
                                f.write(layer_tarfile.extractfile(member).read())
                            return f"Extracted {file_name} to {output_path}"
                    except KeyError:
                        return f"File or directory {file_name} not found in layer {layer_name}"

    def search_files_across_layers(self, query):
        """Search for files across all layers."""
        results = {}
        mode = 'r:gz' if self.local_image_path.endswith(('.tar.gz', '.tgz')) else 'r'
        with tarfile.open(self.local_image_path, mode) as tar:
            for layer_idx, layer_name in enumerate(self.layers):
                layer_files = [m for m in tar.getmembers() if m.name.startswith(layer_name) and 'layer.tar' in m.name]
                if layer_files:
                    layer_tar = tar.extractfile(layer_files[0])
                    if layer_tar is None:
                        continue
                    with tarfile.open(fileobj=layer_tar) as layer_tarfile:
                        files = layer_tarfile.getmembers()
                        matches = [f for f in files if query.lower() in f.name.lower()]
                        if matches:
                            results[layer_idx] = matches
        return results