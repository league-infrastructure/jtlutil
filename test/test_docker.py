import tenacity 
import namesgenerator
from slugify import slugify
import docker
import logging
import pathlib

from jtlutil.docker import *
from jtlutil.config import get_config

cwd = pathlib.Path(__file__).parent.absolute()

config = get_config(cwd / 'config/swarm.env')

networks = ["caddy"]

hw_image = 'crccheck/hello-world'
hello_hash = 'a7bab6a7dafadc0c4046650d46e769a1' # md5 hash of "Hello, World!"


def _test_hello_world(manager):
    """Start up a Hello World service and check that it is working."""
    client = docker.DockerClient(base_url=config.SSH_URI )
    cm = manager

    @tenacity.retry(wait=tenacity.wait_fixed(2), stop=tenacity.stop_after_attempt(8))
    def check_hello_hash(s):
        import requests
        import hashlib
        
        response_text = requests.get(f"https://{s.labels['caddy']}").text
        assert hello_hash == hashlib.md5(response_text.encode()).hexdigest()

    random_name = namesgenerator.get_random_name()

    labels = {
        "caddy": f'{slugify(random_name)}.doswarm.jointheleague.org',
        "caddy.reverse_proxy": "{{upstreams 8000}}",
        "jtl.test": "true",
    }

    s = cm.run(hw_image, name=random_name, labels=labels, network=networks)
    print(s.name, s.labels['caddy'])

    check_hello_hash(s)

def test_hello_world_service():
    """Start up a Hello World service and check that it is working."""
    client = docker.DockerClient(base_url=config.SSH_URI )
    cm = ServicesManager(client)

    _test_hello_world(cm)
    
def test_hello_world_container():
    """Start up a Hello World service and check that it is working."""
    client = docker.DockerClient(base_url=config.SSH_URI )
    cm = ContainersManager(client)

    _test_hello_world(cm)