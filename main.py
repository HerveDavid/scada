from quart import Quart
from interfaces.api.routes import register_api_routes
from interfaces.sse.routes import register_sse_routes


def create_app():
    app = Quart(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 Mo

    # Register all routes
    register_sse_routes(app)
    register_api_routes(app)

    return app


if __name__ == "__main__":
    import asyncio
    import hypercorn.asyncio
    import hypercorn.config

    config = hypercorn.config.Config()
    config.h2_protocol = True
    config.insecure_bind = ["0.0.0.0:8000"]
    config.alpn_protocols = ["h2c", "http/1.1"]

    config.read_timeout = 300
    config.write_timeout = 300

    config.request_max_size = 500 * 1024 * 1024  # 500 Mo
    config.timeout_keep_alive = 600  # 10 minutes
    config.worker_class = "asyncio"  # Use asyncio for stability

    config.graceful_timeout = 300.0
    config.keep_alive_timeout = 300.0

    app = create_app()
    asyncio.run(hypercorn.asyncio.serve(app, config))
