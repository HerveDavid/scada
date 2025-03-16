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
            use_name=False,
            center_name=False,
            diagonal_label=False,
            nodes_infos=False,
            tooltip_enabled=False,
            topological_coloring=True,
            component_library="Convergence",
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
    async def generate_network_area_diagram(
        network,
        element_id=None,
        depth=None,
        low_nominal_voltage_bound=None,
        high_nominal_voltage_bound=None,
    ):
        """
        Generates a network area diagram for a network element.
        Args:
            network: The network object
            element_id: The voltage level ID as the center of the sub network (optional)
            depth: The depth to control the size of the sub network (optional)
            low_nominal_voltage_bound: Lower bound for nominal voltage filtering (optional)
            high_nominal_voltage_bound: Upper bound for nominal voltage filtering (optional)
        Returns:
            tuple: (SVG diagram content, JSON metadata)
        """
        import tempfile
        import os
        import pypowsybl.network as pn

        # Configure diagram parameters
        params = pn.NadParameters(
            edge_name_displayed=True,
            id_displayed=False,
            edge_info_along_edge=True,
            power_value_precision=1,
            angle_value_precision=1,
            current_value_precision=0,
            voltage_value_precision=1,
            bus_legend=True,
            substation_description_displayed=True,
        )

        # Create temporary files for SVG
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as temp_svg:
            svg_path = temp_svg.name

        try:
            # Generate the appropriate network area diagram based on provided parameters
            if element_id and depth:
                if low_nominal_voltage_bound and high_nominal_voltage_bound:
                    # Use voltage level ID, depth, and voltage bounds
                    network.write_network_area_diagram_svg(
                        svg_path,
                        element_id,
                        depth,
                        low_nominal_voltage_bound=low_nominal_voltage_bound,
                        high_nominal_voltage_bound=high_nominal_voltage_bound,
                        nad_parameters=params,
                    )
                else:
                    # Use voltage level ID and depth only
                    network.write_network_area_diagram_svg(
                        svg_path, element_id, depth, nad_parameters=params
                    )
            elif low_nominal_voltage_bound and high_nominal_voltage_bound:
                # Use only voltage bounds
                network.write_network_area_diagram_svg(
                    svg_path,
                    low_nominal_voltage_bound=low_nominal_voltage_bound,
                    high_nominal_voltage_bound=high_nominal_voltage_bound,
                    nad_parameters=params,
                )
            else:
                # Generate for the full network
                network.write_network_area_diagram_svg(svg_path)

            # Read the generated SVG content
            with open(svg_path, "r") as svg_file:
                svg_content = svg_file.read()

            # Create metadata with the displayed voltage levels
            metadata = {}
            if element_id and depth:
                displayed_vls = (
                    network.get_network_area_diagram_displayed_voltage_levels(
                        element_id, depth
                    )
                )
                metadata["displayed_voltage_levels"] = (
                    displayed_vls.tolist()
                    if hasattr(displayed_vls, "tolist")
                    else displayed_vls
                )

            # Add filter information to metadata
            if low_nominal_voltage_bound or high_nominal_voltage_bound:
                metadata["filters"] = {
                    "low_nominal_voltage_bound": low_nominal_voltage_bound,
                    "high_nominal_voltage_bound": high_nominal_voltage_bound,
                }

            return svg_content, metadata

        finally:
            # Clean up temporary files
            if os.path.exists(svg_path):
                os.remove(svg_path)

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
