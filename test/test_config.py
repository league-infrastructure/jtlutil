
from datetime import datetime, timedelta
from src.jtlutil.config import * 
from pathlib import Path

from test import tree1, tree2

t1d = Path(tree1.__file__).parent
t2d = Path(tree2.__file__).parent

def test_find_config_file():
    
    # Build the dirs on the tree1 directory as root
    t1_config_dirs = get_config_dirs(root=t1d, home=t1d/'home'/'testuser', 
                                     cwd=t1d/'dev/l1/l2/l3/dev/')
    
    
    for d in t1_config_dirs:
        d.mkdir(parents=True, exist_ok=True)
    
    def strip_local(d):
        return str(d).rsplit('jtlutil/test/tree1', 1)[1]
    
    # Strip it back off. 
    d = [ strip_local(e) for e in t1_config_dirs]
    
    assert(d == ['/dev/l1/l2/l3/dev', '/home/testuser/.jtl', 
                '/etc/jtl', '/etc/jtl/secrets', '/app/config', 
                '/app/secrets', '/dev/l1/l2/l3/dev/secrets', 
                '/dev/l1/l2/l3/secrets'])
    
    dirs = [
        '/dev/l1/l2/l3/dev', 
        '/home/testuser/.jtl', 
        '/etc/jtl',
        '/etc/jtl/secrets', 
        '/app/config', 
        '/app/secrets', 
        '/dev/l1/l2/l3/dev/secrets', 
        '/dev/l1/l2/l3/secrets'
    ]
    
    config_files = ['config.env', 'dev.env', 'missing.env']

    for d in t1_config_dirs:
        for cf in config_files:
            tf = Path(d)/cf

            if cf != 'missing.env':
                tf.touch()
          
            try:
                p = find_config_file(cf, dirs=t1_config_dirs)
                assert p == tf, f"Expected {tf}, but got {p}"
            except FileNotFoundError as e:
                assert tf.name == 'missing.env', f"Expected missing file, but got {e}"
        
            if tf.exists():
                tf.unlink()
                

def test_config_object():
    config_data = {
        'key1': 'value1',
        'key2': 'value2',
        'key3': 'value3'
    }
    
    config = Config(config_data)
    
    # Test attribute access
    assert config.key1 == 'value1'
    assert config.key2 == 'value2'
    assert config.key3 == 'value3'
    
    # Test item access
    assert config['key1'] == 'value1'
    assert config['key2'] == 'value2'
    assert config['key3'] == 'value3'
    
    # Test item setting
    config['key4'] = 'value4'
    assert config.key4 == 'value4'
    
    # Test item deletion
    del config['key4']
    try:
        _ = config.key4
        assert False, "Expected AttributeError"
    except AttributeError:
        pass
    
    # Test contains
    assert 'key1' in config
    assert 'key4' not in config
    
    # Test get method
    assert config.get('key1') == 'value1'
    assert config.get('key4') is None
    assert config.get('key4', 'default') == 'default'
    
    # Test keys, values, items
    assert set(config.keys()) == {'key1', 'key2', 'key3'}
    assert set(config.values()) == {'value1', 'value2', 'value3'}
    assert set(config.items()) == {('key1', 'value1'), ('key2', 'value2'), ('key3', 'value3')}
    
    config.key4 = 'value4'
    assert config['key4'] == 'value4'
    assert set(config.keys()) == {'key1', 'key2', 'key3', 'key4'}
    assert set(config.values()) == {'value1', 'value2', 'value3', 'value4'}
    
    
