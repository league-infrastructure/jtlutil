import docker
import logging
from typing import List, Dict, Any, Optional
from .proc import Container, Service

logger = logging.getLogger(__name__)

class ProcessGroup:
    """Base class for managing both Docker Containers and Services."""

    def __init__(self, client: Any, env: Dict[str, str] = {}, 
                 network: List[str] = [], 
                 labels: Dict[str, str] = {}) -> None:
        """
        Initialize the process group.
        :param client: Docker client instance.
        """
        self.client = client
        self.env = env
        self.network = network
        self.labels = labels

    def run(self, name: str, image: str, **kwargs: Any) -> Any:
        """Create and run a new process (container or service)."""
        raise NotImplementedError

    def get(self, name_or_id: str) -> Any:
        """Retrieve a process (container or service) by name or ID."""
        raise NotImplementedError

    def list(self) -> List[Any]:
        """List all processes (containers or services)."""
        raise NotImplementedError



    def combine_lists(self, list1: List[str], list2: List[str]) -> List[str]:
        """Combine two lists."""
        return list(set(list1 + list2))

    def combine_dicts(self, dict1: Dict[str, str], dict2: Dict[str, str]) -> Dict[str, str]:
        """Combine two dictionaries."""
        combined = dict1.copy()
        combined.update(dict2)
        return combined


class ContainersManager(ProcessGroup):
    """Manages Docker Containers with a consistent interface."""
    
    def run(self, image: str, name: str = None, labels: Dict[str, str] = {}, 
            environment: Dict[str, str] = {}, ports: Dict[str, str] = {}, 
            volumes: Dict[str, str] = {}, network: Optional[str] = [], 
            restart_policy: Optional[str] = None, **kwargs: Dict[str,Any]) -> Container:
        """
        Run a new container.
        :param name: Name of the container.
        :param image: Docker image to use.
        :param labels: Labels to apply to the container.
        :param environment: Environment variables for the container.
        :param ports: Port mappings for the container.
        :param volumes: Volume mappings for the container.
        :param network: Network for the container.
        :param restart_policy: Restart policy for the container.
        :param kwargs: Additional parameters.
        :return: A Container object.
        """
        
        print("!!!", self.network, network)
        
        network = self.combine_lists(self.network, network)

        container = self.client.containers.run(
            image=image,
            name=name,
            detach=True,
            labels=self.combine_dicts(self.labels, labels),
            environment=self.combine_dicts(self.env, environment),
            ports=ports,
            volumes=volumes,
            restart_policy=restart_policy,
            **kwargs
        )
        
         # Connect to additional networks if specified
        for net in (network or []):
            network = self.client.networks.get(net)           
            network.connect(container)
            
        
        return Container(self.client, container)

    def get(self, name_or_id: str) -> Any:
        """Retrieve a container by name or ID."""
        container = self.client.containers.get(name_or_id)
        return Container(self.client, container)

    def list(self, filters: Dict, all=False, status=None, **kwargs: Any) -> List[Any]:
        """List all containers."""
        return [Container(self.client, cont) for cont in self.client.containers.list(filters=filters, all=all, **kwargs)]

    def only_one_container(self, containers: List[Any], reset: bool = False) -> None:
        """Ensure only one container is running."""
        if containers:
            logger.debug(f"Found {len(containers)} containers")
            first, rest = containers[0], containers[1:]
            
            for container in rest:
                logger.debug(f"Removing container {container.name}")
                container.remove(force=True)
            
            #if first is stopped, start it. 
            if reset:
                logger.debug(f"Destroying container {first.name} because reset is True")
                first.remove(force=True)
        
            elif first.status == "exited":
                logger.debug(f"Starting container {first.name}")
                first.start()
                return first
            else:
                logger.debug(f"Container {first.name} is already running")
                return first
            
        return None

class ServicesManager(ProcessGroup):
    """Manages Docker Services (Swarm mode) with a consistent interface."""
    
    def run(self, image: str, name: str=None, maxreplicas: int=1,
            labels: Dict[str, str] = {}, 
            environment: Dict[str, str] = {}, mounts: List[str] = [], 
            network: List[str] = [], restart_policy: Optional[str] = None, 
            **kwargs: Any) -> Any:
        """
        Create a new service.
        :param name: Name of the service.
        :param image: Docker image to use.
        :param labels: Labels to apply to the service.
        :param environment: Environment variables for the service.
        :param mounts: Mounts for the service.
        :param networks: Networks for the service.
        :param restart_policy: Restart policy for the service.
        :param kwargs: Additional parameters.
        :return: A Service object.
        """
        
        network = self.combine_lists(self.network, network)

        # Convert environment dict to list of key=value strings
        env=self.combine_dicts(self.env, environment)
        env_list = [f"{key}={value}" for key, value in env.items()]

        service = self.client.services.create(
            image=image,
            name=name,
            maxreplicas=maxreplicas,
            labels=self.combine_dicts(self.labels, labels),
            container_labels=self.combine_dicts(self.labels, labels),
            env=env_list,
            mounts=mounts,
            networks=network,
            restart_policy=restart_policy,
            **kwargs
        )
        return Service(self.client, service)

    def get(self, name_or_id: str) -> Any:
        """Retrieve a service by name or ID."""
        service = self.client.services.get(name_or_id)
        return Service(self.client, service)

    def list(self, filters: Dict = None, status: bool = False, all=None,  **kwargs: Any) -> List[Any]:
        """List all services."""
        return [Service(self.client, svc) for svc in self.client.services.list(filters=filters, status=status, **kwargs)]
