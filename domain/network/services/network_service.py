import os
import json
import tempfile
import asyncio
import logging
import glob
from contextlib import contextmanager
from typing import Optional, Tuple, Dict, Any

import pypowsybl.network as pn


class NetworkService:
    """Service for electrical network operations using pypowsybl with persistence support."""

    # Configuration constants
    SLD_PARAMETERS = {
        "use_name": False,
        "center_name": False,
        "diagonal_label": False,
        "nodes_infos": False,
        "tooltip_enabled": False,
        "topological_coloring": True,
        "component_library": "Convergence",
    }

    NAD_PARAMETERS = {
        "edge_name_displayed": True,
        "id_displayed": False,
        "edge_info_along_edge": True,
        "power_value_precision": 1,
        "angle_value_precision": 1,
        "current_value_precision": 0,
        "voltage_value_precision": 1,
        "bus_legend": True,
        "substation_description_displayed": True,
    }

    # Storage paths
    UPLOAD_FOLDER = "uploads"
    LAST_NETWORK_FILE = os.path.join(UPLOAD_FOLDER, "last_loaded_network.json")

    def __init__(self):
        """Initialize the NetworkService."""
        self._current_network = None
        self._current_file_path = None

        # Ensure upload folder exists
        os.makedirs(self.UPLOAD_FOLDER, exist_ok=True)

    @property
    def current_network(self):
        """Get the current network."""
        return self._current_network

    @current_network.setter
    def current_network(self, network):
        """Set the current network."""
        self._current_network = network

    @property
    def current_file_path(self):
        """Get the path to the currently loaded network file."""
        return self._current_file_path

    @contextmanager
    def _temp_file(self, suffix: str):
        """Context manager for creating and cleaning up temporary files.

        Args:
            suffix: File extension (e.g., '.svg', '.json')

        Yields:
            str: Path to the temporary file
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        file_path = temp_file.name
        temp_file.close()

        try:
            yield file_path
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    async def process_iidm_file(self, file_path: str) -> Optional[str]:
        """Load an IIDM file and set it as the current network.

        Args:
            file_path: Path to the IIDM file

        Returns:
            Optional[str]: Error message if loading fails, None otherwise
        """
        try:
            network = pn.load(file_path)
            self.current_network = network
            self._current_file_path = file_path

            # Save information about the last loaded network
            self._save_network_metadata()

            return None
        except Exception as e:
            return f"Error loading network: {str(e)}"

    def _save_network_metadata(self):
        """Save metadata about the current network for persistence."""
        try:
            metadata = {
                "file_path": self._current_file_path,
                "timestamp": asyncio.get_event_loop().time(),
            }
            with open(self.LAST_NETWORK_FILE, "w") as f:
                json.dump(metadata, f)
        except Exception as e:
            logging.error(f"Failed to save network metadata: {str(e)}")

    async def load_last_network(self) -> Optional[str]:
        """Load the most recently used network file.

        Returns:
            Optional[str]: Error message if loading fails, None otherwise
        """
        try:
            # Check if metadata file exists
            if not os.path.exists(self.LAST_NETWORK_FILE):
                # Try to find the most recent file in the uploads folder
                return await self._load_most_recent_network()

            # Load the metadata
            with open(self.LAST_NETWORK_FILE, "r") as f:
                metadata = json.load(f)

            file_path = metadata.get("file_path")
            if not file_path or not os.path.exists(file_path):
                # Metadata exists but file is missing, try to find most recent
                return await self._load_most_recent_network()

            # Load the network from the saved path
            return await self.process_iidm_file(file_path)

        except Exception as e:
            return f"Failed to load last network: {str(e)}"

    async def _load_most_recent_network(self) -> Optional[str]:
        """Find and load the most recent network file in uploads folder.

        Returns:
            Optional[str]: Error message if loading fails, None otherwise
        """
        try:
            # Find all network files in the uploads folder
            files = glob.glob(os.path.join(self.UPLOAD_FOLDER, "*.xiidm"))

            if not files:
                return "No previous network files found"

            # Get the most recent file
            latest_file = max(files, key=os.path.getmtime)

            # Load the network
            return await self.process_iidm_file(latest_file)

        except Exception as e:
            return f"Failed to load most recent network: {str(e)}"

    async def cleanup_old_networks(self, max_files: int = 5) -> None:
        """Remove old network files, keeping only the most recent ones.

        Args:
            max_files: Maximum number of files to keep
        """
        try:
            # Find all network files in the uploads folder
            files = glob.glob(os.path.join(self.UPLOAD_FOLDER, "*.xiidm"))

            if len(files) <= max_files:
                return

            # Sort files by modification time, oldest first
            files.sort(key=os.path.getmtime)

            # Remove oldest files, keeping only max_files
            for file_path in files[:-max_files]:
                try:
                    os.remove(file_path)
                    logging.info(f"Removed old network file: {file_path}")
                except Exception as e:
                    logging.error(
                        f"Failed to remove old network file {file_path}: {str(e)}"
                    )

        except Exception as e:
            logging.error(f"Error during network cleanup: {str(e)}")

    async def element_exists(self, element_id: str) -> bool:
        """Check if an element exists in the current network.

        Args:
            element_id: The element ID to check

        Returns:
            bool: True if the element exists, False otherwise
        """
        if not self.current_network:
            return False

        try:
            # Check in voltage levels
            voltage_levels = self.current_network.get_voltage_levels()
            if element_id in voltage_levels.index:
                return True

            # Check in substations
            substations = self.current_network.get_substations()
            if element_id in substations.index:
                return True

            return False
        except Exception:
            return False

    async def generate_single_line_diagram(
        self, element_id: str
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Generate a single line diagram for a network element.

        Args:
            element_id: The element ID (voltage level or substation)

        Returns:
            tuple: (SVG diagram content, JSON metadata) or (None, None) on error
        """
        if not self.current_network:
            return None, None

        # Configure diagram parameters
        params = pn.SldParameters(**self.SLD_PARAMETERS)

        try:
            with (
                self._temp_file(".svg") as svg_path,
                self._temp_file(".json") as metadata_path,
            ):
                # Generate the SVG with metadata
                self.current_network.write_single_line_diagram_svg(
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
        except Exception as e:
            return None, {"error": str(e)}

    async def generate_network_area_diagram(
        self,
        element_id: Optional[str] = None,
        depth: Optional[int] = None,
        low_nominal_voltage_bound: Optional[float] = None,
        high_nominal_voltage_bound: Optional[float] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Generate a network area diagram.

        Args:
            element_id: The voltage level ID as the center of the sub network
            depth: The depth to control the size of the sub network
            low_nominal_voltage_bound: Lower bound for nominal voltage filtering
            high_nominal_voltage_bound: Upper bound for nominal voltage filtering

        Returns:
            tuple: (SVG diagram content, JSON metadata) or (None, None) on error
        """
        if not self.current_network:
            return None, None

        # Configure diagram parameters
        params = pn.NadParameters(**self.NAD_PARAMETERS)

        try:
            with self._temp_file(".svg") as svg_path:
                kwargs = {"nad_parameters": params}

                # Add optional parameters if provided
                if low_nominal_voltage_bound is not None:
                    kwargs["low_nominal_voltage_bound"] = low_nominal_voltage_bound
                if high_nominal_voltage_bound is not None:
                    kwargs["high_nominal_voltage_bound"] = high_nominal_voltage_bound

                # Generate the appropriate network area diagram based on provided parameters
                if element_id and depth:
                    self.current_network.write_network_area_diagram_svg(
                        svg_path, element_id, depth, **kwargs
                    )
                else:
                    self.current_network.write_network_area_diagram_svg(
                        svg_path, **kwargs
                    )

                # Read the generated SVG content
                with open(svg_path, "r") as svg_file:
                    svg_content = svg_file.read()

                # Create metadata with the displayed voltage levels
                metadata = {}
                if element_id and depth:
                    displayed_vls = self.current_network.get_network_area_diagram_displayed_voltage_levels(
                        element_id, depth
                    )
                    metadata["displayed_voltage_levels"] = (
                        displayed_vls.tolist()
                        if hasattr(displayed_vls, "tolist")
                        else displayed_vls
                    )

                # Add filter information to metadata
                if (
                    low_nominal_voltage_bound is not None
                    or high_nominal_voltage_bound is not None
                ):
                    metadata["filters"] = {
                        "low_nominal_voltage_bound": low_nominal_voltage_bound,
                        "high_nominal_voltage_bound": high_nominal_voltage_bound,
                    }

                return svg_content, metadata
        except Exception as e:
            return None, {"error": str(e)}

    async def convert_network_to_json(
        self,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Convert the current network to JSON format.

        Returns:
            tuple: (JSON content, error message) where one will be None
        """
        if not self.current_network:
            return None, "No network loaded"

        try:
            with self._temp_file(".jiidm") as json_path:
                # Export network to JSON format
                self.current_network.save(json_path, format="JIIDM")

                # Read the generated JSON content
                with open(json_path, "r", encoding="utf-8") as json_file:
                    json_content = json.load(json_file)

                return json_content, None
        except json.JSONDecodeError as je:
            return None, f"Error parsing JSON: {str(je)}"
        except Exception as e:
            return None, f"Error converting network to JSON: {str(e)}"
