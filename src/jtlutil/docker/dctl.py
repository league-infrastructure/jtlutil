import docker
import logging
from slugify import slugify
from pathlib import Path
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

import docker


def process_port_bindings(ports):
    # Prepare port bindings
    if isinstance(ports, dict):
        port_bindings = {f"{port}/tcp": host_port for port, host_port in (ports or {}).items()}
    elif isinstance(ports, list):
        port_bindings = {f"{port}/tcp": None for port in (ports or [])}
    else:
        port_bindings = None
        
    return port_bindings

def make_container_name(username):
    return f"{slugify(username)}"   
    
    
def get_port_from_container(container, container_port):
    """
    Returns the mapped host port for a given container port from a container object.

    Args:
        container (docker.models.containers.Container): The container object.
        container_port (str): The container port (e.g., '8080').

    Returns:
        str: The mapped host port if available, None otherwise.
    """
    try:
        # Get the port bindings
        ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
        port_key = f"{container_port}/tcp"

        if port_key in ports and ports[port_key]:
            # Return the first HostPort found
            return ports[port_key][0].get("HostPort")
        else:
            logger.debug(f"No mapping found for port {container_port}")
            return None
    except Exception as e:
        logger.error(f"Error getting mapped port: {e}")
        return None

# Update get_mapped_port to use the new function
def get_mapped_port(client, container_id, container_port):
    """
    Returns the mapped host port for a given container port.

    Args:
        container_id (str): The ID or name of the container.
        container_port (str): The container port (e.g., '8080').

    Returns:
        str: The mapped host port if available, None otherwise.
    """
    try:
        # Inspect the container
        container = client.containers.get(container_id)
        return get_port_from_container(container, container_port)
    except docker.errors.NotFound:
        logger.error(f"Container with ID {container_id} not found.")
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None