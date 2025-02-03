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


def define_cs_container(config, image, username, hostname_template, env_vars={}, port=None):
    # Create the container
    
    name = slugify(username)
    container_name = make_container_name(username)
       
    password = "code4life"
    
    hostname = hostname_template.format(username=slugify(username))

    _env_vars = {
        "PASSWORD": password,
        "DISPLAY": ":0",
        "VNC_URL": f"https://{hostname}/vnc/",
        "KST_REPORTING_URL": config.KST_REPORTING_URL,
        "KST_CONTAINER_ID": name,
		"KST_REPORT_RATE": config.KST_REPORT_RATE if hasattr(config, "KST_REPORT_RATE") else 30,
        "CS_DISABLE_GETTING_STARTED_OVERRIDE": "1" # Disable the getting started page
    }
    
    env_vars = {**_env_vars, **env_vars}
    
    labels = {
        "jtl": 'true', 
        "jtl.codeserver": 'true',  
        "jtl.codeserver.username": username,
        "jt.codeserver.password": password,
        "jtl.codeserver.start_time": datetime.now(pytz.timezone('America/Los_Angeles')).isoformat(),
                
        "caddy": hostname,
        "caddy.@ws.0_header": "Connection *Upgrade*",
        "caddy.@ws.1_header": "Upgrade websocket",
        "caddy.0_route.handle": "/websockify*",
        "caddy.0_route.handle.reverse_proxy": "@ws {{upstreams 6080}}",
        "caddy.1_route.handle": "/vnc/*",
        "caddy.1_route.handle_path": "/vnc/*",
        "caddy.1_route.handle_path.reverse_proxy": "{{upstreams 6080}}",
        "caddy.2_route.handle": "/*",
        "caddy.2_route.handle.reverse_proxy": "{{upstreams 8080}}"
    }
    
    # This part sets up a port redirection for development, where we don't have
    # a reverse proxy in front of the container.
    
    internal_port = "8080"
    
    if port is True:
        ports = [internal_port]
    elif port is not None and port is not False:
        ports = [f"{port}:{internal_port}"]
    else:
        ports = None
    
    
    return {
        "name": container_name,
        "image": image,
        "labels": labels,
        "environment": env_vars,
        "ports": ports,
        "network" : ["caddy", "jtlctl"],
        
    }
    
    
    
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