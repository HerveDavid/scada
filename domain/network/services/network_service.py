import pypowsybl.network as pn


class NetworkService:
    _current_network = None

    @staticmethod
    async def get_current_network():
        """Gets the current network."""
        return NetworkService._current_network

    @staticmethod
    async def set_current_network(network):
        """Sets the current network."""
        NetworkService._current_network = network
        return network

    @staticmethod
    async def process_iidm_file(file_path):
        """
        Loads an IIDM file and returns its JSON representation
        """
        try:
            # Load the network from the XML file
            network = pn.load(file_path)
            await NetworkService.set_current_network(network)
            return None
        except Exception as e:
            return str(e)

    @staticmethod
    async def element_exists(network, element_id):
        """Checks if an element exists in the network."""
        try:
            # Check in voltage levels
            voltage_levels = network.get_voltage_levels()
            if element_id in voltage_levels.index:
                return True
            # Check in substations
            substations = network.get_substations()
            if element_id in substations.index:
                return True
            return False
        except Exception:
            return False

    @staticmethod
    async def generate_single_line_diagram(network, element_id):
        """
        Generates a single line diagram for a network element.
        Args:
            network: The network object
            element_id: The element ID (voltage level or substation)
        Returns:
            tuple: (SVG diagram content, JSON metadata)
        """
        import tempfile
        import os
        import json
        import pypowsybl.network as pn

        # Configure diagram parameters
        params = pn.SldParameters(
            use_name=True, topological_coloring=True, component_library="Convergence"
        )

        # Create temporary files for SVG and metadata
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as temp_svg:
            svg_path = temp_svg.name
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_metadata:
            metadata_path = temp_metadata.name

        try:
            # Use the file path to generate the SVG with metadata
            network.write_single_line_diagram_svg(
                container_id=element_id,
                svg_file=svg_path,
                metadata_file=metadata_path,
                parameters=params,
            )

            # Read the generated SVG content
            with open(svg_path, "r") as svg_file:
                svg_content = svg_file.read()

            # Read the generated metadata
            with open(metadata_path, "r") as metadata_file:
                metadata_content = json.load(metadata_file)

            return svg_content, metadata_content

        finally:
            # Clean up temporary files
            if os.path.exists(svg_path):
                os.remove(svg_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)

    @staticmethod
    async def convert_network_to_json(network):
        """Converts a network to JSON format."""
        try:
            import tempfile
            import os
            import json

            # Create a temporary file for the JSON output
            with tempfile.NamedTemporaryFile(suffix=".json", delete=True) as temp_json:
                json_path = temp_json.name

            try:
                # # Export network to JSON format
                # network.save("somewhere.jiidm", format="JIIDM")

                # Read the generated JSON content
                with open(json_path, "r") as json_file:
                    json_content = json.load(json_file)

                return json_content, None
            except Exception as e:
                return None, str(e)
            finally:
                # Clean up temporary file
                if os.path.exists(json_path):
                    os.remove(json_path)
        except Exception as e:
            return None, str(e)
