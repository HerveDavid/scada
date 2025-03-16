from quart import request, jsonify, make_response, json
from domain.network.services.network_service import NetworkService

import os


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def register_api_routes(app):
    @app.route("/api/v1/config/iidm", methods=["POST"])
    async def upload_iidm():
        """Endpoint to receive a large IIDM file via POST and convert it to JSON."""
        try:
            # First check if the request contains a file
            files = await request.files
            if "file" not in files:
                return {"error": "No file found in the request"}, 400

            file = files.get("file")

            # Generate a unique filename
            import uuid

            unique_filename = f"{uuid.uuid4().hex}.xiidm"
            destination = os.path.join(UPLOAD_FOLDER, unique_filename)

            # Write the file to disk using direct stream
            # but ensure the file is processed in chunks
            await file.save(destination)

            # Process the file
            app.logger.info(
                f"File received and saved to {destination}. Processing in progress..."
            )
            error = await NetworkService.process_iidm_file(destination)

            if error:
                os.remove(destination)
                return {"error": f"Error during processing: {error}"}, 400

            app.logger.info(f"File received and successfully saved to {destination}.")

            return {"status": "IIDM file loaded"}, 201

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            app.logger.error(f"Error during upload: {str(e)}\n{error_details}")
            return {"error": f"Error during upload: {str(e)}"}, 500

    @app.route("/api/v1/config/iidm", methods=["GET"])
    async def get_network_json():
        """
        Endpoint to get the current network in JSON format.

        Returns:
            The network in JSON format or an error message if no network is available
        """
        try:
            # Get the current network
            network = await NetworkService.get_current_network()

            if not network:
                return {"error": "No network available"}, 404

            # Convert the network to JSON
            json_content, error = await NetworkService.convert_network_to_json(network)

            if error:
                return {"error": f"Error converting network to JSON: {error}"}, 500

            return jsonify(json_content)

        except Exception as e:
            # Log the error for debugging
            app.logger.error(f"Error when getting network JSON: {str(e)}")
            return {"error": f"Unable to get network JSON: {str(e)}"}, 500

    @app.route("/api/v1/network/diagram/line/<string:id>", methods=["GET"])
    async def get_single_line_diagram(id):
        """
        Endpoint to generate and return a single line diagram (SVG) for a voltage level or substation ID.

        Args:
            id: The identifier of the voltage level or substation

        Returns:
            The SVG diagram or an error message if the ID doesn't exist
        """
        try:
            # Get the current network
            network = await NetworkService.get_current_network()

            if not network:
                return {"error": "No network available"}, 404

            # Check if the ID exists in the network
            if not await NetworkService.element_exists(network, id):
                return {
                    "error": f"The identifier '{id}' doesn't exist in the network"
                }, 404

            # Generate the SVG and metadata
            svg_content, metadata = await NetworkService.generate_single_line_diagram(
                network, id
            )

            # Return format according to the request parameter
            if request.args.get("format") == "json":
                # Return SVG + metadata in JSON format
                return jsonify({"svg": svg_content, "metadata": metadata})
            else:
                # Return the SVG directly with the proper headers
                response = await make_response(svg_content)
                response.headers["Content-Type"] = "image/svg+xml"
                response.headers["Content-Disposition"] = (
                    f"inline; filename={id}_diagram.svg"
                )
                # Add metadata in a custom header
                response.headers["X-Diagram-Metadata"] = json.dumps(metadata)

                return response

        except Exception as e:
            # Log the error for debugging
            app.logger.error(f"Error when generating diagram for {id}: {str(e)}")
            return {"error": f"Unable to generate diagram: {str(e)}"}, 500

    @app.route("/api/v1/network/diagram/line/<string:id>/metadata", methods=["GET"])
    async def get_single_line_diagram_metadata(id):
        """
        Endpoint to get only the metadata of a diagram.
        """
        try:
            network = await NetworkService.get_current_network()

            if not network:
                return {"error": "No network available"}, 404

            if not await NetworkService.element_exists(network, id):
                return {
                    "error": f"The identifier '{id}' doesn't exist in the network"
                }, 404

            _, metadata = await NetworkService.generate_single_line_diagram(network, id)

            return jsonify(metadata)

        except Exception as e:
            app.logger.error(f"Error when retrieving metadata for {id}: {str(e)}")
            return {"error": f"Unable to retrieve metadata: {str(e)}"}, 500

    @app.route("/api/v1/network/diagram/area", methods=["GET"])
    async def get_network_area_diagram():
        """
        Endpoint to generate and return a network area diagram (SVG).

        Query parameters:
            voltage_level_id: Optional ID of the voltage level to be used as center
            depth: Optional depth to control the size of the sub network
            low_nominal_voltage: Optional lower bound for nominal voltage filtering
            high_nominal_voltage: Optional upper bound for nominal voltage filtering

        Returns:
            The SVG diagram or an error message
        """
        try:
            # Get the current network
            network = await NetworkService.get_current_network()

            if not network:
                return {"error": "No network available"}, 404

            # Get query parameters
            voltage_level_id = request.args.get("voltage_level_id")
            depth = request.args.get("depth")
            low_nominal_voltage = request.args.get("low_nominal_voltage")
            high_nominal_voltage = request.args.get("high_nominal_voltage")

            # Convert parameters to the correct types
            if depth:
                try:
                    depth = int(depth)
                except ValueError:
                    return {"error": "Depth must be an integer"}, 400

            if low_nominal_voltage:
                try:
                    low_nominal_voltage = float(low_nominal_voltage)
                except ValueError:
                    return {"error": "Low nominal voltage must be a number"}, 400

            if high_nominal_voltage:
                try:
                    high_nominal_voltage = float(high_nominal_voltage)
                except ValueError:
                    return {"error": "High nominal voltage must be a number"}, 400

            # Check if voltage_level_id exists in the network
            if voltage_level_id and not await NetworkService.element_exists(
                network, voltage_level_id
            ):
                return {
                    "error": f"The voltage level identifier '{voltage_level_id}' doesn't exist in the network"
                }, 404

            # Generate the SVG and metadata
            svg_content, metadata = await NetworkService.generate_network_area_diagram(
                network,
                voltage_level_id,
                depth,
                low_nominal_voltage,
                high_nominal_voltage,
            )

            # Return format according to the request parameter
            if request.args.get("format") == "json":
                # Return SVG + metadata in JSON format
                return jsonify({"svg": svg_content, "metadata": metadata})
            else:
                # Return the SVG directly with the proper headers
                response = await make_response(svg_content)
                response.headers["Content-Type"] = "image/svg+xml"
                filename = voltage_level_id or "network"
                response.headers["Content-Disposition"] = (
                    f"inline; filename={filename}_area_diagram.svg"
                )
                # Add metadata in a custom header
                response.headers["X-Diagram-Metadata"] = json.dumps(metadata)

                return response

        except Exception as e:
            # Log the error for debugging
            app.logger.error(f"Error when generating network area diagram: {str(e)}")
            return {"error": f"Unable to generate network area diagram: {str(e)}"}, 500

    @app.route("/api/v1/network/diagram/area/metadata", methods=["GET"])
    async def get_network_area_diagram_metadata():
        """
        Endpoint to get only the metadata of a network area diagram.

        Query parameters:
            voltage_level_id: Optional ID of the voltage level to be used as center
            depth: Optional depth to control the size of the sub network
            low_nominal_voltage: Optional lower bound for nominal voltage filtering
            high_nominal_voltage: Optional upper bound for nominal voltage filtering
        """
        try:
            network = await NetworkService.get_current_network()

            if not network:
                return {"error": "No network available"}, 404

            # Get query parameters
            voltage_level_id = request.args.get("voltage_level_id")
            depth = request.args.get("depth")
            low_nominal_voltage = request.args.get("low_nominal_voltage")
            high_nominal_voltage = request.args.get("high_nominal_voltage")

            # Convert parameters to the correct types
            if depth:
                try:
                    depth = int(depth)
                except ValueError:
                    return {"error": "Depth must be an integer"}, 400

            if low_nominal_voltage:
                try:
                    low_nominal_voltage = float(low_nominal_voltage)
                except ValueError:
                    return {"error": "Low nominal voltage must be a number"}, 400

            if high_nominal_voltage:
                try:
                    high_nominal_voltage = float(high_nominal_voltage)
                except ValueError:
                    return {"error": "High nominal voltage must be a number"}, 400

            # Check if voltage_level_id exists in the network
            if voltage_level_id and not await NetworkService.element_exists(
                network, voltage_level_id
            ):
                return {
                    "error": f"The voltage level identifier '{voltage_level_id}' doesn't exist in the network"
                }, 404

            # Get only the metadata
            _, metadata = await NetworkService.generate_network_area_diagram(
                network,
                voltage_level_id,
                depth,
                low_nominal_voltage,
                high_nominal_voltage,
            )

            return jsonify(metadata)

        except Exception as e:
            app.logger.error(
                f"Error when retrieving network area diagram metadata: {str(e)}"
            )
            return {
                "error": f"Unable to retrieve network area diagram metadata: {str(e)}"
            }, 500
