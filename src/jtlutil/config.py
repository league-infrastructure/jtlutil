

from pathlib import Path
from typing import Any, Dict, List, Tuple
from dotenv import dotenv_values
import os 

def walk_up(d, f=None) -> List[Path]:
    d = Path(d).resolve()
    paths = []
    while True:
        d = d.parent
        if d == Path('/'):
            break

        if f is not None:
            paths.append(d / f)
        else:
            paths.append(d)

    return paths
def get_config_dirs(cwd=None, root=Path('/'), home=Path().home()) -> List[Path]:
    
    if cwd is None:
        cwd = Path.cwd()
    else:
        cwd = Path(cwd)

    root = Path(root)
    home = Path(home)

    return  [
        cwd,
        home.joinpath('.jtl'),
        root / Path('etc/jtl'), 
        root / Path('etc/jtl/secrets'), 
        root / Path('app/config'),
        root / Path('app/secrets'),
        cwd.joinpath('secrets'),
        cwd.parent.joinpath('secrets'),
    ] 


def find_config_file(file: str | List[str], dirs: List[str] | List[Path] = None) -> Path:
    """Find the first instance of a config file, from  a list of possible files, 
    in a list of directories. Return the first file that exists. """

    if isinstance(file, str):
        file = [file]

    if dirs is None:
        dirs = get_config_dirs()


    for d in dirs:
        for f in file:
            p = Path(d) / f 
            if p.exists():
                return p    
    
    raise FileNotFoundError(f"Could not find any of {file} in {dirs}")


def get_config(file: str | Path = None, dirs: List[str] | List[Path] = None) -> Dict[str, Any]:

    if file is None:
        file = 'config.env'


    if '/' in str(file):
        fp = Path(file)
    else:
        fp = find_config_file(file, dirs)

    config = {
        '__CONFIG_PATH': str(fp.absolute()),
        **os.environ,
        **dotenv_values(fp),
    }

    return config


def path_interp(path: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
    """
    Interpolates the parameters into the endpoint URL. So if you have a path
    like '/api/v1/leagues/:league_id/teams/:team_id' and you call

            path_interp(path, league_id=1, team_id=2, foobar=3)

    it will return '/api/v1/leagues/1/teams/2', along with a dictionary of
    the remaining parameters {'foobar': 3}.

    :param path: The endpoint URL template with placeholders.
    :param kwargs: The keyword arguments where the key is the placeholder (without ':') and the value is the actual value to interpolate.

    :return: A string with the placeholders in the path replaced with actual values from kwargs.
    """

    params = {}
    for key, value in kwargs.items():
        placeholder = f":{key}"  # Placeholder format in the path
        if placeholder in path:
            path = path.replace(placeholder, str(value))
        else:
            # Remove the trailing underscore from the key, so we can use params
            # like 'from' that are python keywords.
            params[key.rstrip('_')] = value

    return path, params
