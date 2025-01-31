import docker
import logging
from typing import List, Dict, Any, Optional
from .proc import Container, Service

logger = logging.getLogger(__name__)

class ProcessGroup:
    """Base class for managing both Docker Containers and Services."""

    def __init__(self, client: Any, env: Optional[Dict[str, str]] = None, 
                 network: Optional[List[str]] = None, 
                 labels: Optional[Dict[str, str]] = None) -> None:
        """
        Initialize the process group.
        :param client: Docker client instance.
        """
        self.client = client
        self.env = env or {}
        self.network = network or []
        self.labels = labels or {}
        
        self.info = self.client.info()
        

    @property
    def name(self):
        return self.info['Name']

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

    def ensure_network(self, name: str, driver: str = None, internal: bool = False, ingress: bool = False) -> None:
        """Ensure a network exists.
        
        :param name: Name of the network.
        :param driver: Network driver to use.
        :param internal: Restrict network to internal use.
        :param ingress: Create an ingress network.
        """
        
        driver = driver or "bridge"
        
        try:
            self.client.networks.get(name)
        except docker.errors.NotFound:
            self.client.networks.create(name, driver=driver, internal=internal, ingress=ingress)


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
        
        network = self.combine_lists(self.network, network)
         # Connect to additional networks if specified
        for net in (network or []):
            network = self.client.networks.get(net)           
            network.connect(container)
            
        
        return Container(self.client, container)

    def get(self, name_or_id: str) -> Any:
        """Retrieve a container by name or ID."""
        container = self.client.containers.get(name_or_id)
        return Container(self.client, container)

    def list(self, filters: Dict=None, all=False, status=None, **kwargs: Any) -> List[Any]:
        """List all containers."""
        return [Container(self.client, cont) for cont in self.client.containers.list(filters=filters, all=all, **kwargs)]

    def only_one(self, filters: Dict, reset: bool = False) -> None:
        """Ensure only one container is running."""
        
        containers = self.list(filters=filters, all=True)   
        
        if containers:
            logger.debug(f"Found {len(containers)} containers")
            first, rest = containers[0], containers[1:]
            
            for container in rest: # Delete all but the first
                logger.debug(f"Removing container {container.name}")
                container.remove(force=True)
             
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
            
        return None # Didn't find anything, or killed the one we found. 

  


    @property
    def simple_stats(self):
        """Get stats for all containers."""
        for c in self.list():
            ss =  c.simple_stats
            ss['node'] = self.name
            yield ss
     

class ServicesManager(ProcessGroup):
    """Manages Docker Services (Swarm mode) with a consistent interface."""
    
    def __init__(self, client: Any, env: Dict[str, str] = {}, 
                 network: List[str] = [], 
                 labels: Dict[str, str] = {}, hostname_f = None) -> None:
        """
        Initialize the services manager.
        :param client: Docker client instance.
        """
        super().__init__(client, env, network, labels)
        
        self.hostname_f = hostname_f or (lambda x: x)
        
        
    def _node_client(self, node_name):
        """Return a Docker client for a specific node."""
        import docker

        node_host = self.hostname_f(node_name)
        return ContainersManager(docker.DockerClient(base_url=f"ssh://root@{node_host}"))
    
    @property
    def nodes(self):
        for n in self.client.nodes.list():
            node_name = n.attrs['Description']['Hostname']

            yield self._node_client(node_name)
                
    
    
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
        
        if 'ports' in kwargs:
            del kwargs['ports']
        
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


    @property
    def simple_stats(self):
        """Get stats for all services."""
       
        for n in self.nodes:
            yield from n.simple_stats
            
  
    def only_one(self, filters: Dict, reset: bool = False) -> None:
        """Ensure only one service is running."""
        
        services = self.list(filters=filters, all=True)
        
        if services:
            logger.debug(f"Found {len(services)} services")
            first, rest = services[0], services[1:]
            
            for service in rest:  # Remove all but the first
                logger.debug(f"Removing service {service.name}")
                service.remove()
             
            if reset:
                logger.debug(f"Destroying service {first.name} because reset is True")
                first.remove()
            else:
                logger.debug(f"Service {first.name} is already running")
                return first
            
        return None   # Didn't find anything, or killed the one we found. 
    
    def ensure_network(self, name: str, driver: str = None, internal: bool = False, ingress: bool = False) -> None:
        """Ensure a network exists.
        
        :param name: Name of the network.
        :param driver: Network driver to use.
        :param internal: Restrict network to internal use.
        :param ingress: Create an ingress network.
        """
        
        driver = driver or "overlay"
        
        super().ensure_network(name, driver=driver, internal=internal, ingress=ingress)
        
        
class CodeServeManager(ServicesManager):
    
    def __init__(self, client: Any, env: Dict[str, str] = {}, 
                 network: List[str] = [], 
                 labels: Dict[str, str] = {}) -> None:
        """
        Initialize the code serve manager.
        :param client: Docker client instance.
        """
        
        def hostname_f(node_name):
            return f"{node_name}.jointheleague.org"
        
        super().__init__(client, env, network, labels, hostname_f)
    
    def collect_stats(self, mongo_client):
        """Collect container stats."""
        
        from .db import DockerContainerStatsRepository
        
        repo = DockerContainerStatsRepository(mongo_client)
        
        for n in self.simple_stats:
            logger.debug(f"Adding stats for {n['name']}")   
            repo.add(n)
            
        
            
            
        
        
        